#!/usr/bin/env python3
"""
Xbox Controller Left Joystick Visualizer for Raspberry Pi 4
Displays real-time arrow showing joystick magnitude and direction
"""

import pygame
import math
import sys
import time

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
CENTER_X = WINDOW_WIDTH // 2
CENTER_Y = WINDOW_HEIGHT // 2
ARROW_BASE_LENGTH = 100
ARROW_MAX_LENGTH = 200
BACKGROUND_COLOR = (20, 20, 30)
ARROW_COLOR = (255, 100, 100)
CIRCLE_COLOR = (100, 100, 100)
TEXT_COLOR = (255, 255, 255)
DEADZONE = 0.1  # Ignore small movements

class JoystickVisualizer:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Xbox Controller - Left Joystick Visualizer")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Initialize joystick
        pygame.joystick.init()
        self.joystick = None
        self.init_joystick()
        
        # Joystick state
        self.x_axis = 0.0
        self.y_axis = 0.0
        self.magnitude = 0.0
        self.angle = 0.0
        
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
        
    def update_joystick_state(self):
        """Read and update joystick state"""
        if not self.joystick:
            return
            
        # Get left joystick axes (typically axes 0 and 1)
        raw_x = self.joystick.get_axis(0)
        raw_y = -self.joystick.get_axis(1)
        
        # Apply deadzone
        if abs(raw_x) < DEADZONE:
            raw_x = 0.0
        if abs(raw_y) < DEADZONE:
            raw_y = 0.0
            
        self.x_axis = raw_x
        self.y_axis = raw_y
        
        # Calculate magnitude and angle
        self.magnitude = math.sqrt(raw_x**2 + raw_y**2)
        if self.magnitude > 0:
            self.angle = math.atan2(-raw_y, raw_x)  # Negative y for screen coordinates
        else:
            self.angle = 0.0
            
        # Log the values
        print(f"Left Joystick - X: {self.x_axis:6.3f}, Y: {self.y_axis:6.3f}, "
              f"Magnitude: {self.magnitude:6.3f}, Angle: {math.degrees(self.angle):6.1f}°")
    
    def draw_arrow(self):
        """Draw the joystick direction arrow"""
        if self.magnitude < DEADZONE:
            return
            
        # Calculate arrow length based on magnitude
        arrow_length = ARROW_BASE_LENGTH + (self.magnitude * (ARROW_MAX_LENGTH - ARROW_BASE_LENGTH))
        
        # Calculate arrow end point
        end_x = CENTER_X + arrow_length * math.cos(self.angle)
        end_y = CENTER_Y + arrow_length * math.sin(self.angle)
        
        # Draw main arrow line
        pygame.draw.line(self.screen, ARROW_COLOR, (CENTER_X, CENTER_Y), (end_x, end_y), 4)
        
        # Draw arrowhead
        arrowhead_length = 20
        arrowhead_angle = math.pi / 6  # 30 degrees
        
        # Calculate arrowhead points
        left_x = end_x - arrowhead_length * math.cos(self.angle - arrowhead_angle)
        left_y = end_y - arrowhead_length * math.sin(self.angle - arrowhead_angle)
        right_x = end_x - arrowhead_length * math.cos(self.angle + arrowhead_angle)
        right_y = end_y - arrowhead_length * math.sin(self.angle + arrowhead_angle)
        
        # Draw arrowhead
        pygame.draw.polygon(self.screen, ARROW_COLOR, 
                          [(end_x, end_y), (left_x, left_y), (right_x, right_y)])
    
    def draw_ui(self):
        """Draw UI elements"""
        # Draw center circle
        pygame.draw.circle(self.screen, CIRCLE_COLOR, (CENTER_X, CENTER_Y), 5)
        
        # Draw reference circle
        pygame.draw.circle(self.screen, CIRCLE_COLOR, (CENTER_X, CENTER_Y), ARROW_MAX_LENGTH, 2)
        
        # Draw coordinate axes
        pygame.draw.line(self.screen, CIRCLE_COLOR, 
                        (CENTER_X - ARROW_MAX_LENGTH, CENTER_Y), 
                        (CENTER_X + ARROW_MAX_LENGTH, CENTER_Y), 1)
        pygame.draw.line(self.screen, CIRCLE_COLOR, 
                        (CENTER_X, CENTER_Y - ARROW_MAX_LENGTH), 
                        (CENTER_X, CENTER_Y + ARROW_MAX_LENGTH), 1)
        
        # Draw text info
        info_texts = [
            f"X Axis: {self.x_axis:6.3f}",
            f"Y Axis: {self.y_axis:6.3f}",
            f"Magnitude: {self.magnitude:6.3f}",
            f"Angle: {math.degrees(self.angle):6.1f}°"
        ]
        
        y_offset = 20
        for text in info_texts:
            surface = self.small_font.render(text, True, TEXT_COLOR)
            self.screen.blit(surface, (20, y_offset))
            y_offset += 30
        
        # Draw title
        title = self.font.render("Xbox Controller - Left Joystick", True, TEXT_COLOR)
        title_rect = title.get_rect(center=(CENTER_X, 40))
        self.screen.blit(title, title_rect)
        
        # Draw instructions
        instructions = [
            "Move left joystick to see arrow",
            "Press ESC or close window to exit"
        ]
        
        y_offset = WINDOW_HEIGHT - 60
        for instruction in instructions:
            surface = self.small_font.render(instruction, True, TEXT_COLOR)
            surface_rect = surface.get_rect(center=(CENTER_X, y_offset))
            self.screen.blit(surface, surface_rect)
            y_offset += 25
    
    def run(self):
        """Main game loop"""
        if not self.joystick:
            print("Cannot start - no joystick connected!")
            return
            
        running = True
        
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.JOYBUTTONDOWN:
                    print(f"Button {event.button} pressed")
                    
            # Update joystick state
            self.update_joystick_state()
            
            # Clear screen
            self.screen.fill(BACKGROUND_COLOR)
            
            # Draw everything
            self.draw_ui()
            self.draw_arrow()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)  # 60 FPS
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    print("Xbox Controller Joystick Visualizer")
    print("Make sure your Xbox controller is connected via USB")
    print("Press ESC to exit")
    
    try:
        visualizer = JoystickVisualizer()
        visualizer.run()
    except KeyboardInterrupt:
        print("\nExiting...")
        pygame.quit()
        sys.exit()