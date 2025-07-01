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

import json
import logging
import time

import zmq

# Key difference: Importing the SINGLE arm leader
from lerobot.common.teleoperators.tara_leader.tara_leader_single import TaraLeaderSingle
from lerobot.common.teleoperators.tara_leader.config_tara_leader_single import TaraLeaderSingleConfig
from examples.single_tara.config_tara_single_client import TaraSingleClientConfig

class TaraSingleClient:
    def __init__(self, config: TaraSingleClientConfig):
        self.zmq_context = zmq.Context()
        self.zmq_cmd_socket = self.zmq_context.socket(zmq.PUSH)
        self.zmq_cmd_socket.setsockopt(zmq.CONFLATE, 1)
        self.zmq_cmd_socket.connect(f"tcp://{config.remote_ip}:{config.port_zmq_cmd}")

        self.zmq_observation_socket = self.zmq_context.socket(zmq.PULL)
        self.zmq_observation_socket.setsockopt(zmq.CONFLATE, 1)
        self.zmq_observation_socket.connect(f"tcp://{config.remote_ip}:{config.port_zmq_observations}")

        self.polling_timeout_ms = config.polling_timeout_ms
        self.connect_timeout_s = 10

    def disconnect(self):
        self.zmq_observation_socket.close()
        self.zmq_cmd_socket.close()
        self.zmq_context.term()

def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Configuring Tara Single leader controller...")
    # Key difference: Using the SINGLE arm leader config
    leader_config = TaraLeaderSingleConfig(port="/dev/ttyACM0")
    leader = TaraLeaderSingle(leader_config)

    logging.info("Connecting to Tara Single leader controller...")
    leader.connect()

    logging.info("Starting Tara Single Client...")
    client_config = TaraSingleClientConfig(remote_ip="192.168.31.178")  # Replace with robot's IP
    client = TaraSingleClient(client_config)

    logging.info("Starting teleoperation loop...")
    try:
        while True:
            # 1. Get action from the leader arm
            action = leader.get_action()

            # 2. Send action to the host
            client.zmq_cmd_socket.send_string(json.dumps(action))

            # 3. (Optional) Receive and process observation from the host
            try:
                obs_string = client.zmq_observation_socket.recv_string(zmq.NOBLOCK)
                # Optionally process obs_string here
            except zmq.Again:
                pass  # No new observation

            time.sleep(0.01)  # Small delay to prevent overwhelming the network

    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting...")
    finally:
        print("Shutting down Tara Single Client.")
        leader.disconnect()
        client.disconnect()

    logging.info("Finished Tara Single Client cleanly")

if __name__ == "__main__":
    main()