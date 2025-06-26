# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Simple script to control a robot from teleoperation.

Example:

```shell
python -m lerobot.teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/tty.usbmodem58760431541 \
    --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 1920, height: 1080, fps: 30}}" \
    --robot.id=black \
    --teleop.type=so101_leader \
    --teleop.port=/dev/tty.usbmodem58760431551 \
    --teleop.id=blue \
    --display_data=true
```

Example2:

```shell
python -m lerobot.teleoperate \
    --robot1.type=so101_follower \
    --robot1.port=/dev/ttyACM2 \
    --robot1.id=white_follower_arm \
    --robot2.type=so101_follower \
    --robot2.port=/dev/ttyACM3 \
    --robot2.id=blue_follower_arm \
    --robot.cameras="{ front: {type: opencv, index_or_path: /dev/video2, width: 640, height: 480, fps: 30}}"\
    --teleop1.type=so101_leader \
    --teleop1.port=/dev/ttyACM0 \
    --teleop1.id=white_leader_arm \
    --teleop2.type=so101_leader \
    --teleop2.port=/dev/ttyACM1 \
    --teleop2.id=blue_leader_arm \
    --display_data=true
```
"""

import logging
import time
import threading
from dataclasses import asdict, dataclass
from pprint import pformat

import draccus
import numpy as np
import rerun as rr

from lerobot.common.cameras.opencv.configuration_opencv import OpenCVCameraConfig  # noqa: F401
from lerobot.common.cameras.realsense.configuration_realsense import RealSenseCameraConfig  # noqa: F401
from lerobot.common.robots import (  # noqa: F401
    Robot,
    RobotConfig,
    koch_follower,
    make_robot_from_config,
    so100_follower,
    so101_follower,
)
from lerobot.common.teleoperators import (
    Teleoperator,
    TeleoperatorConfig,
    make_teleoperator_from_config,
)
from lerobot.common.utils.robot_utils import busy_wait
from lerobot.common.utils.utils import init_logging, move_cursor_up
from lerobot.common.utils.visualization_utils import _init_rerun

from .common.teleoperators import gamepad, koch_leader, so100_leader, so101_leader  # noqa: F401


@dataclass
class TeleoperateConfig:
    teleop1: TeleoperatorConfig
    robot1: RobotConfig
    teleop2: TeleoperatorConfig
    robot2: RobotConfig
    fps: int = 60
    teleop_time_s: float | None = None
    display_data: bool = False


def teleop_loop(
    teleop: Teleoperator, robot: Robot, fps: int, display_data: bool = False, duration: float | None = None
):
    display_len = max(len(key) for key in robot.action_features)
    start = time.perf_counter()
    while True:
        loop_start = time.perf_counter()
        action = teleop.get_action()
        if display_data:
            observation = robot.get_observation()
            for obs, val in observation.items():
                if isinstance(val, float):
                    rr.log(f"observation_{obs}", rr.Scalar(val))
                elif isinstance(val, np.ndarray):
                    rr.log(f"observation_{obs}", rr.Image(val), static=True)
            for act, val in action.items():
                if isinstance(val, float):
                    rr.log(f"action_{act}", rr.Scalar(val))

        robot.send_action(action)
        dt_s = time.perf_counter() - loop_start
        busy_wait(1 / fps - dt_s)

        loop_s = time.perf_counter() - loop_start

        print("\n" + "-" * (display_len + 10))
        print(f"{'NAME':<{display_len}} | {'NORM':>7}")
        for motor, value in action.items():
            print(f"{motor:<{display_len}} | {value:>7.2f}")
        print(f"\ntime: {loop_s * 1e3:.2f}ms ({1 / loop_s:.0f} Hz)")

        if duration is not None and time.perf_counter() - start >= duration:
            return

        move_cursor_up(len(action) + 5)

def teleop_dual_loop(cfg: TeleoperateConfig):
    robot1 = make_robot_from_config(cfg.robot1)
    robot2 = make_robot_from_config(cfg.robot2)
    teleop1 = make_teleoperator_from_config(cfg.teleop1)
    teleop2 = make_teleoperator_from_config(cfg.teleop2)

    teleop1.connect()
    teleop2.connect()
    robot1.connect()
    robot2.connect()

    thread1 = threading.Thread(
        target=teleop_loop,
        args=(teleop1, robot1, cfg.fps, cfg.display_data, cfg.teleop_time_s),
        daemon=True,
    )

    thread2 = threading.Thread(
        target=teleop_loop,
        args=(teleop2, robot2, cfg.fps, cfg.display_data, cfg.teleop_time_s),
        daemon=True,
    )

    thread1.start()
    thread2.start()

    try:
        while thread1.is_alive() or thread2.is_alive():
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        teleop1.disconnect()
        teleop2.disconnect()
        robot1.disconnect()
        robot2.disconnect()
        if cfg.display_data:
            rr.rerun_shutdown()



@draccus.wrap()
def teleoperate(cfg: TeleoperateConfig):
    init_logging()
    logging.info(pformat(asdict(cfg)))
    if cfg.display_data:
        _init_rerun(session_name="dual_teleoperation")

    teleop_dual_loop(cfg)


if __name__ == "__main__":
    teleoperate()