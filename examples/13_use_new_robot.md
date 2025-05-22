---
title: Get started with NewRobot
emoji: 🤖
meta:
    title: Get started with NewRobot | LeRobot
    description: This page provides a guide for setting up and using NewRobot with LeRobot.
---

# Get started with `NewRobot`

This page guides you through the basic setup and usage of `NewRobot` with the `LeRobot` framework. `NewRobot` is a conceptual robot class added to demonstrate how new robots can be integrated.

## 1. Prerequisites

- Ensure you have `LeRobot` installed and configured.
- If `NewRobot` had actual hardware dependencies (e.g., specific SDKs, drivers), they would need to be installed. For this example, `NewRobot` is a placeholder.

## 2. Configuration

Robot configurations are managed via YAML files or directly through Python using `draccus` with dataclasses. `NewRobot` uses `NewRobotConfig`.

A typical configuration for `NewRobot` might look like this if saved in a YAML file (e.g., `new_robot_config.yaml`):

```yaml
# lerobot/configs/robot/new_robot.yaml
# This is a conceptual path; actual config would be loaded by your script

# Inherits from ManipulatorRobotConfig
# type identifies the robot
type: new_robot

# Calibration directory (inherited and overridden)
calibration_dir: "~/.cache/lerobot/calibration/new_robot/"

# Example: Define leader and follower arms (if applicable)
# These would be specific to NewRobot's hardware if it were real.
# For this placeholder, we'll assume it might have Dynamixel motors.
# leader_arms:
#   main:
#     # Assuming Dynamixel motors for this conceptual robot
#     type: dynamixel_motors_bus
#     port: "/dev/ttyDXL_leader" # Replace with actual port
#     motors:
#       joint1: [1, "xl430-w250"]
#       joint2: [2, "xl430-w250"]
#       # ... other joints

# follower_arms:
#   main:
#     type: dynamixel_motors_bus
#     port: "/dev/ttyDXL_follower" # Replace with actual port
#     motors:
#       joint1: [1, "xm540-w270"]
#       joint2: [2, "xm540-w270"]
#       # ... other joints

# Example: Define cameras (if applicable)
# cameras:
#   overview_camera:
#     type: opencv_camera # or realsense_camera
#     camera_index: 0 # or serial_number for RealSense
#     fps: 30
#     width: 640
#     height: 480

# Mock mode for simulation without real hardware
mock: true
```

You would typically load this using a script that employs `draccus` or by instantiating the config class directly.

## 3. Basic Usage (Python Script)

Here's a conceptual Python script demonstrating how to instantiate and use `NewRobot`:

```python
from lerobot.common.robot_devices.robots import NewRobot, NewRobotConfig
from lerobot.common.robot_devices.robots.utils import make_robot_from_config

def main():
    # Option 1: Create config directly
    print("Creating NewRobotConfig directly...")
    robot_config = NewRobotConfig(
        # Since NewRobot is a placeholder, we'll enable mock mode.
        # If it were a real robot, you'd configure ports, motors, cameras, etc.
        mock=True,
        # Other parameters like leader_arms, follower_arms, cameras would be set here
        # For example, if NewRobot had a simple arm:
        # leader_arms={"main": DynamixelMotorsBusConfig(port="/dev/ttyFAKE", motors={"j1": [1, "xl320"]})}
        # follower_arms={"main": DynamixelMotorsBusConfig(port="/dev/ttyFAKE", motors={"j1": [1, "xl320"]})}
    )

    # Option 2: Load config using make_robot_config (if registered and using type string)
    # from lerobot.common.robot_devices.robots.utils import make_robot_config
    # print("Creating NewRobotConfig via make_robot_config...")
    # robot_config = make_robot_config(robot_type="new_robot", mock=True)


    print(f"Using robot config: {robot_config}")

    # Create NewRobot instance using the configuration
    # The factory make_robot_from_config can also be used:
    # robot = make_robot_from_config(robot_config)
    # Or instantiate directly:
    print("Creating NewRobot instance...")
    robot = NewRobot(config=robot_config)

    try:
        print("Connecting to NewRobot...")
        # The connect method in the placeholder NewRobot calls calibration
        # and then raises NotImplementedError. We expect this.
        try:
            robot.connect()
        except NotImplementedError:
            print("Caught expected NotImplementedError from connect() during placeholder usage.")
        except Exception as e:
            print(f"An unexpected error occurred during connect: {e}")
            return # Exit if connection truly fails beyond placeholder

        # If connect were fully implemented and successful:
        # print("Successfully connected to NewRobot.")

        # Example: Capture an observation
        # print("Capturing observation...")
        # try:
        #     observation = robot.capture_observation()
        #     print(f"Observation captured: {observation}")
        # except NotImplementedError:
        #     print("capture_observation() is not yet implemented for NewRobot.")
        # except Exception as e:
        #     print(f"Error capturing observation: {e}")

        # Placeholder for teleoperation step
        # print("Performing teleoperation step...")
        # try:
        #     robot.teleop_step()
        # except NotImplementedError:
        #     print("teleop_step() is not yet implemented for NewRobot.")
        # except Exception as e:
        #     print(f"Error in teleop_step: {e}")

        # Placeholder for sending an action
        # print("Sending action...")
        # try:
        #     # Define a dummy action based on NewRobot's expected action space
        #     # This is highly dependent on the robot's design.
        #     # Assuming a simple action dictionary for a manipulator:
        #     action = {"joint_control": [0.1, -0.1, 0.0, 0.0, 0.0, 0.0]} # Example action
        #     robot.send_action(action)
        # except NotImplementedError:
        #     print("send_action() is not yet implemented for NewRobot.")
        # except Exception as e:
        #     print(f"Error sending action: {e}")

    finally:
        print("Disconnecting from NewRobot...")
        try:
            robot.disconnect()
        except NotImplementedError:
            print("Caught expected NotImplementedError from disconnect() during placeholder usage.")
        except Exception as e:
            print(f"Error disconnecting: {e}")
        else:
            print("Successfully disconnected (or disconnect is a no-op/placeholder).")

if __name__ == "__main__":
    main()
```

This script shows the basic lifecycle:
1.  Create a `NewRobotConfig`.
2.  Instantiate `NewRobot` with this config.
3.  Call `connect()`.
4.  Conceptually call methods like `capture_observation()`, `teleop_step()`, `send_action()`.
5.  Call `disconnect()`.

Since `NewRobot`'s methods are placeholders and raise `NotImplementedError`, the example anticipates this.

## 4. Calibration

The `NewRobot`'s `connect` method is set up to call `run_new_robot_calibration(self, self.config)`.
The placeholder `run_new_robot_calibration` function currently:
- Prints a message.
- Ensures the directory specified in `config.calibration_dir` (default `~/.cache/lerobot/calibration/new_robot/`) exists.
- Saves a dummy file `dummy_calibration.json` there.

If `NewRobot` were a real robot, this calibration step would involve actual hardware interaction to determine joint offsets, camera intrinsics, etc.

## 5. Next Steps

- Implement the `TODO(user)` sections in `lerobot/common/robot_devices/robots/new_robot.py` with actual hardware interaction logic.
- Fill in the `run_new_robot_calibration` function in `lerobot/common/robot_devices/robots/new_robot_calibration.py` with the robot-specific calibration procedures.
- Develop more comprehensive examples and tests as the implementation progresses.

This example provides a starting point for integrating and using `NewRobot` within the `LeRobot` ecosystem.
---

This markdown provides a conceptual overview. Users would replace placeholder logic with actual hardware interactions for a real robot.
