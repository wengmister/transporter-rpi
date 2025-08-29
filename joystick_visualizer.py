#!/usr/bin/env python3
"""
Xbox Controller VESC Differential Drive Robot Controller - Direct Control Version
Direct motor control with comprehensive latency logging
"""

import pygame
import math
import sys
import time
import os
from pyvesc.VESC import VESC
from collections import deque
import statistics

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

# Logging Configuration
LATENCY_LOG_INTERVAL = 1.0  # Log statistics every second
LATENCY_HISTORY_SIZE = 100  # Keep last 100 measurements for statistics

class RobotController:
    def __init__(self):
        # Pygame setup
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Xbox VESC Robot Controller - Direct Control")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.large_font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 20)
        
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
        
        # Latency tracking
        self.joystick_read_times = deque(maxlen=LATENCY_HISTORY_SIZE)
        self.motor_command_times = deque(maxlen=LATENCY_HISTORY_SIZE)
        self.total_loop_times = deque(maxlen=LATENCY_HISTORY_SIZE)
        self.last_latency_log = time.time()
        self.command_counter = 0
        self.last_motor_update = time.time()
        self.motor_update_interval = deque(maxlen=LATENCY_HISTORY_SIZE)
        
        # Performance stats for display
        self.avg_joystick_time = 0
        self.avg_motor_time = 0
        self.avg_loop_time = 0
        self.avg_update_rate = 0
        self.max_motor_time = 0
        self.motor_timeouts = 0
        
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
        print(f"Number of axes: {self.joystick.get_numaxes()}")
        print(f"Number of buttons: {self.joystick.get_numbuttons()}")
        return True
    
    def init_vesc(self):
        """Initialize VESC connections"""
        print("\n=== VESC Initialization ===")
        print("Checking VESC ports...")
        os.system("ls /dev/ttyACM*")
        
        try:
            print(f"\nConnecting to VESC motors:")
            print(f"  Left motor:  {VESC_PORT_1}")
            print(f"  Right motor: {VESC_PORT_2}")
            
            # Time the connection process
            conn_start = time.time()
            self.vesc1 = VESC(serial_port=VESC_PORT_1)
            left_conn_time = time.time() - conn_start
            print(f"  Left motor connected in {left_conn_time:.3f}s")
            
            conn_start = time.time()
            self.vesc2 = VESC(serial_port=VESC_PORT_2)
            right_conn_time = time.time() - conn_start
            print(f"  Right motor connected in {right_conn_time:.3f}s")
            
            # Test connection by setting duty cycle to 0
            test_start = time.time()
            self.vesc1.set_duty_cycle(0)
            self.vesc2.set_duty_cycle(0)
            test_time = time.time() - test_start
            print(f"  Initial stop command sent in {test_time:.3f}s")
            
            self.vesc_connected = True
            print("\n✓ VESC motors connected successfully!")
            print("===========================\n")
            
        except Exception as e:
            print(f"\n✗ Failed to connect to VESC motors: {e}")
            print("Running in visualization-only mode")
            print("===========================\n")
            self.vesc_connected = False
    
    def update_joystick_state(self):
        """Read and update joystick state with timing"""
        if not self.joystick:
            return
        
        start_time = time.time()
        
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
        
        # Track joystick read time
        joystick_time = time.time() - start_time
        self.joystick_read_times.append(joystick_time)
        
        # Calculate differential drive and send to motors
        self.calculate_and_send_motor_commands()
    
    def calculate_and_send_motor_commands(self):
        """Calculate differential drive and directly send to motors with timing"""
        # Calculate differential drive values
        self.speed = self.y_axis * SPEED_MULTIPLIER  # Forward/backward
        self.turn = -self.x_axis * SPEED_MULTIPLIER   # Left/right turn - 0829:inverted
        
        # Differential steering calculation
        left_speed = self.speed + self.turn
        right_speed = self.speed - self.turn
        
        # Clamp to maximum values
        left_speed = max(-1.0, min(1.0, left_speed))
        right_speed = max(-1.0, min(1.0, right_speed))
        
        # Apply maximum speed limit for safety
        self.left_motor_duty = left_speed * MAX_SPEED
        self.right_motor_duty = right_speed * MAX_SPEED
        
        # Send directly to motors with timing
        if self.vesc_connected:
            motor_start = time.time()
            
            try:
                if self.emergency_stop:
                    self.vesc1.set_duty_cycle(0)
                    self.vesc2.set_duty_cycle(0)
                else:
                    # Send commands to both motors
                    self.vesc1.set_duty_cycle(self.left_motor_duty)
                    self.vesc2.set_duty_cycle(self.right_motor_duty)
                
                # Track timing
                motor_time = time.time() - motor_start
                self.motor_command_times.append(motor_time)
                self.max_motor_time = max(self.max_motor_time, motor_time)
                
                # Track update interval
                current_time = time.time()
                interval = current_time - self.last_motor_update
                self.motor_update_interval.append(interval)
                self.last_motor_update = current_time
                
                # Increment command counter
                self.command_counter += 1
                
                # Warn if motor command is slow
                if motor_time > 0.05:  # 50ms warning threshold
                    print(f"⚠ Slow motor command: {motor_time:.3f}s (L:{self.left_motor_duty:.2f}, R:{self.right_motor_duty:.2f})")
                
                if motor_time > 0.1:  # 100ms critical threshold
                    print(f"⚠⚠ CRITICAL: Motor command took {motor_time:.3f}s!")
                    self.motor_timeouts += 1
                    
            except Exception as e:
                print(f"✗ Motor control error: {e}")
                self.motor_timeouts += 1
    
    def handle_buttons(self):
        """Handle controller button presses"""
        if not self.joystick:
            return
            
        # Emergency stop button (B button - button 1)
        if self.joystick.get_button(1):  # B button
            if not self.emergency_stop:
                self.emergency_stop = True
                print("🛑 EMERGENCY STOP ACTIVATED!")
                # Send stop command immediately
                if self.vesc_connected:
                    try:
                        start = time.time()
                        self.vesc1.set_duty_cycle(0)
                        self.vesc2.set_duty_cycle(0)
                        stop_time = time.time() - start
                        print(f"  Stop command sent in {stop_time:.3f}s")
                    except:
                        pass
        
        # Reset emergency stop (A button - button 0)
        if self.joystick.get_button(0):  # A button
            if self.emergency_stop:
                self.emergency_stop = False
                print("✓ Emergency stop RELEASED - Robot ready")
    
    def log_latency_stats(self):
        """Log latency statistics periodically"""
        current_time = time.time()
        if current_time - self.last_latency_log >= LATENCY_LOG_INTERVAL:
            # Calculate statistics
            if self.joystick_read_times:
                self.avg_joystick_time = statistics.mean(self.joystick_read_times) * 1000
                max_joystick = max(self.joystick_read_times) * 1000
            else:
                self.avg_joystick_time = 0
                max_joystick = 0
            
            if self.motor_command_times:
                self.avg_motor_time = statistics.mean(self.motor_command_times) * 1000
                max_motor = max(self.motor_command_times) * 1000
            else:
                self.avg_motor_time = 0
                max_motor = 0
            
            if self.total_loop_times:
                self.avg_loop_time = statistics.mean(self.total_loop_times) * 1000
                max_loop = max(self.total_loop_times) * 1000
                avg_fps = 1000 / self.avg_loop_time if self.avg_loop_time > 0 else 0
            else:
                self.avg_loop_time = 0
                max_loop = 0
                avg_fps = 0
            
            if self.motor_update_interval:
                self.avg_update_rate = 1.0 / statistics.mean(self.motor_update_interval)
            else:
                self.avg_update_rate = 0
            
            # Log to console
            print(f"\n=== Latency Report ({self.command_counter} commands) ===")
            print(f"Joystick Read:  avg={self.avg_joystick_time:.2f}ms  max={max_joystick:.2f}ms")
            print(f"Motor Command:  avg={self.avg_motor_time:.2f}ms   max={max_motor:.2f}ms")
            print(f"Total Loop:     avg={self.avg_loop_time:.2f}ms   max={max_loop:.2f}ms")
            print(f"Actual FPS:     {avg_fps:.1f} Hz")
            print(f"Motor Updates:  {self.avg_update_rate:.1f} Hz")
            if self.motor_timeouts > 0:
                print(f"⚠ Motor timeouts: {self.motor_timeouts}")
            print("=" * 40)
            
            self.last_latency_log = current_time
    
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
    
    def draw_latency_display(self):
        """Draw latency information on screen"""
        # Latency box
        latency_x = WINDOW_WIDTH - 250
        latency_y = 100
        
        # Title
        title = self.font.render("LATENCY MONITOR", True, (200, 200, 255))
        self.screen.blit(title, (latency_x, latency_y))
        
        # Stats
        stats = [
            f"Joystick: {self.avg_joystick_time:.1f}ms",
            f"Motor Cmd: {self.avg_motor_time:.1f}ms",
            f"Loop Time: {self.avg_loop_time:.1f}ms",
            f"Motor Rate: {self.avg_update_rate:.1f}Hz",
            f"Commands: {self.command_counter}",
        ]
        
        if self.motor_timeouts > 0:
            stats.append(f"Timeouts: {self.motor_timeouts}")
        
        y_offset = latency_y + 30
        for stat in stats:
            # Color code based on latency
            if "Motor Cmd" in stat and self.avg_motor_time > 50:
                color = (255, 100, 100)  # Red for high latency
            elif "Motor Cmd" in stat and self.avg_motor_time > 20:
                color = (255, 255, 100)  # Yellow for medium latency
            else:
                color = TEXT_COLOR
            
            surface = self.small_font.render(stat, True, color)
            self.screen.blit(surface, (latency_x, y_offset))
            y_offset += 22
        
        # Draw warning if motor commands are slow
        if self.max_motor_time > 100:  # 100ms
            warning = self.font.render(f"⚠ MAX DELAY: {self.max_motor_time:.0f}ms", True, (255, 50, 50))
            self.screen.blit(warning, (latency_x - 20, y_offset + 10))
    
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
        title = self.large_font.render("Xbox VESC Robot - Direct Control", True, TEXT_COLOR)
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
            self.screen.blit(surface, (CENTER_X + 100, y_offset))
            y_offset += 22
    
    def cleanup(self):
        """Clean shutdown of VESC connections"""
        if self.vesc_connected:
            try:
                print("\nStopping motors...")
                start = time.time()
                self.vesc1.set_duty_cycle(0)
                self.vesc2.set_duty_cycle(0)
                stop_time = time.time() - start
                print(f"  Motors stopped in {stop_time:.3f}s")
                
                print("Closing VESC connections...")
                self.vesc1.close()
                self.vesc2.close()
                print("  Connections closed")
            except Exception as e:
                print(f"Error during cleanup: {e}")
        
        pygame.quit()
    
    def run(self):
        """Main control loop"""
        if not self.joystick:
            print("Cannot start - no joystick connected!")
            return
        
        print("\n=== Xbox VESC Robot Controller - Direct Control ===")
        print("Left joystick controls robot movement")
        print("A button: Release emergency stop")
        print("B button: Emergency stop")
        print("ESC: Exit")
        print("Latency statistics logged every second")
        print("===================================================\n")
        
        running = True
        
        try:
            while running:
                loop_start = time.time()
                
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
                            print("🛑 EMERGENCY STOP (Spacebar)")
                    elif event.type == pygame.JOYBUTTONDOWN:
                        print(f"Button {event.button} pressed")
                
                # Update controller state
                self.update_joystick_state()
                self.handle_buttons()
                
                # Log latency statistics periodically
                self.log_latency_stats()
                
                # Clear screen
                self.screen.fill(BACKGROUND_COLOR)
                
                # Draw everything
                self.draw_ui()
                self.draw_joystick_arrow()
                self.draw_motor_indicators()
                self.draw_latency_display()
                
                # Update display
                pygame.display.flip()
                
                # Track total loop time
                loop_time = time.time() - loop_start
                self.total_loop_times.append(loop_time)
                
                self.clock.tick(60)  # 60 FPS target
                
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received...")
        finally:
            # Final statistics
            print("\n=== Final Statistics ===")
            print(f"Total commands sent: {self.command_counter}")
            if self.motor_command_times:
                print(f"Average motor latency: {self.avg_motor_time:.2f}ms")
                print(f"Max motor latency: {self.max_motor_time*1000:.2f}ms")
            if self.motor_timeouts > 0:
                print(f"Total timeouts: {self.motor_timeouts}")
            print("========================")
            
            self.cleanup()
            print("Exited cleanly.")

if __name__ == "__main__":
    print("Xbox VESC Robot Controller - Direct Control Version")
    print("This version sends commands directly to motors without threading")
    print("Make sure Xbox controller and VESC motors are connected\n")
    
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