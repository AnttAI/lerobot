import pytest
import os
from pathlib import Path

from lerobot.common.robot_devices.robots import NewRobot, NewRobotConfig
from lerobot.common.robot_devices.utils import RobotDeviceAlreadyConnectedError, RobotDeviceNotConnectedError
from tests.utils import mock_calibration_dir # For setting up calibration_dir


def test_new_robot_lifecycle(tmp_path):
    """
    Tests the basic lifecycle of NewRobot, including instantiation,
    connection/disconnection (handling NotImplementedError), and calibration file creation.
    """
    # 1. Create NewRobotConfig with mock=True and a temporary calibration_dir
    # tmp_path is a pytest fixture providing a Path object to a temporary directory
    calibration_dir = tmp_path / "new_robot_calibration"
    # mock_calibration_dir(calibration_dir) # Not strictly needed if we just give the path
                                         # but good if the robot expects it to exist.
                                         # NewRobot's calibration function creates it.

    robot_config = NewRobotConfig(
        mock=True,  # Essential for testing without real hardware
        calibration_dir=str(calibration_dir), # Ensure it's a string if the config expects it
    )

    # 2. Instantiate NewRobot
    robot = NewRobot(config=robot_config)
    assert robot is not None, "NewRobot instance should be created."
    assert not robot.is_connected, "Robot should not be connected initially."

    # 3. Test methods before connection (expect RobotDeviceNotConnectedError)
    with pytest.raises(RobotDeviceNotConnectedError):
        robot.teleop_step()
    with pytest.raises(RobotDeviceNotConnectedError):
        robot.capture_observation()
    with pytest.raises(RobotDeviceNotConnectedError):
        robot.send_action({}) # Dummy action
    with pytest.raises(RobotDeviceNotConnectedError):
        robot.disconnect()

    # 4. Test connect()
    # NewRobot.connect() calls run_new_robot_calibration and then raises NotImplementedError.
    # run_new_robot_calibration should create the calibration directory and a dummy file.
    with pytest.raises(NotImplementedError, match="TODO\(user\): Add NewRobot specific connection logic"):
        robot.connect()

    # After the connect attempt, even if it raised NotImplementedError for specific logic,
    # the initial parts of connect (like setting self._connected = True in a parent) might have run.
    # However, for NewRobot, super().connect() which sets self._connected = True
    # is called *after* run_new_robot_calibration and *before* the NotImplementedError.
    # But since the calibration itself is part of connect, and connect fails with NotImplementedError,
    # we need to decide what the state of `is_connected` should be.
    # If super().connect() is called before the error, it might be True.
    # If the error happens before super().connect(), it should be False.
    # In NewRobot's current connect():
    #   run_new_robot_calibration(self, self.config)
    #   super().connect()  <-- This sets self._connected = True
    #   raise NotImplementedError
    # So, is_connected should be True if super().connect() was reached.
    assert robot.is_connected, "Robot should be marked as connected after connect() started, even if partially implemented."


    # Check that calibration directory and dummy file were created
    assert calibration_dir.exists(), "Calibration directory should be created."
    dummy_file = calibration_dir / "dummy_calibration.json"
    assert dummy_file.exists(), "Dummy calibration file should be created."
    assert dummy_file.is_file()

    # 5. Test connecting twice (if the first connect attempt partially succeeded)
    # This depends on whether the first connect() call (that raised NotImplementedError)
    # actually set the robot to a connected state.
    # Given NewRobot's structure, super().connect() is called before the NotImplementedError.
    if robot.is_connected:
         with pytest.raises(RobotDeviceAlreadyConnectedError):
            robot.connect()

    # 6. Test disconnect()
    # NewRobot.disconnect() also raises NotImplementedError after super().disconnect()
    with pytest.raises(NotImplementedError, match="TODO\(user\): Add NewRobot specific disconnection logic"):
        robot.disconnect()

    # Similar to connect(), super().disconnect() is called before the NotImplementedError.
    # So, is_connected should be False.
    assert not robot.is_connected, "Robot should be marked as disconnected after disconnect(), even if partially implemented."

    # Test deleting the object after operations
    del robot
