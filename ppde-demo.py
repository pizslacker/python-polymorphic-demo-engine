#!/usr/bin/env python3
# ppde-demo.py
# Copyright (C) k!M/pizslacker 2026
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import pygame
import numpy as np
import random
import math
# Abstract Base Class (ABC)
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
# 3. Concrete Effect B: Raycasted Boing Ball
# ==========================================
class RaycastBoingEffect(DemoEffect):
    def __init__(self, render_width=160, render_height=120):
        self.width = render_width
        self.height = render_height
        
        # 1. Pre-calculate the ray directions for every pixel on screen
        # Using indexing='ij' so the resulting arrays are shape (width, height)
        # This allows zero-copy blitting to Pygame's surface arrays.
        x = np.linspace(-1, 1, self.width)
        y = np.linspace(-self.height/self.width, self.height/self.width, self.height)
        X, Y = np.meshgrid(x, y, indexing='ij')
        
        # Ray Origin (Camera)
        self.Ro = np.array([0.0, 0.0, -2.5])
        
        # Ray Directions (normalized)
        Rd = np.stack([X, Y, np.ones_like(X)], axis=-1)
        self.Rd = Rd / np.linalg.norm(Rd, axis=-1, keepdims=True)
        
        # Physics & Animation State
        self.time = 0.0
        self.y_pos = 0.0
        self.y_vel = 0.0
        self.gravity = 4.0
        self.radius = 0.8
        
        self.surface = None

    def start(self, screen: pygame.Surface) -> None:
        self.surface = pygame.Surface((self.width, self.height))
        self.time = 0.0
        self.y_pos = -1.0
        self.y_vel = 0.0

    def update(self, dt: float) -> None:
        self.time += dt
        
        # Simple bounce physics for the sphere's Y center
        self.y_vel += self.gravity * dt
        self.y_pos += self.y_vel * dt
        if self.y_pos > 0.8:
            self.y_pos = 0.8
            self.y_vel *= -0.95

    def render(self, screen: pygame.Surface) -> None:
        # Create an empty frame buffer (Width, Height, 3 for RGB)
        frame = np.zeros((self.width, self.height, 3), dtype=np.uint8)
        
        # ==========================================
        # 3.1. BACKGROUND & SHADOW CASTING
        # ==========================================
        # Intersect rays with the back wall at Z = 2.0
        t_wall = (2.0 - self.Ro[2]) / self.Rd[..., 2]
        W = self.Ro + self.Rd * t_wall[..., np.newaxis]
        
        # Draw a classic Amiga purple grid on a gray wall
        grid_mask = (np.abs(W[..., 0]) % 0.6 < 0.03) | (np.abs(W[..., 1]) % 0.6 < 0.03)
        frame[grid_mask] = [140, 100, 140]
        frame[~grid_mask] = [170, 170, 170]
        
        # Cast a shadow from the wall to a light source
        light_pos = np.array([2.0, -2.0, -3.0])
        sphere_center = np.array([0.0, self.y_pos, 0.0])
        
        L_dir = light_pos - W
        L_dir = L_dir / np.linalg.norm(L_dir, axis=-1, keepdims=True)
        
        # Shadow ray intersection with sphere
        O_shadow = W - sphere_center
        b_s = 2.0 * np.sum(L_dir * O_shadow, axis=-1)
        c_s = np.sum(O_shadow**2, axis=-1) - self.radius**2
        disc_s = b_s**2 - 4 * c_s
        
        # Darken the wall where the shadow ray hits the sphere
        shadow_mask = disc_s > 0
        frame[shadow_mask] = frame[shadow_mask] * 0.5
        
        # ==========================================
        # 3.2. SPHERE RAYCASTING (The Boing Ball)
        # ==========================================
        O = self.Ro - sphere_center
        b = 2.0 * np.sum(self.Rd * O, axis=-1)
        c = np.sum(O**2) - self.radius**2
        disc = b**2 - 4 * c
        
        hit_mask = disc > 0
        
        if np.any(hit_mask):
            # Calculate exact hit distances and 3D hit points
            t_sphere = (-b[hit_mask] - np.sqrt(disc[hit_mask])) / 2.0
            P = self.Ro + self.Rd[hit_mask] * t_sphere[..., np.newaxis]
            
            # Surface Normals
            N = (P - sphere_center) / self.radius
            
            # --------------------------------------
            # 3.3. 3D ROTATION MATRIX
            # --------------------------------------
            # Spin around Y axis over time
            spin = self.time * 2.0
            cos_s, sin_s = np.cos(spin), np.sin(spin)
            Ry = np.array([
                [cos_s, 0, sin_s],
                [0,     1, 0    ],
                [-sin_s, 0, cos_s]
            ])
            
            # Static Tilt around Z axis (15 degrees)
            tilt = math.radians(15)
            cos_t, sin_t = np.cos(tilt), np.sin(tilt)
            Rz = np.array([
                [cos_t, -sin_t, 0],
                [sin_t,  cos_t, 0],
                [0,      0,     1]
            ])
            
            # Combine matrices and apply to normals
            # We rotate the normals backward to map the texture forward
            R = Rz @ Ry
            N_rot = N @ R.T
            
            # --------------------------------------
            # 3.4. SPHERICAL UV MAPPING
            # --------------------------------------
            u = np.arctan2(N_rot[:, 0], N_rot[:, 2]) / (2 * np.pi) + 0.5
            v = np.arcsin(np.clip(N_rot[:, 1], -1.0, 1.0)) / np.pi + 0.5
            
            # Checkerboard pattern (16 longitude, 8 latitude segments)
            u_scaled = (u * 16) % 1
            v_scaled = (v * 8) % 1
            is_red = (u_scaled > 0.5) ^ (v_scaled > 0.5)
            
            base_color = np.where(is_red[:, np.newaxis], [220, 20, 20], [240, 240, 240])
            
            # --------------------------------------
            # 3.5. LIGHTING & COMPOSITING
            # --------------------------------------
            # Directional light shining from top-left
            light_dir = np.array([0.577, -0.577, -0.577]) 
            diffuse = np.sum(N * light_dir, axis=-1)
            diffuse = np.clip(diffuse, 0.3, 1.0) # Ambient base of 0.3
            
            lit_color = base_color * diffuse[:, np.newaxis]
            
            # Paint the sphere pixels over the background frame
            frame[hit_mask] = lit_color.astype(np.uint8)

        # ==========================================
        # 3.6. BLIT TO SCREEN
        # ==========================================
        # Fast blit the NumPy array directly into the Pygame surface memory
        pygame.surfarray.blit_array(self.surface, frame)
        pygame.transform.scale(self.surface, screen.get_size(), screen)

