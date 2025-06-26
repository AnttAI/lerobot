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

from ..config import TeleoperatorConfig


@TeleoperatorConfig.register_subclass("gamepadtara")
@dataclass
class GamepadTaraConfig(TeleoperatorConfig):
    """Configuration for GamepadTara teleoperator that controls TaraBase robots.
    
    This teleoperator uses a gamepad controller to send normalized movement 
    commands (-1.0 to 1.0) to the TaraBase robot. The robot's configuration 
    handles the actual speed limits.
    """
    
    # Input deadzone - ignore small inputs to prevent drift
    deadzone: float = 0.1  # Values below this threshold are considered zero
