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


@TeleoperatorConfig.register_subclass("tara_leader")
@dataclass
class TaraLeaderConfig(TeleoperatorConfig):
    """
    Configuration for Tara dual-arm leader teleoperator using two SO101 leader arms.
    """
    
    # Ports to connect to the left and right leader arms
    left_port: str
    right_port: str

    # Set to `True` for backward compatibility with previous policies/dataset
    use_degrees: bool = False