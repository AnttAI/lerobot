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

import base64
import json
import logging
import time

import cv2
import zmq

# Key difference: Importing the SINGLE arm robot
from lerobot.common.robots.tara.tara_single import TaraSingle
from lerobot.common.robots.tara.config_tara_single import TaraSingleConfig

class TaraSingleHostConfig:
    port_zmq_cmd = 6001
    port_zmq_observations = 6002
    watchdog_timeout_ms = 2000
    max_loop_freq_hz = 20


class TaraSingleHost:
    def __init__(self, config: TaraSingleHostConfig):
        self.zmq_context = zmq.Context()
        self.zmq_cmd_socket = self.zmq_context.socket(zmq.PULL)
        self.zmq_cmd_socket.setsockopt(zmq.CONFLATE, 1)
        self.zmq_cmd_socket.bind(f"tcp://*:{config.port_zmq_cmd}")

        self.zmq_observation_socket = self.zmq_context.socket(zmq.PUSH)
        self.zmq_observation_socket.setsockopt(zmq.CONFLATE, 1)
        self.zmq_observation_socket.bind(f"tcp://*:{config.port_zmq_observations}")

        self.watchdog_timeout_ms = config.watchdog_timeout_ms
        self.max_loop_freq_hz = config.max_loop_freq_hz

    def disconnect(self):
        self.zmq_observation_socket.close()
        self.zmq_cmd_socket.close()
        self.zmq_context.term()


def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Configuring Tara Single follower robot...")
    # Key difference: Using the SINGLE arm config
    robot_config = TaraSingleConfig(port="/dev/ttyACM0")
    robot = TaraSingle(robot_config)

    logging.info("Connecting to Tara Single follower robot...")
    robot.connect()

    logging.info("Starting Tara Single Host...")
    host_config = TaraSingleHostConfig()
    host = TaraSingleHost(host_config)

    last_cmd_time = time.time()
    watchdog_active = False
    logging.info("Waiting for commands...")
    try:
        while True:
            loop_start_time = time.time()
            try:
                msg = host.zmq_cmd_socket.recv_string(zmq.NOBLOCK)
                data = dict(json.loads(msg))
                robot.send_action(data)
                last_cmd_time = time.time()
                watchdog_active = False
            except zmq.Again:
                pass  # No new command
            except Exception as e:
                logging.error(f"Message fetching or execution failed: {e}")

            now = time.time()
            if (now - last_cmd_time > host.watchdog_timeout_ms / 1000) and not watchdog_active:
                logging.warning(
                    f"Command not received for more than {host.watchdog_timeout_ms} ms. Stopping motors."
                )
                watchdog_active = True
                # Key difference: Disabling torque on a single bus
                robot.bus.disable_torque()

            last_observation = robot.get_observation()

            for cam_key, image in last_observation.items():
                if "camera" in cam_key:
                    ret, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                    if ret:
                        last_observation[cam_key] = base64.b64encode(buffer).decode("utf-8")
                    else:
                        last_observation[cam_key] = ""

            try:
                host.zmq_observation_socket.send_string(json.dumps(last_observation), flags=zmq.NOBLOCK)
            except zmq.Again:
                logging.info("Dropping observation, no client connected")

            elapsed = time.time() - loop_start_time
            time.sleep(max(1 / host.max_loop_freq_hz - elapsed, 0))

    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting...")
    finally:
        print("Shutting down Tara Single Host.")
        robot.disconnect()
        host.disconnect()

    logging.info("Finished Tara Single Host cleanly")


if __name__ == "__main__":
    main()