# ==========================================
# 4. Post-processing (CRT scanlines filter)
# ==========================================
# generates a static, semi-transparent scanline and vignette overlay once during initialization
class CRTPostProcessor:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Create an overlay surface with per-pixel alpha
        self.overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # 1. Generate Scanlines (varying opacity for a pulsing CRT look)
        for y in range(0, height, 3):
            # Dark main scanline
            pygame.draw.line(self.overlay, (0, 0, 0, 180), (0, y), (width, y))
            # Softer bleed line
            pygame.draw.line(self.overlay, (0, 0, 0, 80), (0, y + 1), (width, y + 1))
            
        # 2. Generate a Vignette (darken the corners)
        center_x, center_y = width // 2, height // 2
        max_dist = (center_x**2 + center_y**2)**0.5
        
        for y in range(height):
            for x in range(width):
                dist = ((x - center_x)**2 + (y - center_y)**2)**0.5
                intensity = dist / max_dist
                if intensity > 0.6:
                    # Increase alpha sharply near the edges
                    alpha = min(255, int((intensity - 0.6) * 500))
                    # Pygame doesn't natively draw individual alpha pixels easily,
                    # so we modify the surface array or use a slow set_at for initialization
                    current = self.overlay.get_at((x, y))
                    self.overlay.set_at((x, y), (0, 0, 0, min(255, current.a + alpha)))

    def apply(self, frame_buffer: pygame.Surface) -> None:
        """Applies the CRT overlay directly onto the target buffer."""
        frame_buffer.blit(self.overlay, (0, 0))

