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

from lerobot.common.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError
from lerobot.common.motors import Motor, MotorCalibration, MotorNormMode
from lerobot.common.motors.feetech import (
    FeetechMotorsBus,
    OperatingMode,
)

from ..teleoperator import Teleoperator
from .config_tara_leader import TaraLeaderConfig

logger = logging.getLogger(__name__)


class TaraLeader(Teleoperator):
    """
    Tara dual-arm leader teleoperator using two SO101 leader arms.
    
    This teleoperator controls two SO101 leader arms to provide input for
    the Tara dual-arm follower robot.
    """

    config_class = TaraLeaderConfig
    name = "tara_leader"

    def __init__(self, config: TaraLeaderConfig):
        super().__init__(config)
        self.config = config
        
        # Determine normalization mode based on config
        norm_mode_body = MotorNormMode.DEGREES if config.use_degrees else MotorNormMode.RANGE_M100_100
        
        # Initialize left leader arm motor bus
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
        
        # Initialize right leader arm motor bus
        self.right_bus = FeetechMotorsBus(
            port=self.config.right_port,
            motors={
                "right_shoulder_pan": Motor(1, "sts3215", norm_mode_body),
                "right_shoulder_lift": Motor(2, "sts3215", norm_mode_body),
                "right_elbow_flex": Motor(3, "sts3215", norm_mode_body),
               "right_wrist_flex": Motor(4, "sts3215", norm_mode_body),
               "right_wrist_roll": Motor(5, "sts3215", norm_mode_body),
               "right_gripper": Motor(6, "sts3215", MotorNormMode.RANGE_0_100),
            },
            calibration=self._get_arm_calibration("right"),
        )

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
    def action_features(self) -> dict[str, type]:
        """Get action features for both leader arms."""
        left_motors = {f"{motor}.pos": float for motor in self.left_bus.motors}
        right_motors = {f"{motor}.pos": float for motor in self.right_bus.motors}
        return {**left_motors, **right_motors}

    @property
    def feedback_features(self) -> dict[str, type]:
        """No feedback features for this teleoperator."""
        return {}

    @property
    def is_connected(self) -> bool:
        """Check if both leader arms are connected."""
        return self.left_bus.is_connected and self.right_bus.is_connected

    def connect(self, calibrate: bool = True) -> None:
        """Connect to both leader arms."""
        if self.is_connected:
            raise DeviceAlreadyConnectedError(f"{self} already connected")

        # Connect both leader arms
        self.left_bus.connect()
        self.right_bus.connect()
        
        # Calibrate if needed
        if not self.is_calibrated and calibrate:
            self.calibrate()

        # Configure both arms
        self.configure()
        logger.info(f"{self} connected.")

    @property
    def is_calibrated(self) -> bool:
        """Check if both leader arms are calibrated."""
        return self.left_bus.is_calibrated and self.right_bus.is_calibrated

    def calibrate(self) -> None:
        """Calibrate both leader arms sequentially and save combined calibration."""
        logger.info(f"\nRunning calibration of {self}")
        
        # Initialize empty calibration dictionary
        self.calibration = {}
        
        # Calibrate left leader arm
        logger.info("Calibrating left leader arm...")
        self._calibrate_arm(self.left_bus, "left")
        
        # Store left arm calibration temporarily
        left_calibration = self.calibration.copy()
        
        # Clear calibration for right arm
        self.calibration = {}
        
        # Calibrate right leader arm
        logger.info("Calibrating right leader arm...")
        self._calibrate_arm(self.right_bus, "right")
        
        # Store right arm calibration
        right_calibration = self.calibration.copy()
        
        # Combine both calibrations
        self.calibration = {**left_calibration, **right_calibration}
        print("leader calibration complete. Saving combined calibration...")#debug purposes

        # Save combined calibration
        self._save_calibration()

        print(f"Combined calibration saved to {self.calibration_fpath}")

    def _calibrate_arm(self, bus: FeetechMotorsBus, arm_name: str) -> None:
        """Calibrate a single leader arm."""
        bus.disable_torque()
        for motor in bus.motors:
            bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)

        input(f"Move {arm_name} leader arm to the middle of its range of motion and press ENTER....")
        homing_offsets = bus.set_half_turn_homings()

        print(
            f"Move all {arm_name} leader arm joints sequentially through their entire ranges "
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
        """Configure both leader arms for torque-free operation."""
        self._configure_arm(self.left_bus)
        self._configure_arm(self.right_bus)

    def _configure_arm(self, bus: FeetechMotorsBus) -> None:
        """Configure a single leader arm."""
        # Disable torque for leader arms so they can be moved freely
        bus.disable_torque()
        bus.configure_motors()
        for motor in bus.motors:
            bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)

    def setup_motors(self) -> None:
        """Setup motor IDs for both leader arms."""
        print("Setting up left leader arm motors...")
        self._setup_arm_motors(self.left_bus, "left")
        
        print("Setting up right leader arm motors...")
        self._setup_arm_motors(self.right_bus, "right")

    def _setup_arm_motors(self, bus: FeetechMotorsBus, arm_name: str) -> None:
        """Setup motor IDs for a single leader arm."""
        for motor in reversed(bus.motors):
            input(f"Connect the controller board to the '{motor}' motor ({arm_name} leader arm) only and press enter.")
            bus.setup_motor(motor)
            print(f"'{motor}' motor id set to {bus.motors[motor].id}")

    def get_action(self) -> dict[str, float]:
        """Get actions from both leader arms by reading their current positions."""
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        action = {}

        # Read left leader arm position
        start = time.perf_counter()
        left_action = self.left_bus.sync_read("Present_Position")
        action.update({f"{motor}.pos": val for motor, val in left_action.items()})
        dt_ms = (time.perf_counter() - start) * 1e3
        logger.debug(f"{self} read left leader action: {dt_ms:.1f}ms")

        # Read right leader arm position
        start = time.perf_counter()
        right_action = self.right_bus.sync_read("Present_Position")
        action.update({f"{motor}.pos": val for motor, val in right_action.items()})
        dt_ms = (time.perf_counter() - start) * 1e3
        logger.debug(f"{self} read right leader action: {dt_ms:.1f}ms")

        return action

    def send_feedback(self, feedback: dict[str, float]) -> None:
        """Send feedback to leader arms (force feedback not implemented)."""
        # TODO: Implement force feedback if needed
        # For now, leader arms operate in torque-free mode
        raise NotImplementedError("Force feedback not implemented for Tara leader")

    def disconnect(self) -> None:
        """Disconnect from both leader arms."""
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        # Disconnect both leader arms
        self.left_bus.disconnect()
        self.right_bus.disconnect()
        
        logger.info(f"{self} disconnected.")