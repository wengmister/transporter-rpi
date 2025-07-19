# Xbox Controller VESC Robot Controller - Setup Instructions

## Prerequisites

1. **Raspberry Pi 4** with Raspberry Pi OS installed
2. **Xbox Controller** (Xbox 360, Xbox One, or Xbox Series X/S)
3. **USB cable** to connect controller to Pi
4. **Display** connected to Pi (HDMI monitor or Pi touchscreen)
5. **Two VESC motor controllers** connected via USB (/dev/ttyACM0 and /dev/ttyACM1)
6. **Differential drive robot** with motors connected to VESCs

## Installation Steps

### 1. Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Required Packages
```bash
# Install pygame dependencies
sudo apt install python3-pygame python3-pip -y

# Install PyVESC for motor control
pip3 install pygame pyvesc

# Alternative method if pygame isn't available via apt:
# pip3 install pygame pyvesc
```

### 3. Set Up Controller Permissions
```bash
# Add your user to the input group to access joystick
sudo usermod -a -G input $USER

# Create udev rule for Xbox controllers (optional but recommended)
sudo nano /etc/udev/rules.d/99-xbox-controller.rules
```

Add this line to the file:
```
SUBSYSTEM=="input", ATTRS{idVendor}=="045e", MODE="0666"
```

Then reload udev rules:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 4. Test Controller and VESC Connection
```bash
# Check if controller is detected
lsusb | grep -i xbox

# Check VESC connections
ls /dev/ttyACM*

# Test joystick detection
python3 -c "
import pygame
pygame.init()
pygame.joystick.init()
print(f'Joysticks found: {pygame.joystick.get_count()}')
if pygame.joystick.get_count() > 0:
    j = pygame.joystick.Joystick(0)
    j.init()
    print(f'Controller: {j.get_name()}')
    print(f'Axes: {j.get_numaxes()}')
    print(f'Buttons: {j.get_numbuttons()}')
"

# Test VESC connection (optional)
python3 -c "
from pyvesc.VESC import VESC
try:
    with VESC('/dev/ttyACM0') as vesc:
        print('VESC 1 connected successfully')
    with VESC('/dev/ttyACM1') as vesc:
        print('VESC 2 connected successfully')
except Exception as e:
    print(f'VESC connection test failed: {e}')
"
```

### 5. Run the Robot Controller
```bash
# Make the script executable
chmod +x xbox_vesc_robot_controller.py

# Run the controller
python3 xbox_vesc_robot_controller.py
```

## Usage

1. **Connect your Xbox controller** via USB to the Raspberry Pi
2. **Connect VESC controllers** to /dev/ttyACM0 and /dev/ttyACM1
3. **Ensure robot is in safe area** before running
4. **Run the script** - it will auto-detect controller and VESCs
5. **Use left joystick** to control robot movement:
   - **Up/Down**: Forward/Backward
   - **Left/Right**: Turn left/right
   - **Diagonal**: Combined movement
6. **Safety controls**:
   - **B Button**: Emergency stop
   - **A Button**: Release emergency stop
   - **Spacebar**: Emergency stop (keyboard)
   - **ESC**: Exit program

## Robot Control Features

- **Differential drive logic** - converts joystick to left/right motor speeds
- **Real-time visualization** of joystick input and motor outputs
- **Emergency stop system** with multiple activation methods
- **Threaded motor control** for smooth, non-blocking operation
- **Safety limits** - maximum 80% duty cycle by default
- **Deadzone handling** - ignores small joystick movements
- **Visual motor indicators** showing direction and power level

## Troubleshooting

### Controller Not Detected
- Check USB connection
- Try different USB port
- Verify controller works on another device
- Check `lsusb` output for Xbox device

### Permission Issues
- Make sure you're in the `input` group: `groups $USER`
- Try running with `sudo` (not recommended for regular use)
- Check udev rules are properly set

### VESC Connection Issues
- Check USB connections to both VESC controllers
- Verify ports: `ls /dev/ttyACM*` should show ACM0 and ACM1
- Try different USB ports
- Check VESC configuration and firmware
- Ensure VESCs are powered and motors connected
- Script will run in visualization-only mode if VESCs not connected

## Controller Compatibility

This script works with:
- Xbox 360 Controller (wired)
- Xbox One Controller (wired)
- Xbox Series X/S Controller (wired)
- Many third-party Xbox-compatible controllers

## Configuration Options

You can modify these settings in the code:

### Motor Control Settings
- `MAX_SPEED = 0.8` - Maximum motor duty cycle (0.8 = 80%)
- `SPEED_MULTIPLIER = 1.0` - Joystick sensitivity
- `DEADZONE = 0.15` - Minimum joystick movement to register
- `VESC_PORT_1/2` - USB ports for left/right motors

### Display Settings
- `WINDOW_WIDTH/HEIGHT` - Window size
- `ARROW_COLOR` - Joystick arrow color
- `MOTOR_COLOR_LEFT/RIGHT` - Motor indicator colors

### Safety Settings
- Emergency stop activated by: B button, Spacebar, or code emergency_stop flag
- Motors automatically stop on program exit
- Threaded motor control prevents blocking

## Next Steps

- Camera & Visualization
    - Object detection (YOLO)
    - Obstacle avoidance (need depth)
- Mechanical integration