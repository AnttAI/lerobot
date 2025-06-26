# Run :./examples/run_tarabase_gamepad.sh
# This script demonstrates how to run the TaraBase robot with gamepad teleoperator

echo "Running TaraBase with gamepad teleoperator..."

python -m lerobot.teleoperate \
    --robot.type=tarabase \
    --robot.port=/dev/ttyUSB0 \
    --teleop.type=gamepadtara \
    --teleop.max_wheel_speed=10 \
    --display_data=true

# The speed limits are controlled by the robot configuration, not the teleoperator
# The gamepad teleoperator simply sends normalized values (-1.0 to 1.0)