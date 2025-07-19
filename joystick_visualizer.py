#!/usr/bin/env python3
"""
Xbox Controller VESC Differential Drive Robot Controller
Combines joystick visualization with VESC motor control for differential drive robot
"""

import pygame
import math
import sys
import time
import os
from pyvesc.VESC import VESC
import threading
import queue

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
CENTER_X = WINDOW_WIDTH // 2
CENTER_Y = WINDOW_HEIGHT // 2 - 50
ARROW_BASE_LENGTH = 80
ARROW_MAX_LENGTH = 150
BACKGROUND_COLOR = (20, 20, 30)
ARROW_COLOR = (255, 100, 100)
MOTOR_COLOR_LEFT = (100, 255, 100)
MOTOR_COLOR_RIGHT = (100, 150, 255)
CIRCLE_COLOR = (100, 100, 100)
TEXT_COLOR = (255, 255, 255)
DEADZONE = 0.15  # Ignore small movements for safety

# VESC Configuration
VESC_PORT_1 = '/dev/ttyACM0'  # Left motor
VESC_PORT_2 = '/dev/ttyACM1'  # Right motor
MAX_SPEED = 0.8  # Maximum duty cycle (80% for safety)
SPEED_MULTIPLIER = 1.0  # Joystick sensitivity

class RobotController:
    def __init__(self):
        # Pygame setup
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Xbox VESC Robot Controller")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.large_font = pygame.font.Font(None, 36)
        
        # Initialize joystick
        pygame.joystick.init()
        self.joystick = None
        self.init_joystick()
        
        # Robot state
        self.x_axis = 0.0
        self.y_axis = 0.0
        self.magnitude = 0.0
        self.angle = 0.0
        self.speed = 0.0
        self.turn = 0.0
        self.left_motor_duty = 0.0
        self.right_motor_duty = 0.0
        
        # VESC connections
        self.vesc1 = None  # Left motor
        self.vesc2 = None  # Right motor
        self.vesc_connected = False
        self.emergency_stop = False
        
        # Threading for VESC communication
        self.motor_queue = queue.Queue()
        self.motor_thread = None
        self.running = False
        
        # Initialize VESC
        self.init_vesc()
        
    def init_joystick(self):
        """Initialize the Xbox controller"""
        joystick_count = pygame.joystick.get_count()
        
        if joystick_count == 0:
            print("No joystick connected!")
            return False
            
        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        
        print(f"Joystick connected: {self.joystick.get_name()}")
        return True
    
    def init_vesc(self):
        """Initialize VESC connections"""
        print("Checking VESC ports...")
        os.system("ls /dev/ttyACM*")
        
        try:
            print(f"Connecting to VESC motors on {VESC_PORT_1} and {VESC_PORT_2}...")
            self.vesc1 = VESC(serial_port=VESC_PORT_1)
            self.vesc2 = VESC(serial_port=VESC_PORT_2)
            
            # Test connection by setting duty cycle to 0
            self.vesc1.set_duty_cycle(0)
            self.vesc2.set_duty_cycle(0)
            
            self.vesc_connected = True
            print("VESC motors connected successfully!")
            
            # Start motor control thread
            self.running = True
            self.motor_thread = threading.Thread(target=self.motor_control_loop, daemon=True)
            self.motor_thread.start()
            
        except Exception as e:
            print(f"Failed to connect to VESC motors: {e}")
            print("Running in visualization-only mode")
            self.vesc_connected = False
    
    def motor_control_loop(self):
        """Separate thread for motor control to avoid blocking"""
        while self.running and self.vesc_connected:
            try:
                if not self.motor_queue.empty():
                    left_duty, right_duty = self.motor_queue.get()
                    
                    if self.emergency_stop:
                        left_duty = 0.0
                        right_duty = 0.0
                    
                    self.vesc1.set_duty_cycle(left_duty)
                    self.vesc2.set_duty_cycle(right_duty)
                    
                time.sleep(0.02)  # 50Hz update rate for motors
                
            except Exception as e:
                print(f"Motor control error: {e}")
                break
    
    def update_joystick_state(self):
        """Read and update joystick state"""
        if not self.joystick:
            return
            
        # Get left joystick axes
        raw_x = self.joystick.get_axis(0)  # Left/right
        raw_y = -self.joystick.get_axis(1)  # Forward/back (inverted)
        
        # Apply deadzone
        if abs(raw_x) < DEADZONE:
            raw_x = 0.0
        if abs(raw_y) < DEADZONE:
            raw_y = 0.0
            
        self.x_axis = raw_x
        self.y_axis = raw_y
        
        # Calculate magnitude and angle
        self.magnitude = math.sqrt(raw_x**2 + raw_y**2)
        self.magnitude = min(1.0, self.magnitude)  # Clamp to max 1.0
        
        if self.magnitude > 0:
            self.angle = math.atan2(raw_y, raw_x)
        else:
            self.angle = 0.0
        
        # Calculate differential drive values
        self.calculate_differential_drive()
        
        # Log the values
        print(f"Joystick X: {self.x_axis:6.3f}, Y: {self.y_axis:6.3f} | "
              f"Speed: {self.speed:6.3f}, Turn: {self.turn:6.3f} | "
              f"L: {self.left_motor_duty:6.3f}, R: {self.right_motor_duty:6.3f}")
    
    def calculate_differential_drive(self):
        """Calculate differential drive motor values from joystick input"""
        # Convert joystick to speed and turn
        self.speed = self.y_axis * SPEED_MULTIPLIER  # Forward/backward
        self.turn = self.x_axis * SPEED_MULTIPLIER   # Left/right turn
        
        # Differential steering calculation
        left_speed = self.speed + self.turn
        right_speed = self.speed - self.turn
        
        # Clamp to maximum values
        left_speed = max(-1.0, min(1.0, left_speed))
        right_speed = max(-1.0, min(1.0, right_speed))
        
        # Apply maximum speed limit for safety
        self.left_motor_duty = left_speed * MAX_SPEED
        self.right_motor_duty = right_speed * MAX_SPEED
        
        # Send to motor control thread
        if self.vesc_connected and not self.motor_queue.full():
            try:
                self.motor_queue.put((self.left_motor_duty, self.right_motor_duty), block=False)
            except queue.Full:
                pass  # Skip this update if queue is full
    
    def handle_buttons(self):
        """Handle controller button presses"""
        if not self.joystick:
            return
            
        # Emergency stop button (B button - button 1)
        if self.joystick.get_button(1):  # B button
            if not self.emergency_stop:
                self.emergency_stop = True
                print("EMERGENCY STOP ACTIVATED!")
                # Send stop command immediately
                if self.vesc_connected:
                    try:
                        self.vesc1.set_duty_cycle(0)
                        self.vesc2.set_duty_cycle(0)
                    except:
                        pass
        
        # Reset emergency stop (A button - button 0)
        if self.joystick.get_button(0):  # A button
            if self.emergency_stop:
                self.emergency_stop = False
                print("Emergency stop RELEASED - Robot ready")
    
    def draw_joystick_arrow(self):
        """Draw the joystick direction arrow"""
        if self.magnitude < DEADZONE:
            return
            
        # Calculate arrow length based on magnitude
        arrow_length = ARROW_BASE_LENGTH + (self.magnitude * (ARROW_MAX_LENGTH - ARROW_BASE_LENGTH))
        
        # Calculate arrow end point
        end_x = CENTER_X + arrow_length * math.cos(self.angle)
        end_y = CENTER_Y - arrow_length * math.sin(self.angle)  # Negative for screen coordinates
        
        # Draw main arrow line
        color = ARROW_COLOR if not self.emergency_stop else (255, 50, 50)
        pygame.draw.line(self.screen, color, (CENTER_X, CENTER_Y), (end_x, end_y), 6)
        
        # Draw arrowhead
        arrowhead_length = 25
        arrowhead_angle = math.pi / 6  # 30 degrees
        
        # Calculate arrowhead points
        left_x = end_x - arrowhead_length * math.cos(self.angle - arrowhead_angle)
        left_y = end_y + arrowhead_length * math.sin(self.angle - arrowhead_angle)
        right_x = end_x - arrowhead_length * math.cos(self.angle + arrowhead_angle)
        right_y = end_y + arrowhead_length * math.sin(self.angle + arrowhead_angle)
        
        # Draw arrowhead
        pygame.draw.polygon(self.screen, color, 
                          [(end_x, end_y), (left_x, left_y), (right_x, right_y)])
    
    def draw_motor_indicators(self):
        """Draw motor power indicators"""
        # Left motor indicator
        left_y = WINDOW_HEIGHT - 150
        left_x = 100
        left_height = int(abs(self.left_motor_duty) * 100)
        left_rect = pygame.Rect(left_x, left_y - left_height, 40, left_height)
        
        if self.left_motor_duty > 0:
            pygame.draw.rect(self.screen, MOTOR_COLOR_LEFT, left_rect)
            direction = "FWD"
        elif self.left_motor_duty < 0:
            pygame.draw.rect(self.screen, (255, 100, 100), left_rect)
            direction = "REV"
        else:
            direction = "STOP"
        
        # Left motor labels
        left_label = self.font.render(f"LEFT MOTOR", True, TEXT_COLOR)
        self.screen.blit(left_label, (left_x - 10, left_y + 20))
        left_duty = self.font.render(f"{self.left_motor_duty:.2f}", True, TEXT_COLOR)
        self.screen.blit(left_duty, (left_x, left_y + 45))
        left_dir = self.font.render(direction, True, TEXT_COLOR)
        self.screen.blit(left_dir, (left_x, left_y + 70))
        
        # Right motor indicator
        right_y = WINDOW_HEIGHT - 150
        right_x = WINDOW_WIDTH - 140
        right_height = int(abs(self.right_motor_duty) * 100)
        right_rect = pygame.Rect(right_x, right_y - right_height, 40, right_height)
        
        if self.right_motor_duty > 0:
            pygame.draw.rect(self.screen, MOTOR_COLOR_RIGHT, right_rect)
            direction = "FWD"
        elif self.right_motor_duty < 0:
            pygame.draw.rect(self.screen, (255, 100, 100), right_rect)
            direction = "REV"
        else:
            direction = "STOP"
        
        # Right motor labels
        right_label = self.font.render(f"RIGHT MOTOR", True, TEXT_COLOR)
        self.screen.blit(right_label, (right_x - 15, right_y + 20))
        right_duty = self.font.render(f"{self.right_motor_duty:.2f}", True, TEXT_COLOR)
        self.screen.blit(right_duty, (right_x, right_y + 45))
        right_dir = self.font.render(direction, True, TEXT_COLOR)
        self.screen.blit(right_dir, (right_x, right_y + 70))
        
        # Draw motor indicator outlines
        pygame.draw.rect(self.screen, CIRCLE_COLOR, (left_x, left_y - 100, 40, 100), 2)
        pygame.draw.rect(self.screen, CIRCLE_COLOR, (right_x, right_y - 100, 40, 100), 2)
    
    def draw_ui(self):
        """Draw UI elements"""
        # Draw center circle and reference elements
        pygame.draw.circle(self.screen, CIRCLE_COLOR, (CENTER_X, CENTER_Y), 8)
        pygame.draw.circle(self.screen, CIRCLE_COLOR, (CENTER_X, CENTER_Y), ARROW_MAX_LENGTH, 2)
        
        # Draw coordinate axes
        pygame.draw.line(self.screen, CIRCLE_COLOR, 
                        (CENTER_X - ARROW_MAX_LENGTH, CENTER_Y), 
                        (CENTER_X + ARROW_MAX_LENGTH, CENTER_Y), 1)
        pygame.draw.line(self.screen, CIRCLE_COLOR, 
                        (CENTER_X, CENTER_Y - ARROW_MAX_LENGTH), 
                        (CENTER_X, CENTER_Y + ARROW_MAX_LENGTH), 1)
        
        # Title
        title = self.large_font.render("Xbox VESC Robot Controller", True, TEXT_COLOR)
        title_rect = title.get_rect(center=(CENTER_X, 30))
        self.screen.blit(title, title_rect)
        
        # Connection status
        if self.vesc_connected:
            status_color = (100, 255, 100) if not self.emergency_stop else (255, 100, 100)
            status_text = "CONNECTED" if not self.emergency_stop else "EMERGENCY STOP"
        else:
            status_color = (255, 255, 100)
            status_text = "VESC DISCONNECTED"
        
        status = self.font.render(f"Status: {status_text}", True, status_color)
        self.screen.blit(status, (20, 60))
        
        # Joystick info
        info_texts = [
            f"Joystick X: {self.x_axis:6.3f}",
            f"Joystick Y: {self.y_axis:6.3f}",
            f"Magnitude: {self.magnitude:6.3f}",
            f"Angle: {math.degrees(self.angle):6.1f}°",
            "",
            f"Robot Speed: {self.speed:6.3f}",
            f"Robot Turn: {self.turn:6.3f}",
        ]
        
        y_offset = 100
        for text in info_texts:
            if text:  # Skip empty strings
                surface = self.font.render(text, True, TEXT_COLOR)
                self.screen.blit(surface, (20, y_offset))
            y_offset += 25
        
        # Controls info
        controls = [
            "CONTROLS:",
            "Left Stick - Drive robot",
            "A Button - Release E-Stop",
            "B Button - Emergency Stop",
            "ESC/Close - Exit"
        ]
        
        y_offset = WINDOW_HEIGHT - 140
        for control in controls:
            color = TEXT_COLOR if not control.startswith("CONTROLS") else (200, 200, 255)
            surface = self.font.render(control, True, color)
            self.screen.blit(surface, (CENTER_X + 200, y_offset))
            y_offset += 22
    
    def cleanup(self):
        """Clean shutdown of VESC connections"""
        self.running = False
        
        if self.vesc_connected:
            try:
                print("Stopping motors...")
                self.vesc1.set_duty_cycle(0)
                self.vesc2.set_duty_cycle(0)
                time.sleep(0.1)  # Give time for stop command
                
                print("Closing VESC connections...")
                self.vesc1.close()
                self.vesc2.close()
            except Exception as e:
                print(f"Error during cleanup: {e}")
        
        if self.motor_thread and self.motor_thread.is_alive():
            self.motor_thread.join(timeout=1.0)
        
        pygame.quit()
    
    def run(self):
        """Main control loop"""
        if not self.joystick:
            print("Cannot start - no joystick connected!")
            return
        
        print("\n=== Xbox VESC Robot Controller ===")
        print("Left joystick controls robot movement")
        print("A button: Release emergency stop")
        print("B button: Emergency stop")
        print("ESC: Exit")
        print("=====================================\n")
        
        running = True
        
        try:
            while running:
                # Handle events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_SPACE:
                            # Space bar emergency stop
                            self.emergency_stop = True
                            print("EMERGENCY STOP (Spacebar)")
                    elif event.type == pygame.JOYBUTTONDOWN:
                        print(f"Button {event.button} pressed")
                
                # Update controller state
                self.update_joystick_state()
                self.handle_buttons()
                
                # Clear screen
                self.screen.fill(BACKGROUND_COLOR)
                
                # Draw everything
                self.draw_ui()
                self.draw_joystick_arrow()
                self.draw_motor_indicators()
                
                # Update display
                pygame.display.flip()
                self.clock.tick(60)  # 60 FPS
                
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received...")
        finally:
            self.cleanup()
            print("Exited cleanly.")

if __name__ == "__main__":
    print("Xbox VESC Robot Controller")
    print("Make sure Xbox controller and VESC motors are connected")
    
    try:
        controller = RobotController()
        controller.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        # Emergency cleanup
        try:
            import traceback
            traceback.print_exc()
            
            # Try to stop motors if possible
            if 'controller' in locals() and controller.vesc_connected:
                controller.vesc1.set_duty_cycle(0)
                controller.vesc2.set_duty_cycle(0)
        except:
            pass
        sys.exit(1)