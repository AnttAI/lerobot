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
'''
shell 
Example:
python examples/tara_base_teleop.py --port=/dev/ttyUSB0 --max-speed=0.5 --max-angular=0.8

'''

import logging
import time
from functools import cached_property
from typing import Any

import numpy as np

# Import the TaraSDK module with the TaraBase class
from tara_sdk import TaraBase as TaraBaseSDK


# No cameras used in this implementation
from lerobot.common.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError

from ..robot import Robot
from .config_tarabase import TaraBaseConfig

logger = logging.getLogger(__name__)


class TaraBase(Robot):
    """
    TaraBase robot controlled using the TaraSDK.
    
    This robot provides a mobile base platform that can be controlled with simple
    movement commands (forward/backward, left/right).
    """

    config_class = TaraBaseConfig
    name = "tarabase"

    def __init__(self, config: TaraBaseConfig):
        """Initialize the TaraBase robot with the given configuration."""
        super().__init__(config)
        self.config = config
        
        # Create the TaraBaseSDK instance right in the init with just the port
        self.robot_client = TaraBaseSDK(
            port=self.config.port
        )
        
        # Track connection state
        self._connected = False
        
        # Current state values
        self.current_speed = 0.0
        self.current_direction = 0.0  # in radians, 0 is forward

    @property
    def action_features(self) -> dict:
        """Define the action space for the TaraBase robot."""
        return {
            "dtype": "float32",
            "shape": (3,),
            "names": {
                "linear_x": 0,  # Forward/backward motion
                "linear_y": 1,  # Sideways motion (if supported by the base)
                "angular_z": 2,  # Rotation around Z axis
            },
        }

    @property
    def observation_features(self) -> dict:
        """Define the observation space for the TaraBase robot."""
        return {
            "dtype": "float32",
            "shape": (3,),
            "names": {
                "current_linear_x": 0,
                "current_linear_y": 1,
                "current_angular_z": 2,
            },
        }

    def connect(self) -> None:
        """Connect to the TaraBase robot using TaraSDK."""
        if self._connected:
            raise DeviceAlreadyConnectedError("TaraBase is already connected")
            
        try:
            logger.info(f"Connecting to TaraBase on port {self.config.port}")
            
            # Connect to the robot using the already created TaraBaseSDK instance
            self.robot_client.connect()
                    
            self._connected = True
            logger.info("Successfully connected to TaraBase")
            
        except Exception as e:
            logger.error(f"Failed to connect to TaraBase: {e}")
            self.robot_client = None
            raise

    def disconnect(self) -> None:
        """Disconnect from the TaraBase robot."""
        if not self._connected:
            return
            
        try:
            # Stop the robot before disconnecting
            self._stop_robot()
            
            # Disconnect from the robot
            if self.robot_client:
                self.robot_client.disconnect()
                
            self._connected = False
            logger.info("Disconnected from TaraBase")
            
        except Exception as e:
            logger.error(f"Error disconnecting from TaraBase: {e}")
            raise
        finally:
            # Only reset the connection state, don't nullify the client
            self._connected = False

    def is_connected(self) -> bool:
        """Check if the robot is connected."""
        return self._connected and self.robot_client is not None

    @property
    def is_calibrated(self) -> bool:
        """Check if the robot is calibrated. For TaraBase, we always return True (hardcoded)."""
        return True

    def calibrate(self) -> None:
        """Calibrate the robot. For TaraBase, this is a no-op since we hardcode calibration values."""
        logger.info("TaraBase calibration skipped - using hardcoded values")
        # Set some dummy calibration values if needed
        self.calibration = {}

    def configure(self) -> None:
        """Configure the robot. For TaraBase, this sets basic parameters."""
        logger.info("Configuring TaraBase with default parameters")
        # Any configuration can go here if needed in the future

    def _stop_robot(self) -> None:
        """Stop all robot movement."""
        if self.robot_client:
            try:
                # Set both linear_x and linear_y to zero
                self.robot_client.set_velocity(0.0, 0.0)
                self.current_speed = 0.0
                self.current_direction = 0.0
            except Exception as e:
                logger.error(f"Error stopping robot: {e}")

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Send a movement action to the robot.
        
        Args:
            action: Dictionary containing linear_x, linear_y, and angular_z values.
            
        Returns:
            The action actually sent to the robot (potentially clipped).
        """
        if not self.is_connected():
            raise DeviceNotConnectedError("TaraBase is not connected")
            
        try:
            # Extract action values
            linear_x = float(action.get("linear_x", 0.0))
            linear_y = float(action.get("linear_y", 0.0))
            # angular_z is ignored, as SDK does not support it
            
            # Apply speed limits
            linear_x = np.clip(linear_x, -self.config.max_linear_speed, self.config.max_linear_speed)
            linear_y = np.clip(linear_y, -self.config.max_linear_speed, self.config.max_linear_speed)
            
            # Set wheel velocities based on both delta_x (forward/backward) and delta_y (turning)
            wheel_speed = 5  # Fixed speed value for forward/backward
            turn_speed = 3   # Fixed speed value for turning (can be adjusted)
            
            # Determine base movement direction (forward/backward)
            # For differential drive, we need opposite directions for each wheel
            # Left wheel is negative for forward, positive for backward
            # Right wheel is positive for forward, negative for backward
            
            # Initialize wheel speeds to 0
            left_wheel = 0
            right_wheel = 0
            
            # First, handle forward/backward movement based on linear_x
            if abs(linear_x) >= 0.5:  # Active forward/backward movement
                if linear_x > 0:  # Forward
                    left_wheel = -wheel_speed
                    right_wheel = wheel_speed
                    movement_str = f"FORWARD with delta_x = {linear_x}"
                else:  # Backward
                    left_wheel = wheel_speed
                    right_wheel = -wheel_speed
                    movement_str = f"BACKWARD with delta_x = {linear_x}"
            else:
                movement_str = ""
                
            # Then, handle turning based on linear_y (overrides or modifies forward/backward)
            if abs(linear_y) >= 0.5:  # Active turning
                # For pure rotation in place, both wheels need to rotate in the SAME direction
                # This is opposite to forward/backward movement where wheels rotate in opposite directions
                if linear_y > 0:  # Turn LEFT: Both wheels rotate counterclockwise
                    left_wheel = -turn_speed  # Left wheel negative (counterclockwise)
                    right_wheel = -turn_speed  # Right wheel also negative (counterclockwise)
                    turning_str = f"LEFT with delta_y = {linear_y}"
                else:  # Turn RIGHT: Both wheels rotate clockwise
                    left_wheel = turn_speed   # Left wheel positive (clockwise)
                    right_wheel = turn_speed  # Right wheel also positive (clockwise)
                    turning_str = f"RIGHT with delta_y = {linear_y}"
                if movement_str:
                    print(f"Moving {movement_str} and turning {turning_str}")
                else:
                    print(f"Turning {turning_str}")
            elif movement_str:
                print(f"Moving {movement_str}")
            else:
                print("STOPPED")
                
            # Send command to robot using the TaraBaseSDK methods
            self.robot_client.set_velocity(left_wheel, right_wheel)
            
            # Update current state
            self.current_speed = abs(left_wheel)
            self.current_direction = np.sign(left_wheel)
            
            # Return the action that was actually sent (potentially clipped)
            return {
                "linear_x": left_wheel,
                "linear_y": right_wheel,
                "angular_z": 0.0,  # Not supported
            }
            
        except Exception as e:
            logger.error(f"Error sending action to TaraBase: {e}")
            self._stop_robot()
            raise

    def get_observation(self) -> dict[str, Any]:
        """Get the current state of the robot.
        
        Returns:
            Dictionary containing current speeds and camera observations.
        """
        if not self.is_connected():
            raise DeviceNotConnectedError("TaraBase is not connected")
            
        # Start with basic observations using the last known values
        observation = {
            "current_linear_x": self.current_speed if self.current_direction >= 0 else -self.current_speed,
            "current_linear_y": 0.0,
            "current_angular_z": 0.0,
            "current_left": 0.0,
            "current_right": 0.0
        }
        
        try:
            # Try to get velocity information but don't fail if it's not available
            if self.robot_client and hasattr(self.robot_client, 'get_actual_velocity'):
                try:
                    # Attempt to get the velocity
                    velocities = self.robot_client.get_actual_velocity()
                    
                    # Only extract values if we got a valid object
                    if velocities is not None:
                        if hasattr(velocities, 'left_motor_velocity'):
                            observation["current_left"] = velocities.left_motor_velocity
                        
                        if hasattr(velocities, 'right_motor_velocity'):
                            observation["current_right"] = velocities.right_motor_velocity
                except Exception as e:
                    logger.warning(f"Could not get velocity information: {e}")
                    # If we can't get the actual velocity, use the last known speed
                    observation["current_left"] = self.current_speed * self.current_direction
                    observation["current_right"] = self.current_speed * self.current_direction
        except Exception as e:
            logger.error(f"Error getting observation from TaraBase: {e}")
            
        return observation

    def reset(self) -> dict[str, Any]:
        """Reset the robot to a safe state and return the initial observation.
        
        Returns:
            Initial observation after reset.
        """
        if not self.is_connected():
            raise DeviceNotConnectedError("TaraBase is not connected")
            
        try:
            # Stop all movement
            self._stop_robot()
            time.sleep(0.5)  # Give the robot time to come to a complete stop
            
            # Return the current state as the initial observation
            return self.get_observation()
            
        except Exception as e:
            logger.error(f"Error resetting TaraBase: {e}")
            raise

    def emergency_stop(self) -> None:
        """Immediately stop all robot movement (emergency stop)."""
        if self.is_connected() and self.robot_client:
            try:
                # No emergency_halt in SDK; just stop the robot
                self._stop_robot()
                logger.warning("Emergency stop activated on TaraBase (set_velocity(0,0))")
            except Exception as e:
                logger.error(f"Error during emergency stop: {e}")
                # Fall back to regular stop if emergency halt fails
                try:
                    self._stop_robot()
                except:
                    pass
