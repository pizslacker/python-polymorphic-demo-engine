#!/usr/bin/env python3
import pygame
import math
import random
import sys

# ==========================================
# 1. POLYMORPHIC BASE CLASS
# ==========================================
class DemoEffect:
    def __init__(self, width, height):
        self.w = width
        self.h = height
        self.cx = width // 2
        self.cy = height // 2

    def update(self, dt, run_time):
        pass

    def draw(self, surface):
        pass

# ==========================================
# 2. EFFECT IMPLEMENTATIONS
# ==========================================
class Starfield(DemoEffect):
    def __init__(self, width, height):
        super().__init__(width, height)
        self.num_stars = 400
        self.stars = [[random.uniform(-self.w, self.w), 
                       random.uniform(-self.h, self.h), 
                       random.uniform(0.1, self.w)] for _ in range(self.num_stars)]
        self.speed = 150.0

    def update(self, dt, run_time):
        current_speed = self.speed + math.sin(run_time * 2) * 100
        
        for star in self.stars:
            star[2] -= current_speed * dt
            if star[2] <= 0:
                star[0] = random.uniform(-self.w, self.w)
                star[1] = random.uniform(-self.h, self.h)
                star[2] = self.w

    def draw(self, surface):
        surface.fill((5, 5, 10)) 
        
        for x, y, z in self.stars:
            proj_x = int((x / z) * 200 + self.cx)
            proj_y = int((y / z) * 200 + self.cy)
            
            depth_ratio = 1.0 - (z / self.w)
            size = max(1, int(depth_ratio * 4))
            color_val = max(50, int(depth_ratio * 255))
            
            if 0 <= proj_x < self.w and 0 <= proj_y < self.h:
                pygame.draw.rect(surface, (color_val, color_val, color_val), (proj_x, proj_y, size, size))


class VectorTunnel(DemoEffect):
    def __init__(self, width, height):
        super().__init__(width, height)
        self.segments = 25
        self.depth_spacing = 40
        
    def update(self, dt, run_time):
        self.time = run_time

    def draw(self, surface):
        surface.fill((10, 0, 20)) 
        
        for i in range(self.segments, 0, -1):
            z = (i * self.depth_spacing) - ((self.time * 200) % self.depth_spacing)
            if z < 1: z = 1
            
            angle = self.time * 0.5 + (i * 0.1)
            size = 8000 / z
            
            offset_x = math.sin(self.time + i * 0.1) * (1000 / z)
            offset_y = math.cos(self.time * 1.3 + i * 0.1) * (1000 / z)
            
            points = []
            for corner in [(1,1), (1,-1), (-1,-1), (-1,1)]:
                rx = corner[0] * math.cos(angle) - corner[1] * math.sin(angle)
                ry = corner[0] * math.sin(angle) + corner[1] * math.cos(angle)
                
                px = self.cx + offset_x + (rx * size)
                py = self.cy + offset_y + (ry * size)
                points.append((px, py))
                
            r = int(127 + 128 * math.sin(self.time * 2 + i * 0.2))
            g = int(127 + 128 * math.sin(self.time * 3 + i * 0.1))
            b = 255
            
            pygame.draw.polygon(surface, (r, g, b), points, max(1, int(5 - z/100)))

# ==========================================
# 3. POLYMORPHIC ENGINE CORE WITH BLENDING
# ==========================================
class DemoEngine:
    def __init__(self, width=1280, height=1024):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Python Polymorphic Demo Engine")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Courier", 18, bold=True)
        
        # Off-screen surfaces for crossfading
        self.surface_current = pygame.Surface((width, height))
        self.surface_next = pygame.Surface((width, height))
        
        self.effects = [
            VectorTunnel(width, height),
            Starfield(width, height)
        ]
        self.current_effect_idx = 0
        
        # Timing controls
        self.timer = 0.0
        self.effect_duration = 8.0     # Total time per effect
        self.transition_duration = 2.0 # How long the crossfade lasts

    def run(self):
        running = True
        run_time = 0.0
        
        while running:
            dt = self.clock.tick(60) / 1000.0
            run_time += dt
            self.timer += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        # Force jump to the transition phase immediately
                        if self.timer < (self.effect_duration - self.transition_duration):
                            self.timer = self.effect_duration - self.transition_duration

            # Check if it's time to fully switch index and reset timer
            if self.timer >= self.effect_duration:
                self.timer -= self.effect_duration
                self.current_effect_idx = (self.current_effect_idx + 1) % len(self.effects)

            current_effect = self.effects[self.current_effect_idx]
            is_transitioning = self.timer >= (self.effect_duration - self.transition_duration)

            if not is_transitioning:
                # Normal Rendering: Update and draw directly to the main screen
                current_effect.update(dt, run_time)
                current_effect.draw(self.screen)
                active_name = current_effect.__class__.__name__
            else:
                # Transition Rendering: Update both, draw to off-screen surfaces, and blend
                next_effect_idx = (self.current_effect_idx + 1) % len(self.effects)
                next_effect = self.effects[next_effect_idx]
                
                current_effect.update(dt, run_time)
                next_effect.update(dt, run_time)
                
                current_effect.draw(self.surface_current)
                next_effect.draw(self.surface_next)
                
                # Calculate alpha 0-255 based on transition progress
                time_in_transition = self.timer - (self.effect_duration - self.transition_duration)
                alpha = int(255 * (time_in_transition / self.transition_duration))
                alpha = max(0, min(255, alpha))
                
                self.surface_next.set_alpha(alpha)
                
                # Blit the layers onto the main display
                self.screen.blit(self.surface_current, (0, 0))
                self.screen.blit(self.surface_next, (0, 0))
                
                active_name = f"{current_effect.__class__.__name__} -> {next_effect.__class__.__name__}"

            # Draw Engine Overlay
            fps_text = self.font.render(f"FPS: {int(self.clock.get_fps())}", True, (0, 255, 0))
            effect_text = self.font.render(f"EFFECT: {active_name}", True, (0, 255, 255))
            self.screen.blit(fps_text, (10, 10))
            self.screen.blit(effect_text, (10, 30))

            pygame.display.flip()

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    engine = DemoEngine(800, 600)
    engine.run()