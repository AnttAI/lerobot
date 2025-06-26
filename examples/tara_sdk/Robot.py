import time
import math
import minimalmodbus
import logging

class Robot:
    def __init__(self, port='/dev/ttyUSB0', slave_id=1, baudrate=115200, debug=False, max_position_counts=20480):
        self.port = port
        self.slave_id = slave_id
        self.baudrate = baudrate
        self.debug = debug
        self.max_position_counts = max_position_counts  # Maximum motor position in counts
        self.instrument = None
        self.connected = False
        
        # Configure logging for debug mode
        if self.debug:
            logging.basicConfig(level=logging.DEBUG)
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.INFO)

    def connect(self):
        if not self.connected:
            try:
                self.instrument = minimalmodbus.Instrument(self.port, self.slave_id)
                self.instrument.serial.baudrate = self.baudrate
                self.instrument.serial.bytesize = 8
                self.instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
                self.instrument.serial.stopbits = 1
                self.instrument.serial.timeout = 1
                self.instrument.mode = minimalmodbus.MODE_RTU
                
                # Enable debug mode if requested
                if self.debug:
                    self.instrument.debug = True
                    self.logger.debug(f"MODBUS debug enabled for {self.port}")
                
                # Test connection by reading a register
                if self.debug:
                    self.logger.debug("Testing connection by reading control register 0x200E")
                self.instrument.read_register(0x200E)
                
                self.connected = True
                print(f"Robot connected to {self.port} (slave {self.slave_id})")
            except Exception as e:
                print(f"Connection failed: {e}")
                self.connected = False
        else:
            print("Already connected.")

    def capture_observation(self):
        if self.connected and self.instrument:
            try:
                if self.debug:
                    self.logger.debug("Reading motor positions...")
                
                # Read actual motor positions (32-bit values split across 16-bit registers)
                # Left motor position
                if self.debug:
                    self.logger.debug("Reading left motor position registers 0x20A7/0x20A8")
                left_pos_high = self.instrument.read_register(0x20A7)
                left_pos_low = self.instrument.read_register(0x20A8)
                left_position = (left_pos_high << 16) | left_pos_low
                
                if self.debug:
                    self.logger.debug(f"Left motor raw: high=0x{left_pos_high:04X}, low=0x{left_pos_low:04X}, combined=0x{left_position:08X}")
                
                # Convert from unsigned to signed 32-bit
                if left_position >= 0x80000000:
                    left_position -= 0x100000000
                
                # Right motor position  
                if self.debug:
                    self.logger.debug("Reading right motor position registers 0x20A9/0x20AA")
                right_pos_high = self.instrument.read_register(0x20A9)
                right_pos_low = self.instrument.read_register(0x20AA)
                right_position = (right_pos_high << 16) | right_pos_low
                
                if self.debug:
                    self.logger.debug(f"Right motor raw: high=0x{right_pos_high:04X}, low=0x{right_pos_low:04X}, combined=0x{right_position:08X}")
                
                # Convert from unsigned to signed 32-bit
                if right_position >= 0x80000000:
                    right_position -= 0x100000000
                
                observation = {
                    'left_motor_position': left_position,
                    'right_motor_position': right_position
                }
                
                if self.debug:
                    self.logger.debug(f"Final positions - Left: {left_position}, Right: {right_position}")
                
                print(f"Current positions - Left: {left_position}, Right: {right_position}")
                return observation
                
            except Exception as e:
                print(f"Failed to read motor positions: {e}")
                return None
        else:
            print("Robot not connected.")
            return None

    def send_action(self, left_target, right_target):
        """
        Send position commands to both motors
        
        Args:
            left_target: Target position for left motor (-100 to 100)
            right_target: Target position for right motor (-100 to 100)
        
        Returns:
            bool: True if command sent successfully, False otherwise
        """
        if not self.connected or not self.instrument:
            print("Robot not connected.")
            return False
        
        # Validate input range
        if not (-100 <= left_target <= 100) or not (-100 <= right_target <= 100):
            print("Target position must be between -100 and 100")
            return False
        
        try:
            # Convert from -100/100 range to motor counts
            left_counts = int((left_target / 100.0) * self.max_position_counts)
            right_counts = int((right_target / 100.0) * self.max_position_counts)
            
            if self.debug:
                self.logger.debug(f"Converting targets: left {left_target} -> {left_counts} counts, right {right_target} -> {right_counts} counts")
            
            # Initialize position control mode if needed
            self._initialize_position_control()
            
            # Set target positions (32-bit values split into 16-bit registers)
            self._write_position(left_counts, 0x208A, 0x208B, "Left")   # Left motor
            self._write_position(right_counts, 0x208C, 0x208D, "Right") # Right motor
            
            # Enable motors and start movement
            if self.debug:
                self.logger.debug("Enabling motors and starting movement")
            
            # Enable motor
            self.instrument.write_register(0x200E, 0x08)
            
            # Start movement (synchronous mode)
            self.instrument.write_register(0x200E, 0x10)
            
            print(f"Sent position commands - Left: {left_target} ({left_counts} counts), Right: {right_target} ({right_counts} counts)")
            return True
            
        except Exception as e:
            print(f"Failed to send action: {e}")
            if self.debug:
                self.logger.error(f"send_action failed: {e}")
            return False
    
    def _initialize_position_control(self):
        """Initialize the motor controller for position control mode"""
        if self.debug:
            self.logger.debug("Initializing position control mode")
        
        # Set asynchronous control mode
        self.instrument.write_register(0x200F, 0x01)
        
        # Set position mode (relative)
        self.instrument.write_register(0x200D, 0x01)
        
        # Set default acceleration/deceleration times (500ms)
        self.instrument.write_register(0x2080, 500)  # Left acceleration
        self.instrument.write_register(0x2081, 500)  # Right acceleration  
        self.instrument.write_register(0x2082, 500)  # Left deceleration
        self.instrument.write_register(0x2083, 500)  # Right deceleration
        
        # Set default target speeds (120 RPM)
        self.instrument.write_register(0x208E, 120)  # Left speed
        self.instrument.write_register(0x208F, 120)  # Right speed
    
    def _write_position(self, position, high_reg, low_reg, motor_name):
        """Write a 32-bit position value to two 16-bit registers"""
        
        # Convert signed to unsigned 32-bit if negative
        if position < 0:
            position = position + 0x100000000
        
        # Split 32-bit value into high and low 16-bit parts
        high_value = (position >> 16) & 0xFFFF
        low_value = position & 0xFFFF
        
        if self.debug:
            self.logger.debug(f"{motor_name} motor position: 0x{position:08X} -> high: 0x{high_value:04X}, low: 0x{low_value:04X}")
        
        # Write to registers
        self.instrument.write_register(high_reg, high_value)
        self.instrument.write_register(low_reg, low_value)

    def disconnect(self):
        if self.connected:
            # Send stop command to motors before disconnecting
            if self.instrument and self.instrument.serial.is_open:
                try:
                    if self.debug:
                        self.logger.debug("Sending stop command to motors before disconnect")
                    self.instrument.write_register(0x200E, 0x07)  # Stop command
                except Exception as e:
                    print(f"Warning: Failed to send stop command during disconnect: {e}")
                    if self.debug:
                        self.logger.error(f"Stop command failed: {e}")
                
                # Close the serial connection
                self.instrument.serial.close()
            self.connected = False
            print("Robot disconnected.")
        else:
            print("Robot already disconnected.")
            return

        print("Disconnecting from robot")

        # Optional: send stop command to motors (8206 to 0x200E)
        self.instrument.write_register(0x200E, 7, 0, 6)

        self.is_connected = False
        print("Robot disconnected.")

    def push_command(self, action: dict) -> None:
        print("Pushing command to robot - updated")
        print(action)

        self.state_x = action.get("key_x", self.state_x)
        self.state_y = action.get("key_y", self.state_y)
        self.state_theta = action.get("key_t", self.state_theta)

        self.send_motor_commands(self.state_y, self.state_theta)

        print("current x, y, theta", self.state_x, self.state_y, self.state_theta)

    def send_motor_commands(self, key_y, key_t):
        wheel_radius = 0.2  # meters
        wheel_base = 0.157  # meters

        linear_velocity = key_y  # m/s
        angular_velocity = math.radians(key_t)  # deg/s to rad/s

        v_left = linear_velocity - (wheel_base / 2.0) * angular_velocity
        v_right = linear_velocity + (wheel_base / 2.0) * angular_velocity

        left_rpm = (v_left / (2 * math.pi * wheel_radius)) * 60
        right_rpm = (v_right / (2 * math.pi * wheel_radius)) * 60

        MAX_RPM = 10
        if abs(left_rpm) > MAX_RPM or abs(right_rpm) > MAX_RPM:
            print(f"RPM too high! Left: {left_rpm:.2f}, Right: {right_rpm:.2f}")
            print("Not sending motor commands to protect the motors.")
            return

        print(f"Calculated RPMs -> Left: {left_rpm:.2f}, Right: {right_rpm:.2f}")

        # Uncomment below lines when instrument is properly configured
        # Converting (8328,8329 to 0x2088,0x2089)
        self.instrument.write_register(0x2088, int(left_rpm), 0, 6, True)
        self.instrument.write_register(0x2089, -1 * int(right_rpm), 0, 6, True)

    

