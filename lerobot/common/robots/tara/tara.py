#!/usr/bin/env python

# Copyright 2025 The HuggingFace Inc. team. All rights reserved.
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

import logging
import time
from functools import cached_property
from typing import Any

from lerobot.common.cameras.utils import make_cameras_from_configs
from lerobot.common.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError
from lerobot.common.motors import Motor, MotorCalibration, MotorNormMode
from lerobot.common.motors.feetech import (
    FeetechMotorsBus,
    OperatingMode,
)

from ..robot import Robot
from ..utils import ensure_safe_goal_position
from .config_tara import TaraConfig

logger = logging.getLogger(__name__)


class Tara(Robot):
    """
    Tara dual-arm robot using two SO101 arms.
    
    This robot controls two SO101 arms simultaneously, providing coordinated
    dual-arm manipulation capabilities.
    """

    config_class = TaraConfig
    name = "tara"

    def __init__(self, config: TaraConfig):
        super().__init__(config)
        self.config = config
        
        # Determine normalization mode based on config
        norm_mode_body = MotorNormMode.DEGREES if config.use_degrees else MotorNormMode.RANGE_M100_100
        
        # Initialize left arm motor bus
        self.left_bus = FeetechMotorsBus(
            port=self.config.left_port,
            motors={
                "left_shoulder_pan": Motor(1, "sts3215", norm_mode_body),
                "left_shoulder_lift": Motor(2, "sts3215", norm_mode_body),
                "left_elbow_flex": Motor(3, "sts3215", norm_mode_body),
                "left_wrist_flex": Motor(4, "sts3215", norm_mode_body),
                "left_wrist_roll": Motor(5, "sts3215", norm_mode_body),
                "left_gripper": Motor(6, "sts3215", MotorNormMode.RANGE_0_100),
            },
            calibration=self._get_arm_calibration("left"),
        )
        
        # Initialize right arm motor bus
        self.right_bus = FeetechMotorsBus(
            port=self.config.right_port,
            motors={
                "right_shoulder_pan": Motor(1, "sts3215", norm_mode_body),
                "right_shoulder_lift": Motor(2, "sts3215", norm_mode_body),
                "right_elbow_flex": Motor(3, "sts3215", norm_mode_body),
               #"right_wrist_flex": Motor(4, "sts3215", norm_mode_body),
               #"right_wrist_roll": Motor(5, "sts3215", norm_mode_body),
               #"right_gripper": Motor(6, "sts3215", MotorNormMode.RANGE_0_100),
            },
            calibration=self._get_arm_calibration("right"),
        )
        
        # Initialize cameras
        self.cameras = make_cameras_from_configs(config.cameras)

    def _get_arm_calibration(self, arm_name: str) -> dict | None:
        """Get calibration data for a specific arm."""
        if not hasattr(self, 'calibration') or self.calibration is None:
            return None
        
        # Filter calibration data for the specific arm
        arm_calibration = {}
        for motor_name, calib in self.calibration.items():
            if motor_name.startswith(f"{arm_name}_"):
                arm_calibration[motor_name] = calib
        
        return arm_calibration if arm_calibration else None

    @property
    def _motors_ft(self) -> dict[str, type]:
        """Get motor feature types for both arms."""
        left_motors = {f"{motor}.pos": float for motor in self.left_bus.motors}
        right_motors = {f"{motor}.pos": float for motor in self.right_bus.motors}
        return {**left_motors, **right_motors}

    @property
    def _cameras_ft(self) -> dict[str, tuple]:
        """Get camera feature types."""
        return {
            cam: (self.config.cameras[cam].height, self.config.cameras[cam].width, 3) 
            for cam in self.cameras
        }

    @cached_property
    def observation_features(self) -> dict[str, type | tuple]:
        """Get all observation features (motors + cameras)."""
        return {**self._motors_ft, **self._cameras_ft}

    @cached_property
    def action_features(self) -> dict[str, type]:
        """Get all action features (motors only)."""
        return self._motors_ft

    @property
    def is_connected(self) -> bool:
        """Check if both arms and all cameras are connected."""
        return (
            self.left_bus.is_connected 
            and self.right_bus.is_connected 
            and all(cam.is_connected for cam in self.cameras.values())
        )

    def connect(self, calibrate: bool = True) -> None:
        """
        Connect to both arms and cameras.
        
        Args:
            calibrate: Whether to run calibration if not already calibrated.
        """
        if self.is_connected:
            raise DeviceAlreadyConnectedError(f"{self} already connected")

        # Connect both arms
        self.left_bus.connect()
        self.right_bus.connect()
        
        # Calibrate if needed
        if not self.is_calibrated and calibrate:
            self.calibrate()

        # Connect cameras
        for cam in self.cameras.values():
            cam.connect()

        # Configure both arms
        self.configure()
        logger.info(f"{self} connected.")

    @property
    def is_calibrated(self) -> bool:
        """Check if both arms are calibrated."""
        return self.left_bus.is_calibrated and self.right_bus.is_calibrated

    def calibrate(self) -> None:
        """Calibrate both arms sequentially and save combined calibration."""
        logger.info(f"\nRunning calibration of {self}")
        
        # Initialize empty calibration dictionary
        self.calibration = {}
        
        # Calibrate left arm
        logger.info("Calibrating left arm...")
        self._calibrate_arm(self.left_bus, "left")
        
        # Store left arm calibration temporarily
        left_calibration = self.calibration.copy()
        
        # Clear calibration for right arm
        self.calibration = {}
        
        # Calibrate right arm
        logger.info("Calibrating right arm...")
        self._calibrate_arm(self.right_bus, "right")
        
        # Store right arm calibration
        right_calibration = self.calibration.copy()
        
        # Combine both calibrations
        self.calibration = {**left_calibration, **right_calibration}
        print("Robot calibration complete. Saving combined calibration...")#debug purposes
        # Save combined calibration
        self._save_calibration()
        print(f"Combined calibration saved to {self.calibration_fpath}")

    def _calibrate_arm(self, bus: FeetechMotorsBus, arm_name: str) -> None:
        """Calibrate a single arm."""
        bus.disable_torque()
        for motor in bus.motors:
            bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)

        input(f"Move {arm_name} arm to the middle of its range of motion and press ENTER....")
        homing_offsets = bus.set_half_turn_homings()

        print(
            f"Move all {arm_name} arm joints sequentially through their entire ranges "
            "of motion.\nRecording positions. Press ENTER to stop..."
        )
        range_mins, range_maxes = bus.record_ranges_of_motion()

        # Store calibration data
        if not hasattr(self, 'calibration') or self.calibration is None:
            self.calibration = {}
            
        for motor, m in bus.motors.items():
            self.calibration[motor] = MotorCalibration(
                id=m.id,
                drive_mode=0,
                homing_offset=homing_offsets[motor],
                range_min=range_mins[motor],
                range_max=range_maxes[motor],
            )

        bus.write_calibration(self._get_arm_calibration(arm_name))

    def configure(self) -> None:
        """Configure both arms with optimal settings."""
        self._configure_arm(self.left_bus)
        self._configure_arm(self.right_bus)

    def _configure_arm(self, bus: FeetechMotorsBus) -> None:
        """Configure a single arm."""
        with bus.torque_disabled():
            bus.configure_motors()
            for motor in bus.motors:
                bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)
                # Set P_Coefficient to lower value to avoid shakiness (Default is 32)
                bus.write("P_Coefficient", motor, 16)
                # Set I_Coefficient and D_Coefficient to default value 0 and 32
                bus.write("I_Coefficient", motor, 0)
                bus.write("D_Coefficient", motor, 32)

    def setup_motors(self) -> None:
        """Setup motor IDs for both arms."""
        print("Setting up left arm motors...")
        self._setup_arm_motors(self.left_bus, "left")
        
        print("Setting up right arm motors...")
        self._setup_arm_motors(self.right_bus, "right")

    def _setup_arm_motors(self, bus: FeetechMotorsBus, arm_name: str) -> None:
        """Setup motor IDs for a single arm."""
        for motor in reversed(bus.motors):
            input(f"Connect the controller board to the '{motor}' motor ({arm_name} arm) only and press enter.")
            bus.setup_motor(motor)
            print(f"'{motor}' motor id set to {bus.motors[motor].id}")

    def get_observation(self) -> dict[str, Any]:
        """Get observations from both arms and all cameras."""
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        obs_dict = {}

        # Read left arm position
        start = time.perf_counter()
        left_pos = self.left_bus.sync_read("Present_Position")
        obs_dict.update({f"{motor}.pos": val for motor, val in left_pos.items()})
        dt_ms = (time.perf_counter() - start) * 1e3
        logger.debug(f"{self} read left arm state: {dt_ms:.1f}ms")

        # Read right arm position
        start = time.perf_counter()
        right_pos = self.right_bus.sync_read("Present_Position")
        obs_dict.update({f"{motor}.pos": val for motor, val in right_pos.items()})
        dt_ms = (time.perf_counter() - start) * 1e3
        logger.debug(f"{self} read right arm state: {dt_ms:.1f}ms")

        # Capture images from cameras
        for cam_key, cam in self.cameras.items():
            start = time.perf_counter()
            obs_dict[cam_key] = cam.async_read()
            dt_ms = (time.perf_counter() - start) * 1e3
            logger.debug(f"{self} read {cam_key}: {dt_ms:.1f}ms")

        return obs_dict

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """
        Send actions to both arms.

        The relative action magnitude may be clipped depending on the configuration parameter
        `max_relative_target`. In this case, the action sent differs from original action.
        Thus, this function always returns the action actually sent.

        Args:
            action: Dictionary containing goal positions for all motors.

        Returns:
            The action sent to the motors, potentially clipped.
        """
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        # Separate actions for left and right arms
        left_actions = {}
        right_actions = {}
        
        for key, val in action.items():
            if key.endswith(".pos"):
                motor_name = key.removesuffix(".pos")
                if motor_name.startswith("left_"):
                    left_actions[motor_name] = val
                elif motor_name.startswith("right_"):
                    right_actions[motor_name] = val

        # Apply safety limits if configured
        if self.config.max_relative_target is not None:
            left_actions = self._apply_safety_limits(self.left_bus, left_actions)
            right_actions = self._apply_safety_limits(self.right_bus, right_actions)

        # Send actions to both arms
        self.left_bus.sync_write("Goal_Position", left_actions)
        self.right_bus.sync_write("Goal_Position", right_actions)

        # Return the actual actions sent
        sent_actions = {}
        sent_actions.update({f"{motor}.pos": val for motor, val in left_actions.items()})
        sent_actions.update({f"{motor}.pos": val for motor, val in right_actions.items()})
        
        return sent_actions

    def _apply_safety_limits(self, bus: FeetechMotorsBus, goal_pos: dict[str, float]) -> dict[str, float]:
        """Apply safety limits to goal positions for a single arm."""
        present_pos = bus.sync_read("Present_Position")
        goal_present_pos = {key: (g_pos, present_pos[key]) for key, g_pos in goal_pos.items()}
        return ensure_safe_goal_position(goal_present_pos, self.config.max_relative_target)

    def disconnect(self):
        """Disconnect from both arms and all cameras."""
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        # Disconnect both arms
        self.left_bus.disconnect(self.config.disable_torque_on_disconnect)
        self.right_bus.disconnect(self.config.disable_torque_on_disconnect)
        
        # Disconnect cameras
        for cam in self.cameras.values():
            cam.disconnect()

        logger.info(f"{self} disconnected.")