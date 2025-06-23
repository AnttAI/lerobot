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

"""
Example script demonstrating how to use the Tara dual-arm robot.

This script shows basic usage including:
- Creating a Tara robot configuration
- Connecting to both arms
- Getting observations from both arms
- Sending coordinated actions to both arms
- Disconnecting safely

Usage:
    python examples/tara_example.py
"""

import time
from dataclasses import dataclass

from lerobot.common.cameras import OpenCVCameraConfig
from lerobot.common.robots.tara import Tara, TaraConfig


def create_tara_config() -> TaraConfig:
    """Create a sample Tara configuration."""
    return TaraConfig(
        # Adjust these ports based on your actual hardware setup
        left_port="/dev/ttyUSB0",
        right_port="/dev/ttyUSB1",
        
        # Safety settings
        max_relative_target=10,  # Limit motor movement for safety
        
        # Camera setup (optional)
        cameras={
            "left_wrist": OpenCVCameraConfig(
                camera_index=0,
                fps=30,
                width=640,
                height=480,
            ),
            "right_wrist": OpenCVCameraConfig(
                camera_index=1,
                fps=30,
                width=640,
                height=480,
            ),
        },
        
        # Calibration directory
        calibration_dir="/tmp/tara_calibration",
    )


def main():
    """Main example function."""
    print("Tara Dual-Arm Robot Example")
    print("=" * 30)
    
    # Create robot configuration
    config = create_tara_config()
    print(f"Created Tara config with ports: {config.left_port}, {config.right_port}")
    
    # Initialize robot
    tara = Tara(config)
    print("Initialized Tara robot")
    
    try:
        # Connect to robot (this will also calibrate if needed)
        print("Connecting to Tara...")
        tara.connect(calibrate=True)
        print("Successfully connected!")
        
        # Get initial observation
        print("\nGetting initial observation...")
        obs = tara.get_observation()
        
        # Print motor positions
        print("Current motor positions:")
        for key, value in obs.items():
            if key.endswith(".pos"):
                print(f"  {key}: {value:.2f}")
        
        # Print camera info
        camera_keys = [key for key in obs.keys() if not key.endswith(".pos")]
        if camera_keys:
            print(f"Camera feeds available: {camera_keys}")
        
        # Example: Send a simple coordinated action
        print("\nSending coordinated action...")
        
        # Create a simple action that moves both arms slightly
        action = {}
        for motor_key in obs.keys():
            if motor_key.endswith(".pos"):
                # Small movement for demonstration (adjust as needed)
                current_pos = obs[motor_key]
                if "gripper" in motor_key:
                    # Keep grippers in current position
                    action[motor_key] = current_pos
                else:
                    # Small coordinated movement
                    action[motor_key] = current_pos + 0.1
        
        # Send the action
        sent_action = tara.send_action(action)
        print("Action sent successfully!")
        
        # Wait a bit to see the movement
        time.sleep(2.0)
        
        # Get final observation
        print("\nGetting final observation...")
        final_obs = tara.get_observation()
        
        print("Final motor positions:")
        for key, value in final_obs.items():
            if key.endswith(".pos"):
                print(f"  {key}: {value:.2f}")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        
    finally:
        # Always disconnect safely
        if tara.is_connected:
            print("\nDisconnecting from Tara...")
            tara.disconnect()
            print("Disconnected successfully!")


if __name__ == "__main__":
    main()