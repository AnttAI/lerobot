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

@dataclass
class TaraSingleClientConfig:
    """
    Configuration for Tara Single Client.
    """

    # Network Configuration
    remote_ip: str
    port_zmq_cmd: int = 6001
    port_zmq_observations: int = 6002

    # Polling and connection timeouts
    polling_timeout_ms: int = 15