#!/usr/bin/env python3
import pygame
import numpy as np
import random
from abc import ABC, abstractmethod

# ==========================================
# 1. The Polymorphic Contract
# ==========================================
class DemoEffect(ABC):
    @abstractmethod
    def start(self, screen: pygame.Surface) -> None:
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        pass

    @abstractmethod
    def render(self, screen: pygame.Surface) -> None:
        pass

    def teardown(self) -> None:
        pass

# ==========================================
# 2. Concrete Effect A: Pixel Fire
# ==========================================
class PixelFireEffect(DemoEffect):
    def __init__(self, render_width=160, render_height=145):
        self.width = render_width
        self.height = render_height
        
        # Classic 37-color DOOM fire palette
        self.palette = np.array([
            [0,0,0], [31,7,7], [47,15,7], [71,15,7], [87,23,7], [103,31,7],
            [119,31,7], [143,39,7], [159,47,7], [175,63,7], [191,71,7], [199,71,7],
            [223,79,7], [223,87,7], [223,87,7], [215,95,7], [215,95,7], [215,103,15],
            [207,111,15], [207,119,15], [207,127,15], [207,135,23], [199,135,23],
            [199,143,23], [199,151,31], [191,159,31], [191,159,31], [191,167,39],
            [191,167,39], [191,175,47], [183,175,47], [183,183,47], [183,183,55],
            [207,207,111], [223,223,159], [239,239,199], [255,255,255]
        ], dtype=np.uint8)
        
        # 2D heat buffer
        self.fire_buffer = np.zeros((self.width, self.height), dtype=np.uint8)
        self.surface = None
        
    def start(self, screen: pygame.Surface) -> None:
        self.surface = pygame.Surface((self.width, self.height))
        # Ignite the bottom row
        self.fire_buffer[:, self.height - 1] = 36
        
    def update(self, dt: float) -> None:
        # Standard bottom-up fire propagation
        for x in range(self.width):
            for y in range(1, self.height):
                heat = self.fire_buffer[x, y]
                
                if heat > 0:
                    decay = random.randint(0, 2)
                    spread = random.randint(-1, 1)
                    
                    new_x = (x + spread) % self.width
                    new_y = y - 1
                    
                    self.fire_buffer[new_x, new_y] = max(0, heat - (decay & 1))
                else:
                    self.fire_buffer[x, y - 1] = 0

    def render(self, screen: pygame.Surface) -> None:
        # Map heat indices to RGB palette instantly via NumPy
        rgb_array = self.palette[self.fire_buffer]
        
        # Blit the NumPy array to our low-res surface
        pygame.surfarray.blit_array(self.surface, rgb_array)
        
        # Hardware-scale the low-res fire to fill the main screen
        pygame.transform.scale(self.surface, screen.get_size(), screen)
        
    def teardown(self) -> None:
        self.fire_buffer.fill(0)

# ==========================================
# 3. Concrete Effect B: Amiga Boing Ball
# ==========================================
class AmigaBoingEffect(DemoEffect):
    def __init__(self):
        self.x, self.y = 0.0, 0.0
        self.vy = 0.0
        self.gravity = 900.0
        
    def start(self, screen: pygame.Surface) -> None:
        self.x = screen.get_width() / 2
        self.y = 50.0
        self.vy = 0.0
        
    def update(self, dt: float) -> None:
        self.vy += self.gravity * dt
        self.y += self.vy * dt
        
        if self.y > 400:
            self.y = 400
            self.vy *= -0.9 # Bounce

    def render(self, screen: pygame.Surface) -> None:
        screen.fill((40, 40, 100))
        # Shadow
        pygame.draw.circle(screen, (20, 20, 50), (int(self.x) + 15, int(self.y) + 15), 40)
        # Ball
        pygame.draw.circle(screen, (200, 0, 0), (int(self.x), int(self.y)), 40)

# ==========================================
# 4. The State Machine / Engine
# ==========================================
class DemoEngine:
    def __init__(self, width: int, height: int):
        pygame.init()
        pygame.display.set_caption("Polymorphic Demo Engine")
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.playlist = []
        self.current_idx = 0
        self.running = False

    def add_effect(self, effect: DemoEffect):
        self.playlist.append(effect)

    def run(self):
        if not self.playlist:
            return

        self.running = True
        active_effect = self.playlist[self.current_idx]
        active_effect.start(self.screen)
        
        effect_duration = 5.0 # Seconds per effect
        timer = 0.0

        while self.running:
            # Cap at 60 FPS, calculate delta time in seconds
            dt = self.clock.tick(60) / 1000.0
            timer += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # Effect transition logic
            if timer > effect_duration:
                timer = 0.0
                active_effect.teardown()
                self.current_idx = (self.current_idx + 1) % len(self.playlist)
                active_effect = self.playlist[self.current_idx]
                active_effect.start(self.screen)

            # ---------------------------------------------------------
            # Polymorphic Execution: The engine doesn't care what 
            # active_effect is, as long as it adheres to DemoEffect.
            # ---------------------------------------------------------
            active_effect.update(dt)
            active_effect.render(self.screen)
            
            pygame.display.flip()
            
            # Print FPS to console to monitor performance of the fire loop
            print(f"FPS: {self.clock.get_fps():.2f}", end="\r")

        pygame.quit()

if __name__ == "__main__":
    engine = DemoEngine(640, 480)
    engine.add_effect(PixelFireEffect())
    engine.add_effect(AmigaBoingEffect())
    engine.run()