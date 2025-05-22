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

from typing import Protocol

from lerobot.common.robot_devices.robots.configs import (
    AlohaRobotConfig,
    KochBimanualRobotConfig,
    KochRobotConfig,
    LeKiwiRobotConfig,
    ManipulatorRobotConfig,
    MossRobotConfig,
    NewRobotConfig,
    RobotConfig,
    So100RobotConfig,
    So101RobotConfig,
    StretchRobotConfig,
)


def get_arm_id(name, arm_type):
    """Returns the string identifier of a robot arm. For instance, for a bimanual manipulator
    like Aloha, it could be left_follower, right_follower, left_leader, or right_leader.
    """
    return f"{name}_{arm_type}"


class Robot(Protocol):
    # TODO(rcadene, aliberts): Add unit test checking the protocol is implemented in the corresponding classes
    robot_type: str
    features: dict

    def connect(self): ...
    def run_calibration(self): ...
    def teleop_step(self, record_data=False): ...
    def capture_observation(self): ...
    def send_action(self, action): ...
    def disconnect(self): ...


def make_robot_config(robot_type: str, **kwargs) -> RobotConfig:
    if robot_type == "aloha":
        return AlohaRobotConfig(**kwargs)
    elif robot_type == "koch":
        return KochRobotConfig(**kwargs)
    elif robot_type == "koch_bimanual":
        return KochBimanualRobotConfig(**kwargs)
    elif robot_type == "moss":
        return MossRobotConfig(**kwargs)
    elif robot_type == "so100":
        return So100RobotConfig(**kwargs)
    elif robot_type == "so101":
        return So101RobotConfig(**kwargs)
    elif robot_type == "stretch":
        return StretchRobotConfig(**kwargs)
    elif robot_type == "lekiwi":
        return LeKiwiRobotConfig(**kwargs)
    elif robot_type == "new_robot":
        return NewRobotConfig(**kwargs)
    else:
        raise ValueError(f"Robot type '{robot_type}' is not available.")


def make_robot_from_config(config: RobotConfig):
    # NewRobot is a ManipulatorRobot, and NewRobotConfig is a ManipulatorRobotConfig.
    # So, the existing ManipulatorRobot block will handle NewRobot.
    # If NewRobot required specific instantiation logic different from ManipulatorRobot,
    # an explicit check would be:
    # elif isinstance(config, NewRobotConfig):
    #     from lerobot.common.robot_devices.robots.new_robot import NewRobot
    #     return NewRobot(config)
    if isinstance(config, ManipulatorRobotConfig):
        # This will also correctly instantiate NewRobot if config is NewRobotConfig,
        # because NewRobot is a subclass of ManipulatorRobot.
        # To be more specific and future-proof for NewRobot specific logic,
        # one could add a dedicated block as commented out above.
        # However, if NewRobot is intended to be created just like any other ManipulatorRobot,
        # this is fine.
        # Let's import the specific robot class based on the config type if possible,
        # falling back to ManipulatorRobot for generic manipulator configs.
        if isinstance(config, AlohaRobotConfig):
            from lerobot.common.robot_devices.robots.aloha.aloha_robot import AlohaRobot
            return AlohaRobot(config)
        elif isinstance(config, KochRobotConfig) or isinstance(config, KochBimanualRobotConfig):
            from lerobot.common.robot_devices.robots.koch.koch_robot import KochRobot
            return KochRobot(config)
        elif isinstance(config, MossRobotConfig):
            from lerobot.common.robot_devices.robots.moss.moss_robot import MossRobot
            return MossRobot(config)
        elif isinstance(config, So100RobotConfig):
            from lerobot.common.robot_devices.robots.so100.so100_robot import So100Robot
            return So100Robot(config)
        elif isinstance(config, So101RobotConfig):
            from lerobot.common.robot_devices.robots.so101.so101_robot import So101Robot
            return So101Robot(config)
        elif isinstance(config, NewRobotConfig): # Explicitly handle NewRobotConfig
            from lerobot.common.robot_devices.robots.new_robot import NewRobot
            return NewRobot(config)
        else:
            # Fallback for other ManipulatorRobotConfig types if any
            from lerobot.common.robot_devices.robots.manipulator import ManipulatorRobot
            return ManipulatorRobot(config)
    elif isinstance(config, LeKiwiRobotConfig):
        from lerobot.common.robot_devices.robots.mobile_manipulator import MobileManipulator

        return MobileManipulator(config)
    else:
        from lerobot.common.robot_devices.robots.stretch import StretchRobot

        return StretchRobot(config)


def make_robot(robot_type: str, **kwargs) -> Robot:
    config = make_robot_config(robot_type, **kwargs)
    return make_robot_from_config(config)
