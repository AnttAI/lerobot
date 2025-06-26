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

from dataclasses import dataclass

from ..config import RobotConfig


@RobotConfig.register_subclass("tarabase")
@dataclass
class TaraBaseConfig(RobotConfig):
    """
    Configuration for TaraBase robot that uses the TaraSDK for control.
    
    This robot provides a mobile base platform controlled through a gamepad.
    """
    
    # Port ID for the robot base (e.g., /dev/ttyUSB0, COM3, etc.)
    port: str = ""
    

    # Speed control parameters
    max_linear_speed: float = 1.0  # Maximum linear speed in m/s
    max_angular_speed: float = 1.0  # Maximum angular speed in rad/s
    
    # Safety settings
    emergency_stop_enabled: bool = True
