import threading
import time
from dataclasses import dataclass, asdict
from pprint import pformat
import numpy as np
import rerun as rr
import draccus
from lerobot.common.robots import make_robot_from_config, RobotConfig
from lerobot.common.teleoperators import make_teleoperator_from_config, TeleoperatorConfig
from lerobot.common.cameras.opencv.configuration_opencv import OpenCVCameraConfig
from lerobot.common.cameras.opencv.opencv_camera import OpenCVCamera
from lerobot.common.utils.robot_utils import busy_wait
from lerobot.common.utils.visualization_utils import _init_rerun
from lerobot.common.utils.utils import init_logging, move_cursor_up

@dataclass
class TaraConfig:
    teleop1: TeleoperatorConfig
    robot1: RobotConfig
    teleop2: TeleoperatorConfig
    robot2: RobotConfig
    camera: dict
    fps: int = 60
    teleop_time_s: float | None = None
    display_data: bool = True

def teleop_loop(
    teleop, robot, fps, display_data=False, duration=None, name=""
):
    display_len = max(len(key) for key in robot.action_features)
    start = time.perf_counter()
    while True:
        loop_start = time.perf_counter()
        action = teleop.get_action()
        if display_data:
            observation = robot.get_observation()
            # Log all observations with arm name
            for obs, val in observation.items():
                if isinstance(val, float):
                    rr.log(f"{name}/observation/{obs}", rr.Scalar(val))
                elif isinstance(val, np.ndarray):
                    rr.log(f"{name}/observation/{obs}", rr.Image(val), static=True)
            # Log all actions with arm name
            for act, val in action.items():
                if isinstance(val, float):
                    rr.log(f"{name}/action/{act}", rr.Scalar(val))
        robot.send_action(action)
        dt_s = time.perf_counter() - loop_start
        busy_wait(max(0, 1 / fps - dt_s))
        loop_s = time.perf_counter() - loop_start
        print(f"\n[{name}] " + "-" * (display_len + 10))
        print(f"{'NAME':<{display_len}} | {'NORM':>7}")
        for motor, value in action.items():
            print(f"{motor:<{display_len}} | {value:>7.2f}")
        print(f"\n[{name}] time: {loop_s * 1e3:.2f}ms ({1 / loop_s:.0f} Hz)")
        if duration is not None and time.perf_counter() - start >= duration:
            return
        move_cursor_up(len(action) + 5)

def camera_loop(camera, fps, display_data=True):
    while True:
        frame = camera.get_image()
        if display_data:
            rr.log("camera/front", rr.Image(frame), static=True)
        busy_wait(1 / fps)

@draccus.wrap()
def main(cfg: TaraConfig):
    init_logging()
    print(pformat(asdict(cfg)))
    if cfg.display_data:
        _init_rerun(session_name="tara_teleoperation")
    # Setup robots and teleops
    robot1 = make_robot_from_config(cfg.robot1)
    robot2 = make_robot_from_config(cfg.robot2)
    teleop1 = make_teleoperator_from_config(cfg.teleop1)
    teleop2 = make_teleoperator_from_config(cfg.teleop2)
    # Setup camera
    try:
        cam_cfg = cfg.camera["front"]
    except KeyError:
        raise KeyError("Camera configuration must include a 'front' key.")
    camera = OpenCVCamera(OpenCVCameraConfig(**cam_cfg))
    try:
        camera.connect()
    except Exception as e:
        print(f"Failed to connect to camera: {e}")
        return
    # Connect everything
    teleop1.connect()
    teleop2.connect()
    robot1.connect()
    robot2.connect()
    # Names for logging
    name1 = getattr(cfg.robot1, "id", "robot1")
    name2 = getattr(cfg.robot2, "id", "robot2")
    # Start threads
    t1 = threading.Thread(target=teleop_loop, args=(teleop1, robot1, cfg.fps, cfg.display_data, cfg.teleop_time_s, name1), daemon=True)
    t2 = threading.Thread(target=teleop_loop, args=(teleop2, robot2, cfg.fps, cfg.display_data, cfg.teleop_time_s, name2), daemon=True)
    tcam = threading.Thread(target=camera_loop, args=(camera, cfg.fps, cfg.display_data), daemon=True)
    t1.start()
    t2.start()
    tcam.start()
    try:
        while t1.is_alive() or t2.is_alive() or tcam.is_alive():
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        teleop1.disconnect()
        teleop2.disconnect()
        robot1.disconnect()
        robot2.disconnect()
        camera.disconnect()
        if cfg.display_data:
            rr.rerun_shutdown()

if __name__ == "__main__":
    main()
