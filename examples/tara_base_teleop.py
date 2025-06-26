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

import time
import sys
import signal
import logging
import argparse

# Import the gamepad-related classes
from lerobot.common.teleoperators.gamepad import GamepadTeleop, GamepadTeleopConfig

# Import the TaraBase robot class
from lerobot.common.robots import TaraBaseConfig, TaraBase

# Try to import any potentially needed dependencies
try:
    import pygame  # This may be needed for the gamepad functionality
except ImportError:
    print("Warning: pygame module not found. You may need to install it with: pip install pygame")

# Set up logging
logging.basicConfig(level=logging.INFO)


def signal_handler(sig, frame):
    """Handle Ctrl+C to clean up resources."""
    print("\nExiting gamepad controller...")
    sys.exit(0)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Control TaraBase robot using a gamepad.")
    parser.add_argument("--port", type=str, default="/dev/ttyUSB0",
                        help="Port ID of the TaraBase robot (e.g., /dev/ttyUSB0, COM3)")
    parser.add_argument("--max-speed", type=float, default=0.5,
                        help="Maximum linear speed in m/s (default: 0.5)")
    parser.add_argument("--max-angular", type=float, default=0.8,
                        help="Maximum angular speed in rad/s (default: 0.8)")
    parser.add_argument("--gamepad-index", type=int, default=0,
                        help="Index of the gamepad to use (default: 0)")
    return parser.parse_args()


def main():
    # Parse command line arguments
    args = parse_args()
    
    # Set up gamepad teleoperator configuration
    teleop_config = GamepadTeleopConfig(
        use_gripper=False,  # Set to False if your base doesn't have a gripper
    )
    
    # Set up TaraBase robot configuration
    robot_config = TaraBaseConfig(
        id="tarabase",
        port=args.port,
        max_linear_speed=args.max_speed,
        max_angular_speed=args.max_angular,
        emergency_stop_enabled=True
    )
    
    # Initialize teleoperator
    try:
        teleop = GamepadTeleop(teleop_config)
        print("Attempting to connect to gamepad...")
        teleop.connect()
        
        if not teleop.is_connected():
            print("Failed to connect to gamepad. Please check your connection.")
            return
    except Exception as e:
        print(f"Error initializing gamepad: {str(e)}")
        return
    
    # Initialize robot
    try:
        robot = TaraBase(robot_config)
        print(f"Attempting to connect to TaraBase on port {args.port}...")
        robot.connect()
        
        if not robot.is_connected():
            print("Failed to connect to TaraBase robot. Please check the connection.")
            teleop.disconnect()
            return
    except Exception as e:
        print(f"Error connecting to TaraBase: {str(e)}")
        teleop.disconnect()
        return
    
    print("\nGamepad and TaraBase robot connected successfully!")
    print("Use gamepad to control the robot:")
    print("- Left stick: Move forward/backward (X) and sideways (Y)")
    print("- Right stick: Rotate (angular Z)")
    print("Press Ctrl+C to exit.")
    
    # Main loop
    try:
        while True:
            # Make sure gamepad is updated before getting action
            if hasattr(teleop, "gamepad") and teleop.gamepad is not None:
                teleop.gamepad.update()
                
            # Get action from gamepad
            teleop_action = teleop.get_action()
            
            # Map gamepad controls to robot movement commands
            robot_action = {
                "linear_x": teleop_action.get("delta_x", 0.0),    # Forward/backward
                "linear_y": teleop_action.get("delta_y", 0.0),    # Left/right
                "angular_z": teleop_action.get("delta_z", 0.0)    # Rotation
            }
            
            # Send the action to the robot
            robot.send_action(robot_action)
            time.sleep(0.05)  # Default sleep time
            # Get robot state feedback
            robot_state = robot.get_observation()
            
            # Clear line and print controls and robot state
            sys.stdout.write("\r" + " " * 100 + "\r")  # Clear line
            
            # Format the output nicely - show both gamepad inputs and robot state
            status = "Gamepad: "
            for key, value in teleop_action.items():
                if key.startswith("delta") and abs(value) > 0.01:
                    status += f"{key}={value:.2f} "
                elif not key.startswith("delta"):
                    status += f"{key}={value} "
                    
            status += " | Robot: "
            status += f"speed_x={robot_state['current_linear_x']:.2f} "
            status += f"speed_y={robot_state['current_linear_y']:.2f} "
            status += f"angular={robot_state['current_angular_z']:.2f}"
            
            sys.stdout.write(status)
            sys.stdout.flush()
            
            time.sleep(0.05)  # Small delay to prevent high CPU usage
            
    except KeyboardInterrupt:
        print("\nExiting controller...")
    except Exception as e:
        print(f"\nError during operation: {e}")
    finally:
        # Clean up - stop robot and disconnect everything
        print("\nStopping robot and disconnecting...")
        try:
            robot.emergency_stop()  # Emergency stop for safety
            robot.disconnect()
            print("Robot disconnected.")
        except Exception as e:
            print(f"Error disconnecting robot: {e}")
            
        try:
            teleop.disconnect()
            print("Gamepad disconnected.")
        except Exception as e:
            print(f"Error disconnecting gamepad: {e}")
            


if __name__ == "__main__":
    # Register signal handler for clean exits
    signal.signal(signal.SIGINT, signal_handler)
    main()
