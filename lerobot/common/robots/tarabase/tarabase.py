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
            port=self.config.port, debug=True
        )
        
        # Track connection state
        self._connected = False
        
        # Current state values for wheel speeds
        self.current_left_wheel = 0.0
        self.current_right_wheel = 0.0
        # Legacy values for backward compatibility
        self.current_speed = 0.0
        self.current_direction = 0.0  # in radians, 0 is forward

    @property
    def action_features(self) -> dict:
        """Define the action space for the TaraBase robot based on connected motors."""
        if not self.is_connected():
            # Return default features if not connected
            return {
                "dtype": "float32",
                "shape": (2,),
                "names": {
                    "left_wheel": 0,   # Left wheel motor speed
                    "right_wheel": 1,  # Right wheel motor speed
                },
            }
        
        try:
            # Get motor information from the connected robot
            motor_info = self.robot_client.get_motor_info() if hasattr(self.robot_client, 'get_motor_info') else None
            
            if motor_info and hasattr(motor_info, 'motor_count') and motor_info.motor_count == 2:
                # Dynamic features based on actual motors
                return {
                    "dtype": "float32",
                    "shape": (2,),
                    "names": {
                        "left_wheel": 0,   # Left wheel motor speed
                        "right_wheel": 1,  # Right wheel motor speed
                    },
                }
            else:
                # Fallback to default 2-wheel configuration
                return {
                    "dtype": "float32",
                    "shape": (2,),
                    "names": {
                        "left_wheel": 0,   # Left wheel motor speed
                        "right_wheel": 1,  # Right wheel motor speed
                    },
                }
        except Exception as e:
            logger.warning(f"Could not get motor info from robot: {e}")
            # Fallback to default 2-wheel configuration
            return {
                "dtype": "float32",
                "shape": (2,),
                "names": {
                    "left_wheel": 0,   # Left wheel motor speed
                    "right_wheel": 1,  # Right wheel motor speed
                },
            }

    @property
    def observation_features(self) -> dict:
        """Define the observation space for the TaraBase robot based on connected motors."""
        if not self.is_connected():
            # Return default features if not connected
            return {
                "dtype": "float32",
                "shape": (2,),
                "names": {
                    "current_left_wheel": 0,   # Current left wheel speed
                    "current_right_wheel": 1,  # Current right wheel speed
                },
            }
        
        try:
            # Get motor information from the connected robot
            motor_info = self.robot_client.get_motor_info() if hasattr(self.robot_client, 'get_motor_info') else None
            
            if motor_info and hasattr(motor_info, 'motor_count') and motor_info.motor_count == 2:
                # Dynamic features based on actual motors
                return {
                    "dtype": "float32",
                    "shape": (2,),
                    "names": {
                        "current_left_wheel": 0,   # Current left wheel speed
                        "current_right_wheel": 1,  # Current right wheel speed
                    },
                }
            else:
                # Fallback to default 2-wheel configuration
                return {
                    "dtype": "float32",
                    "shape": (2,),
                    "names": {
                        "current_left_wheel": 0,   # Current left wheel speed
                        "current_right_wheel": 1,  # Current right wheel speed
                    },
                }
        except Exception as e:
            logger.warning(f"Could not get motor info from robot: {e}")
            # Fallback to default 2-wheel configuration
            return {
                "dtype": "float32",
                "shape": (2,),
                "names": {
                    "current_left_wheel": 0,   # Current left wheel speed
                    "current_right_wheel": 1,  # Current right wheel speed
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
                # Set both wheels to zero velocity
                self.robot_client.set_velocity(0.0, 0.0)
                self.current_left_wheel = 0.0
                self.current_right_wheel = 0.0
                # Legacy values for backward compatibility
                self.current_speed = 0.0
                self.current_direction = 0.0
            except Exception as e:
                logger.error(f"Error stopping robot: {e}")

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Send a movement action to the robot.
        
        Args:
            action: Dictionary containing normalized left_wheel and right_wheel values (-1.0 to 1.0).
            
        Returns:
            The action actually sent to the robot (potentially clipped).
        """
        if not self.is_connected():
            raise DeviceNotConnectedError("TaraBase is not connected")
            
        try:
            # Extract normalized wheel speeds (-1.0 to 1.0)
            left_wheel_normalized = float(action.get("left_wheel", 0.0))
            right_wheel_normalized = float(action.get("right_wheel", 0.0))
            
            # Clip normalized values to [-1.0, 1.0] range
            left_wheel_normalized = np.clip(left_wheel_normalized, -1.0, 1.0)
            right_wheel_normalized = np.clip(right_wheel_normalized, -1.0, 1.0)
            
            # Scale normalized values to actual motor speeds using robot's max_linear_speed
            left_wheel = left_wheel_normalized * self.config.max_linear_speed
            right_wheel = right_wheel_normalized * self.config.max_linear_speed
            
            # Log movement direction for debugging
            if abs(left_wheel) > 0.1 or abs(right_wheel) > 0.1:
                if left_wheel * right_wheel > 0:
                    # Both wheels same direction = turning
                    direction = "LEFT" if left_wheel < 0 else "RIGHT"
                    print(f"Turning {direction}: L={left_wheel:.2f}, R={right_wheel:.2f}")
                else:
                    # Wheels opposite direction = forward/backward
                    direction = "FORWARD" if left_wheel < right_wheel else "BACKWARD"
                    print(f"Moving {direction}: L={left_wheel:.2f}, R={right_wheel:.2f}")
            else:
                print("STOPPED")
                
            # Send command to robot using the TaraBaseSDK methods
            self.robot_client.set_velocity(left_wheel, right_wheel)
            
            # Update current state
            self.current_left_wheel = left_wheel
            self.current_right_wheel = right_wheel
            # Legacy values for backward compatibility
            self.current_speed = max(abs(left_wheel), abs(right_wheel))
            self.current_direction = np.sign(left_wheel + right_wheel) / 2
            
            # Return the action that was actually sent (scaled motor speeds)
            return {
                "left_wheel": left_wheel,
                "right_wheel": right_wheel,
            }
            
        except Exception as e:
            logger.error(f"Error sending action to TaraBase: {e}")
            self._stop_robot()
            raise

    def get_observation(self) -> dict[str, Any]:
        """Get the current state of the robot.
        
        Returns:
            Dictionary containing current wheel speeds.
        """
        if not self.is_connected():
            raise DeviceNotConnectedError("TaraBase is not connected")
            
        # Start with basic observations using the last known values
        observation = {
            "current_left_wheel": 0.0,
            "current_right_wheel": 0.0
        }
        
        try:
            # Try to get velocity information from the robot
            if self.robot_client and hasattr(self.robot_client, 'get_actual_velocity'):
                try:
                    # Attempt to get the actual wheel velocities
                    velocities = self.robot_client.get_actual_velocity()
                    
                    # Extract values if we got a valid object
                    if velocities is not None:
                        if hasattr(velocities, 'left_motor_velocity'):
                            observation["current_left_wheel"] = velocities.left_motor_velocity
                        
                        if hasattr(velocities, 'right_motor_velocity'):
                            observation["current_right_wheel"] = velocities.right_motor_velocity
                        
                        logger.debug(f"Got actual velocities: L={observation['current_left_wheel']:.2f}, R={observation['current_right_wheel']:.2f}")
                    else:
                        # Use last known values if we can't get current ones
                        observation["current_left_wheel"] = self.current_left_wheel
                        observation["current_right_wheel"] = self.current_right_wheel
                        logger.debug(f"Using cached velocities: L={observation['current_left_wheel']:.2f}, R={observation['current_right_wheel']:.2f}")
                        
                except Exception as e:
                    logger.warning(f"Could not get velocity information: {e}")
                    # Fallback to last known values
                    observation["current_left_wheel"] = self.current_left_wheel
                    observation["current_right_wheel"] = self.current_right_wheel
            else:
                # SDK doesn't support velocity feedback, use last commanded values
                observation["current_left_wheel"] = self.current_left_wheel
                observation["current_right_wheel"] = self.current_right_wheel
                logger.debug(f"No velocity feedback available, using cached values")
                
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
