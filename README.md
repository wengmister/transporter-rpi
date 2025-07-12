# Xbox Controller Joystick Visualizer - Setup Instructions

## Prerequisites

1. **Raspberry Pi 4** with Raspberry Pi OS installed
2. **Xbox Controller** (Xbox 360, Xbox One, or Xbox Series X/S)
3. **USB cable** to connect controller to Pi
4. **Display** connected to Pi (HDMI monitor or Pi touchscreen)

## Installation Steps

### 1. Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Required Packages
```bash
# Install pygame dependencies
sudo apt install python3-pygame python3-pip -y

# Alternative method if pygame isn't available via apt:
pip3 install pygame
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

### 4. Test Controller Connection
```bash
# Check if controller is detected
lsusb | grep -i xbox

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
```

### 5. Run the Visualizer
```bash
# Make the script executable
chmod +x xbox_joystick_viz.py

# Run the visualizer
python3 xbox_joystick_viz.py
```

## Usage

1. **Connect your Xbox controller** via USB to the Raspberry Pi
2. **Run the script** - it will automatically detect the controller
3. **Move the left joystick** to see the real-time arrow visualization
4. **Check the console** for logged joystick values
5. **Press ESC or close the window** to exit

## Features

- **Real-time visualization** of left joystick input
- **Arrow display** showing magnitude and direction
- **Console logging** of X/Y values, magnitude, and angle
- **Deadzone handling** to ignore small movements
- **60 FPS smooth updates**

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

### Performance Issues
- Reduce FPS in the code (change `clock.tick(60)` to lower value)
- Close other applications to free up resources
- Consider running without desktop environment for better performance

### Display Issues
- Ensure HDMI display is connected and configured
- For headless setup, you'll need to modify the code to remove pygame display
- Check display resolution settings

## Controller Compatibility

This script works with:
- Xbox 360 Controller (wired)
- Xbox One Controller (wired)
- Xbox Series X/S Controller (wired)
- Many third-party Xbox-compatible controllers

## Customization

You can modify the following in the code:
- `WINDOW_WIDTH/HEIGHT` - Change display size
- `ARROW_COLOR` - Change arrow color
- `DEADZONE` - Adjust joystick sensitivity
- `ARROW_MAX_LENGTH` - Change maximum arrow length
- Logging frequency and format

## Next Steps

To extend this project, you could:
- Add right joystick visualization
- Include button press indicators
- Log data to file for analysis
- Add network streaming of joystick data
- Create a web interface for remote monitoring