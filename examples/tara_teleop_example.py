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
Example script demonstrating teleoperation of Tara dual-arm robot using Tara leader.

This script shows how to:
- Set up Tara leader teleoperator (input device) 
- Set up Tara follower robot (output device)
- Perform coordinated dual-arm teleoperation
- Handle connection/disconnection safely

Usage:
    python examples/tara_teleop_example.py
"""

import time
from dataclasses import dataclass

from lerobot.common.cameras import OpenCVCameraConfig
from lerobot.common.robots.tara import Tara, TaraConfig
from lerobot.common.teleoperators.tara_leader import TaraLeader, TaraLeaderConfig


def create_tara_leader_config() -> TaraLeaderConfig:
    """Create Tara leader configuration for teleoperation input."""
    return TaraLeaderConfig(
        # Adjust these ports based on your actual leader arm hardware setup
        left_port="/dev/ttyUSB2",   # Leader left arm port
        right_port="/dev/ttyUSB3",  # Leader right arm port
        
        # Calibration directory
        calibration_dir="/tmp/tara_leader_calibration",
    )


def create_tara_follower_config() -> TaraConfig:
    """Create Tara follower configuration for robot output."""
    return TaraConfig(
        # Adjust these ports based on your actual follower arm hardware setup
        left_port="/dev/ttyUSB0",   # Follower left arm port
        right_port="/dev/ttyUSB1",  # Follower right arm port
        
        # Safety settings - important for teleoperation
        max_relative_target=15,  # Allow larger movements for teleoperation
        
        # Camera setup for observation
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
        calibration_dir="/tmp/tara_follower_calibration",
    )


def teleoperate_step(leader: TaraLeader, follower: Tara) -> None:
    """Perform one step of teleoperation."""
    # Get action from leader arms (human input)
    leader_action = leader.get_action()
    
    # Send action to follower arms (robot output)
    follower_action = follower.send_action(leader_action)
    
    return leader_action, follower_action


def main():
    """Main teleoperation function."""
    print("Tara Dual-Arm Teleoperation Example")
    print("=" * 40)
    
    # Create configurations
    leader_config = create_tara_leader_config()
    follower_config = create_tara_follower_config()
    
    print(f"Leader ports: {leader_config.left_port}, {leader_config.right_port}")
    print(f"Follower ports: {follower_config.left_port}, {follower_config.right_port}")
    
    # Initialize devices
    leader = TaraLeader(leader_config)
    follower = Tara(follower_config)
    
    print("Initialized Tara leader and follower")
    
    try:
        # Connect leader (input device)
        print("\nConnecting to Tara leader...")
        leader.connect(calibrate=True)
        print("Leader connected!")
        
        # Connect follower (robot)
        print("Connecting to Tara follower...")
        follower.connect(calibrate=True)
        print("Follower connected!")
        
        print("\n" + "="*50)
        print("TELEOPERATION READY!")
        print("Move the leader arms to control the follower robot.")
        print("The follower will mirror the leader movements.")
        print("Press Ctrl+C to stop teleoperation.")
        print("="*50)
        
        # Teleoperation loop
        step_count = 0
        start_time = time.time()
        
        while True:
            try:
                # Perform one teleoperation step
                leader_action, follower_action = teleoperate_step(leader, follower)
                
                step_count += 1
                
                # Print status every 30 steps (roughly every second at 30Hz)
                if step_count % 30 == 0:
                    elapsed = time.time() - start_time
                    fps = step_count / elapsed
                    print(f"Teleoperation running... Steps: {step_count}, FPS: {fps:.1f}")
                    
                    # Print sample motor positions
                    print("Sample positions:")
                    for key, val in leader_action.items():
                        if "left_shoulder_pan" in key or "right_shoulder_pan" in key:
                            print(f"  {key}: {val:.2f}")
                
                # Small delay to control loop frequency
                time.sleep(1/30)  # Target 30Hz
                
            except KeyboardInterrupt:
                print("\nTeleoperation stopped by user.")
                break
        
        # Get final observations
        print("\nGetting final observations...")
        final_obs = follower.get_observation()
        print("Final follower positions:")
        for key, value in final_obs.items():
            if key.endswith(".pos"):
                print(f"  {key}: {value:.2f}")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Always disconnect safely
        print("\nDisconnecting devices...")
        
        if leader.is_connected:
            leader.disconnect()
            print("Leader disconnected")
            
        if follower.is_connected:
            follower.disconnect()
            print("Follower disconnected")
        
        print("Teleoperation complete!")


if __name__ == "__main__":
    main()