# ==========================================
# 5. The State Machine / Engine
# ==========================================
class DemoEngine:
    def __init__(self, width: int, height: int):
        pygame.init()
        pygame.display.set_caption("Python Polymorphic Demo Engine - CRT Edition")
        self.screen = pygame.display.set_mode((width, height))
        self.font = pygame.font.SysFont("Courier", 12, bold=True)
        
        # Master frame buffer for all rendering
        self.frame_buffer = pygame.Surface((width, height))
        
        # Offscreen buffers for transition blending
        self.surface_a = pygame.Surface((width, height))
        self.surface_b = pygame.Surface((width, height))
        
        # Initialize the post-processing pipeline
        self.post_processor = CRTPostProcessor(width, height)
        
        self.clock = pygame.time.Clock()
        self.playlist = []
        self.current_idx = 0
        self.running = False

        self.is_transitioning = False
        self.transition_progress = 0.0
        self.transition_duration = 1.5  
        self.effect_duration = 5.0      

    def add_effect(self, effect: DemoEffect):
        self.playlist.append(effect)

        # Timing controls
        self.timer = 0.0

    def run(self):
        run_time = 0.0
        if not self.playlist:
            return

        self.running = True
        active_effect = self.playlist[self.current_idx]
        
        # Pass the internal buffer, not the physical screen
        active_effect.start(self.frame_buffer)
        
        timer = 0.0

        while self.running:
            dt = self.clock.tick(60) / 1000.0
            run_time += dt
            self.timer += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # Clear the master buffer at the start of the frame
            self.frame_buffer.fill((0, 0, 0))

            if not self.is_transitioning:
                timer += dt
                if timer > self.effect_duration:
                    self.is_transitioning = True
                    self.transition_progress = 0.0
                    next_idx = (self.current_idx + 1) % len(self.playlist)
                    self.playlist[next_idx].start(self.frame_buffer)
                
                active_effect.update(dt)
                active_effect.render(self.frame_buffer)

            else:
                self.transition_progress += dt / self.transition_duration
                next_idx = (self.current_idx + 1) % len(self.playlist)
                next_effect = self.playlist[next_idx]

                if self.transition_progress >= 1.0:
                    self.is_transitioning = False
                    active_effect.teardown()
                    self.current_idx = next_idx
                    active_effect = next_effect
                    timer = 0.0
                    
                    active_effect.update(dt)
                    active_effect.render(self.frame_buffer)
                else:
                    active_effect.update(dt)
                    next_effect.update(dt)
                    
                    self.surface_a.fill((0,0,0))
                    self.surface_b.fill((0,0,0))
                    
                    active_effect.render(self.surface_a)
                    next_effect.render(self.surface_b)
                    
                    alpha = int(255 * self.transition_progress)
                    self.surface_b.set_alpha(alpha)
                    
                    # Composite transitions onto the master buffer
                    self.frame_buffer.blit(self.surface_a, (0, 0))
                    self.frame_buffer.blit(self.surface_b, (0, 0))

            # --- POST-PROCESSING PASS ---
            self.post_processor.apply(self.frame_buffer)

            # --- HARDWARE FLIP ---
            self.screen.blit(self.frame_buffer, (0, 0))
            fps_text = self.font.render(f"FPS: {int(self.clock.get_fps())}", True, (0, 255, 0))
            self.screen.blit(fps_text, (10, 10))
            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    engine = DemoEngine(800, 600)
    engine.add_effect(PixelFireEffect())
    engine.add_effect(RaycastBoingEffect())
    engine.run()
