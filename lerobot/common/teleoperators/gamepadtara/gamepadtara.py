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

import sys
import logging
from typing import Any

import numpy as np

from ..teleoperator import Teleoperator
from .config_gamepadtara import GamepadTaraConfig

logger = logging.getLogger(__name__)


class GamepadTara(Teleoperator):
    """
    Teleoperator class to control TaraBase robots using gamepad inputs.
    
    This maps gamepad inputs directly to left_wheel and right_wheel speeds
    for differential drive control of the TaraBase robot.
    """

    config_class = GamepadTaraConfig
    name = "gamepadtara"

    def __init__(self, config: GamepadTaraConfig):
        super().__init__(config)
        self.config = config
        
        # Will be initialized in connect()
        self.gamepad = None

    @property
    def action_features(self) -> dict:
        """Define the action space for the TaraBase teleoperator."""
        return {
            "dtype": "float32",
            "shape": (2,),
            "names": {
                "left_wheel": 0,   # Left wheel motor speed
                "right_wheel": 1,  # Right wheel motor speed
            },
        }

    @property
    def feedback_features(self) -> dict:
        """Define the feedback features (none for gamepad)."""
        return {}

    def connect(self) -> None:
        """Initialize and connect to the gamepad controller."""
        # Use HidApi for macOS
        if sys.platform == "darwin":
            # NOTE: On macOS, pygame doesn't reliably detect input from some controllers
            # so we fall back to hidapi
            from ..gamepad.gamepad_utils import GamepadControllerHID as Gamepad
        else:
            from ..gamepad.gamepad_utils import GamepadController as Gamepad

        try:
            self.gamepad = Gamepad()
            self.gamepad.start()
            logger.info("Connected to gamepad controller")
        except Exception as e:
            logger.error(f"Failed to connect to gamepad: {e}")
            self.gamepad = None
            raise

    def _apply_deadzone(self, value, deadzone):
        """Apply deadzone to input values to prevent drift from small inputs."""
        if abs(value) < deadzone:
            return 0.0
        return value

    def get_action(self) -> dict[str, Any]:
        """Get the current gamepad inputs and convert them to TaraBase wheel commands."""
        if not self.is_connected():
            logger.warning("Gamepad not connected, returning zero action")
            return {"left_wheel": 0.0, "right_wheel": 0.0}

        # Update the controller to get fresh inputs
        self.gamepad.update()

        # Get movement deltas from the controller
        # For TaraBase, we use:
        # - Left stick Y-axis (delta_x) for forward/backward motion
        # - Left stick X-axis (delta_y) for turning left/right
        
        delta_x, delta_y, _ = self.gamepad.get_deltas()
        
        # Apply deadzone to get normalized values (-1.0 to 1.0)
        forward_backward = self._apply_deadzone(delta_x, self.config.deadzone)
        left_right = self._apply_deadzone(delta_y, self.config.deadzone)
        
        # Convert gamepad inputs to normalized differential drive wheel commands
        # The robot will handle the actual speed scaling
        
        left_wheel = 0.0
        right_wheel = 0.0
        
        # Handle forward/backward movement
        if abs(forward_backward) > 0.1:
            if forward_backward > 0:  # Forward
                left_wheel = -forward_backward  # Normalized value
                right_wheel = forward_backward   # Normalized value
            else:  # Backward
                left_wheel = -forward_backward   # Normalized value
                right_wheel = forward_backward   # Normalized value
        
        # Handle turning (overrides forward/backward if both are active)
        if abs(left_right) > 0.1:
            if left_right > 0:  # Turn left
                left_wheel = -left_right   # Normalized value
                right_wheel = -left_right  # Normalized value
            else:  # Turn right
                left_wheel = -left_right   # Normalized value
                right_wheel = -left_right  # Normalized value
        
        # Create action dictionary for TaraBase (normalized values -1.0 to 1.0)
        action_dict = {
            "left_wheel": left_wheel,
            "right_wheel": right_wheel,
        }
        
        return action_dict

    def disconnect(self) -> None:
        """Disconnect from the gamepad."""
        if self.gamepad is not None:
            try:
                self.gamepad.stop()
                logger.info("Disconnected from gamepad")
            except Exception as e:
                logger.error(f"Error disconnecting from gamepad: {e}")
            finally:
                self.gamepad = None

    def is_connected(self) -> bool:
        """Check if gamepad is connected."""
        return self.gamepad is not None

    def calibrate(self) -> None:
        """Calibrate the gamepad (not needed)."""
        # No calibration needed for gamepad
        pass

    def is_calibrated(self) -> bool:
        """Check if gamepad is calibrated."""
        # Gamepad doesn't require calibration
        return True

    def configure(self) -> None:
        """Configure the gamepad."""
        # No additional configuration needed
        pass

    def send_feedback(self, feedback: dict) -> None:
        """Send feedback to the gamepad (not supported)."""
        # Gamepad doesn't support feedback
        pass
