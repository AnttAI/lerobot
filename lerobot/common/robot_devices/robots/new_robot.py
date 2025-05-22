from lerobot.common.robot_devices.robots.manipulator import ManipulatorRobot
# The following import will create a circular dependency if new_robot_calibration.py
# imports NewRobot at the top level for type hinting.
# This is acceptable if type checking is static or imports are managed (e.g., inside methods/functions).
from lerobot.common.robot_devices.robots.new_robot_calibration import run_new_robot_calibration


class NewRobot(ManipulatorRobot):
    """A new robot class."""

    def __init__(self, config):
        """Initialize NewRobot."""
        super().__init__(config)
        # TODO(user): Add NewRobot specific initialization
        raise NotImplementedError

    def connect(self):
        """Connect to NewRobot."""
        # Run calibration before connecting to the robot
        run_new_robot_calibration(self, self.config)
        super().connect()
        # TODO(user): Add NewRobot specific connection logic
        raise NotImplementedError

    def disconnect(self):
        """Disconnect from NewRobot."""
        super().disconnect()
        # TODO(user): Add NewRobot specific disconnection logic
        raise NotImplementedError

    def teleop_step(self):
        """Perform a teleoperation step for NewRobot."""
        super().teleop_step()
        # TODO(user): Add NewRobot specific teleoperation logic
        raise NotImplementedError

    def capture_observation(self):
        """Capture an observation from NewRobot."""
        super().capture_observation()
        # TODO(user): Add NewRobot specific observation capturing logic
        raise NotImplementedError

    def send_action(self, action):
        """Send an action to NewRobot."""
        super().send_action(action)
        # TODO(user): Add NewRobot specific action sending logic
        raise NotImplementedError
