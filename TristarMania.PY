import pygame
import sys
import random
import math
import numpy as np # Import the NumPy library

# --- Constants ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FULLSCREEN = True
FPS = 60
SPAWN_RATE = 120 # Spawn an obstacle every X frames
SAMPLE_RATE = 44100 # Standard audio sample rate for sound generation
LETTER_MAPPING = "HGFURSRQMLEDCBKIJPONAXYZWV" # Used for save/load codes

# --- Colors ---
DARK_BLUE = (15, 15, 30)
BLUE = (50, 50, 100)
LIGHT_BLUE = (150, 150, 200)
WHITE = (255, 255, 255)
MENU_TEXT_COLOR = (200, 200, 255)
HOVER_TEXT_COLOR = (255, 255, 255)
SLIDER_BG_COLOR = (70, 70, 70)
SLIDER_HANDLE_COLOR = (200, 200, 255)
SPACESHIP_COLOR = (255, 20, 147) # Bright neon pink
ENEMY_COLOR = (255, 50, 50)
NEUTRAL_COLOR = (50, 255, 50)
ROCK_COLOR = (150, 150, 150)
LASER_COLOR = (0, 255, 255)
LIFE_COLOR = (255, 50, 50)
EXPLOSION_COLORS = [(255, 255, 0), (255, 165, 0), (255, 69, 0), (255, 0, 0)]


# --- Helper function for sound generation ---
def sinc(x):
    """
    Implements the sinc function. This is necessary because pygame does not have a built-in sinc function.
    """
    if x == 0:
        return 1.0
    else:
        return math.sin(x) / x

# --- Starfield Animation Class ---
class Star:
    def __init__(self, screen_width, screen_height):
        self.x = random.randrange(0, screen_width)
        self.y = random.randrange(0, screen_height)
        self.size = random.randint(1, 3)
        self.speed = random.uniform(0.5, 2.0)
        self.color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        self.screen_width = screen_width
        self.screen_height = screen_height

    def update(self):
        self.y += self.speed
        if self.y > self.screen_height:
            self.y = 0
            self.x = random.randrange(0, self.screen_width)

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)

# --- Explosion Effect Classes ---
class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = random.uniform(1, 5)
        self.angle = random.uniform(0, 2 * math.pi)
        self.vx = self.speed * math.cos(self.angle)
        self.vy = self.speed * math.sin(self.angle)
        self.lifespan = random.randint(20, 40)
        self.color = random.choice(EXPLOSION_COLORS)
        self.size = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifespan -= 1
        if self.size > 0.1:
            self.size -= 0.1

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.size))

class Explosion:
    def __init__(self, x, y, num_particles=30):
        self.particles = [Particle(x, y) for _ in range(num_particles)]
        self.is_done = False

    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.lifespan > 0 and p.size > 0]
        if not self.particles:
            self.is_done = True

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)

# --- Harvest Particle Class (New) ---
class HarvestParticle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = random.uniform(2, 4)
        self.size = random.randint(2, 4)
        self.lifespan = 180 # Longer lifespan to reach the player
        self.rect = pygame.Rect(self.x, self.y, self.size * 2, self.size * 2)

    def update(self, player_pos):
        # Calculate vector to the player
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist = math.hypot(dx, dy)

        if dist > 0:
            self.x += self.speed * (dx / dist)
            self.y += self.speed * (dy / dist)

        self.lifespan -= 1
        self.rect.center = (int(self.x), int(self.y))
        
    def draw(self, screen):
        # Draw a white circle
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.size)
        
# --- Spaceship Class (Player) ---
class Spaceship:
    def __init__(self, screen_width, screen_height):
        self.x = screen_width / 2
        self.y = screen_height + 50 # Start below the screen
        self.velocity = 0
        self.max_velocity = 5
        self.acceleration = 0.2
        self.deceleration = 0.1 # New deceleration rate
        self.rotation_speed = 3
        self.direction = -90 # Start facing up, in degrees
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.size = 20
        self.rect = pygame.Rect(self.x - self.size, self.y - self.size, self.size * 2, self.size * 2)
        # Invulnerability attributes
        self.invulnerable = False
        self.invulnerability_duration = 180 # 3 seconds at 60 FPS
        self.invulnerability_timer = 0
        self.blink = False
        
    def update(self):
        self.x += self.velocity * math.cos(math.radians(self.direction))
        self.y += self.velocity * math.sin(math.radians(self.direction))
        
        # Keep spaceship on screen
        self.x %= self.screen_width
        self.y %= self.screen_height
        
        self.rect.center = (int(self.x), int(self.y))

        # Handle invulnerability
        if self.invulnerable:
            self.invulnerability_timer -= 1
            # Blink every 10 frames
            if self.invulnerability_timer % 10 < 5:
                self.blink = True
            else:
                self.blink = False

            if self.invulnerability_timer <= 0:
                self.invulnerable = False
                self.blink = False
        
    def move_forward(self):
        self.velocity = min(self.max_velocity, self.velocity + self.acceleration)
        
    def move_backward(self):
        self.velocity = max(-self.max_velocity, self.velocity - self.acceleration)
    
    # Method to stop the ship completely
    def stop(self):
        # Gradual deceleration
        if self.velocity > 0:
            self.velocity = max(0, self.velocity - self.deceleration)
        elif self.velocity < 0:
            self.velocity = min(0, self.velocity + self.deceleration)

    def rotate_left(self):
        self.direction -= self.rotation_speed
        
    def rotate_right(self):
        self.direction += self.rotation_speed
        
    def draw(self, screen):
        if self.blink:
            return # Don't draw if blinking

        angle_rad = math.radians(self.direction)
        
        # Tip of the spaceship
        p1_x = self.x + self.size * math.cos(angle_rad)
        p1_y = self.y + self.size * math.sin(angle_rad)
        
        # Left wing
        p2_x = self.x + self.size * math.cos(angle_rad + 2.5)
        p2_y = self.y + self.size * math.sin(angle_rad + 2.5)
        
        # Right wing
        p3_x = self.x + self.size * math.cos(angle_rad - 2.5)
        p3_y = self.y + self.size * math.sin(angle_rad - 2.5)
        
        points = [(p1_x, p1_y), (p2_x, p2_y), (p3_x, p3_y)]
        pygame.draw.polygon(screen, SPACESHIP_COLOR, points)
        
    def check_collision(self, other_rect):
        return self.rect.colliderect(other_rect)

    def respawn(self):
        self.x = self.screen_width / 2
        self.y = self.screen_height / 2
        self.velocity = 0
        self.invulnerable = True
        self.invulnerability_timer = self.invulnerability_duration

# --- Laser Class ---
class Laser:
    def __init__(self, x, y, direction, screen_width, screen_height, is_enemy_laser=False, level=1):
        self.x = x
        self.y = y
        self.direction = direction
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.is_enemy_laser = is_enemy_laser

        if is_enemy_laser:
            # Enemy laser properties
            self.speed = 5
            self.color = ENEMY_COLOR
            width, height = 5, 15
        else:
            # Player laser properties
            self.speed = 10
            self.color = LASER_COLOR
            # Increase width based on level, with a maximum cap
            base_width = 5
            width = min(base_width + (level // 2), 25)
            height = 15
        
        self.rect = pygame.Rect(self.x, self.y, width, height)
        
    def update(self):
        # Move the laser forward
        self.x += self.speed * math.cos(math.radians(self.direction))
        self.y += self.speed * math.sin(math.radians(self.direction))
        self.rect.center = (int(self.x), int(self.y))
        
    def draw(self, screen):
        # Draw a simple rectangle for the laser
        pygame.draw.rect(screen, self.color, self.rect)
        
    def is_off_screen(self):
        return self.x < 0 or self.x > self.screen_width or self.y < 0 or self.y > self.screen_height

# --- Obstacle Classes ---
class SpaceRock:
    def __init__(self, screen_width, screen_height):
        self.size = random.randint(15, 40)
        self.x = random.randrange(self.size, screen_width - self.size)
        self.y = -self.size
        self.speed = random.uniform(1.0, 3.0)
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.rect = pygame.Rect(self.x - self.size, self.y - self.size, self.size * 2, self.size * 2)
        self.is_destroyed = False
        self.score_value = 10
        self.is_life_rock = True # Flag to indicate this is a life-giving rock
        
    def update(self):
        self.y += self.speed
        self.rect.center = (int(self.x), int(self.y))
        
    def draw(self, screen):
        pygame.draw.circle(screen, ROCK_COLOR, (int(self.x), int(self.y)), self.size)
        
    def is_off_screen(self):
        return self.y > self.screen_height + self.size

class EnemySpaceship:
    def __init__(self, screen_width, screen_height, level):
        self.size = 20
        self.x = random.randrange(self.size, screen_width - self.size)
        self.y = random.randrange(-300, -50) # Start off-screen at a random x
        # Increase speed based on level
        self.base_speed = random.uniform(1.5, 3.5)
        capped_level = min(level, 2)
        self.speed_multiplier = 1 + (capped_level - 1) * 0.2
        self.speed = self.base_speed * self.speed_multiplier
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.rect = pygame.Rect(self.x - self.size, self.y - self.size, self.size * 2, self.size * 2)
        self.is_destroyed = False
        self.score_value = 50
        self.last_shot_time = pygame.time.get_ticks()

    def update(self, player_pos, level):
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist = math.hypot(dx, dy)
        
        if dist != 0:
            self.x += self.speed * (dx / dist)
            self.y += self.speed * (dy / dist)
            
        self.rect.center = (int(self.x), int(self.y))

    def can_shoot(self, current_time, level):
        # Enemy ships start firing at level 3
        if level < 3:
            return False
        # Fire a laser every 1.5 seconds at level 3, faster at higher levels
        shoot_cooldown = (1500 - (level - 3) * 50) * 2
        return current_time - self.last_shot_time > max(500, shoot_cooldown)

    def shoot(self, player_pos):
        # Calculate the direction to the player
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        angle = math.degrees(math.atan2(dy, dx))
        
        # Create a new laser from the enemy's position, set to target the player
        new_laser = Laser(self.x, self.y, angle, self.screen_width, self.screen_height, is_enemy_laser=True)
        self.last_shot_time = pygame.time.get_ticks()
        return new_laser

    
    def draw(self, screen):
        points = [
            (self.x, self.y - self.size),
            (self.x + self.size, self.y),
            (self.x, self.y + self.size),
            (self.x - self.size, self.y)
        ]
        pygame.draw.polygon(screen, ENEMY_COLOR, points)
        
    def is_off_screen(self):
        return self.y > self.screen_height + self.size or self.x < -self.size or self.x > self.screen_width + self.size

class NeutralSpaceship:
    def __init__(self, screen_width, screen_height):
        self.size = 15
        self.x = random.randrange(self.size, screen_width - self.size)
        self.y = random.randrange(-300, -50)
        self.speed = random.uniform(1.0, 2.0)
        self.direction = random.uniform(0, 360) # Random initial direction
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.rect = pygame.Rect(self.x - self.size, self.y - self.size, self.size * 2, self.size * 2)
        self.is_destroyed = False
        self.is_life_stealer = True # Flag to indicate this is a life-stealing ship
        
    def update(self):
        self.x += self.speed * math.cos(math.radians(self.direction))
        self.y += self.speed * math.sin(math.radians(self.direction))
        
        self.x %= self.screen_width
        self.y %= self.screen_height
        
        self.rect.center = (int(self.x), int(self.y))
    
    def draw(self, screen):
        points = [
            (self.x, self.y - self.size),
            (self.x + self.size, self.y + self.size),
            (self.x - self.size, self.y + self.size)
        ]
        pygame.draw.polygon(screen, NEUTRAL_COLOR, points)
        
    def is_off_screen(self):
        return False

# --- Boss Class (New) ---
class Boss:
    def __init__(self, screen_width, screen_height, level):
        self.size = 100
        self.x = screen_width / 2
        self.y = -self.size
        self.speed = 0.5 # Slower speed
        self.max_health = (10 + (level - 4) * 10) * 2 # More aggressive HP scaling
        self.health = self.max_health
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.rect = pygame.Rect(self.x - self.size / 2, self.y - self.size / 2, self.size, self.size)
        self.is_destroyed = False
        self.score_value = 0 # Boss grants no points
        self.last_shot_time = pygame.time.get_ticks()

    def update(self, player_pos):
        # Move towards the player, like other enemies
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist = math.hypot(dx, dy)
        
        if dist != 0:
            self.x += self.speed * (dx / dist)
            self.y += self.speed * (dy / dist)
            
        self.rect.center = (int(self.x), int(self.y))

    def can_shoot(self, current_time, level):
        # Boss starts shooting at level 5 (its second appearance)
        if level < 5:
            return False
        # Cooldown decreases as level increases, making it fire faster
        shoot_cooldown = max(500, 2000 - (level - 5) * 100)
        return current_time - self.last_shot_time > shoot_cooldown

    def shoot(self, player_pos):
        # Calculate the direction to the player
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        angle = math.degrees(math.atan2(dy, dx))
        
        # Create a new laser from the boss's position
        new_laser = Laser(self.x, self.y, angle, self.screen_width, self.screen_height, is_enemy_laser=True)
        self.last_shot_time = pygame.time.get_ticks()
        return new_laser

    def draw(self, screen):
        # Draw the boss square
        pygame.draw.rect(screen, ENEMY_COLOR, self.rect)
        # Draw the health bar
        if self.health > 0:
            # Health bar background
            bg_rect = pygame.Rect(self.rect.left, self.rect.top - 20, self.rect.width, 10)
            pygame.draw.rect(screen, DARK_BLUE, bg_rect)
            # Health bar foreground
            health_percentage = self.health / self.max_health
            fg_rect = pygame.Rect(self.rect.left, self.rect.top - 20, self.rect.width * health_percentage, 10)
            pygame.draw.rect(screen, LIFE_COLOR, fg_rect)
            # Health bar outline
            pygame.draw.rect(screen, WHITE, bg_rect, 1)

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.is_destroyed = True

    def is_off_screen(self):
        return self.y > self.screen_height + self.size

# --- Main Game Class ---
class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.clock = pygame.time.Clock()

        self.SCREEN_WIDTH = SCREEN_WIDTH
        self.SCREEN_HEIGHT = SCREEN_HEIGHT
        self.FULLSCREEN = FULLSCREEN
        self.FPS = FPS

        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.FULLSCREEN if self.FULLSCREEN else 0)
        pygame.display.set_caption("Tristar Mania")

        self.font = pygame.font.Font(None, 74)
        self.menu_font = pygame.font.Font(None, 60)
        self.small_font = pygame.font.Font(None, 40)
        self.score_font = pygame.font.Font(None, 50)
        self.life_font = pygame.font.Font(None, 50)
        self.leaderboard_font = pygame.font.Font(None, 45)


        self.stars = [Star(self.SCREEN_WIDTH, self.SCREEN_HEIGHT) for _ in range(300)]
        self.high_scores = [] # Temporary leaderboard stored in a list
        self.volume = 0.5
        
        self.resolutions = [(1280, 720), (1600, 900), (1920, 1080)]
        self.current_resolution_index = 2
        
        self.keybinds = {
            "Move Up": pygame.K_w,
            "Move Down": pygame.K_s,
            "Move Left": pygame.K_a,
            "Move Right": pygame.K_d,
            "Shoot": pygame.K_SPACE # Add a new keybind for shooting
        }
        self.remapping_key_for = None
        
        self.explosions = []
        self.music_is_playing = False # Flag to manage music state

        # --- Sound Effects ---
        # Generate the sound data as a list of integers
        laser_sound_list = [int(20000 * sinc(2 * math.pi * 440 * i / SAMPLE_RATE)) for i in range(SAMPLE_RATE // 10)]
        # A simple, short beep for menu clicks
        menu_click_sound_list = [int(15000 * math.sin(2 * math.pi * 880 * i / SAMPLE_RATE)) for i in range(SAMPLE_RATE // 20)]
        # Explosion sound: decaying white noise
        explosion_sound_list = [int(random.uniform(-1, 1) * 20000 * (1 - i / (SAMPLE_RATE // 4))) for i in range(SAMPLE_RATE // 4)]
        # Level-up sound: A rising tone
        level_up_sound_list = []
        duration_samples = SAMPLE_RATE // 3 # 0.33 seconds
        for i in range(duration_samples):
            # Frequency sweep from C5 to C6
            start_freq = 523.25
            end_freq = 1046.50
            current_freq = start_freq + (end_freq - start_freq) * (i / duration_samples)
            # Fade out the amplitude
            amplitude = 18000 * (1 - (i / duration_samples))
            sample = amplitude * math.sin(2 * math.pi * current_freq * i / SAMPLE_RATE)
            level_up_sound_list.append(int(sample))
        # Harvest sound: A short, high-pitched "ding"
        harvest_sound_list = []
        duration_samples = int(SAMPLE_RATE * 0.1) # 0.1 seconds
        for i in range(duration_samples):
            freq = 1500 + 500 * (i / duration_samples) # Rising pitch
            amplitude = 10000 * math.sin(math.pi * (i / duration_samples)) # Fades in and out
            sample = amplitude * math.sin(2 * math.pi * freq * i / SAMPLE_RATE)
            harvest_sound_list.append(int(sample))
        
        # Hurt sound: A longer, more clear sine wave
        hurt_sound_list = []
        duration_samples = int(SAMPLE_RATE * 0.4) # 0.4 seconds
        frequency = 150 # Low frequency for a "thump"
        amplitude_envelope = 1.0 # Start at full volume
        for i in range(duration_samples):
            # A decaying sine wave
            amplitude_envelope = max(0, 1 - (i / duration_samples))
            sample = 15000 * amplitude_envelope * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)
            hurt_sound_list.append(int(sample))

        # Convert the lists to a NumPy array with the correct data type (signed 16-bit integers)
        # The mixer requires a 2-dimensional array for stereo sound, so we use column_stack to create two identical channels.
        laser_sound_1d = np.array(laser_sound_list, dtype=np.int16)
        menu_click_sound_1d = np.array(menu_click_sound_list, dtype=np.int16)
        explosion_sound_1d = np.array(explosion_sound_list, dtype=np.int16)
        level_up_sound_1d = np.array(level_up_sound_list, dtype=np.int16)
        harvest_sound_1d = np.array(harvest_sound_list, dtype=np.int16)
        hurt_sound_1d = np.array(hurt_sound_list, dtype=np.int16)

        laser_sound_data = np.column_stack((laser_sound_1d, laser_sound_1d))
        menu_click_sound_data = np.column_stack((menu_click_sound_1d, menu_click_sound_1d))
        explosion_sound_data = np.column_stack((explosion_sound_1d, explosion_sound_1d))
        level_up_sound_data = np.column_stack((level_up_sound_1d, level_up_sound_1d))
        harvest_sound_data = np.column_stack((harvest_sound_1d, harvest_sound_1d))
        hurt_sound_data = np.column_stack((hurt_sound_1d, hurt_sound_1d))
        
        self.laser_sound = pygame.mixer.Sound(pygame.sndarray.make_sound(laser_sound_data))
        self.explosion_sound = pygame.mixer.Sound(pygame.sndarray.make_sound(explosion_sound_data))
        self.menu_click_sound = pygame.mixer.Sound(pygame.sndarray.make_sound(menu_click_sound_data))
        self.level_up_sound = pygame.mixer.Sound(pygame.sndarray.make_sound(level_up_sound_data))
        self.harvest_sound = pygame.mixer.Sound(pygame.sndarray.make_sound(harvest_sound_data))
        self.hurt_sound = pygame.mixer.Sound(pygame.sndarray.make_sound(hurt_sound_data))

        # --- Background Music ---
        note_duration = int(SAMPLE_RATE * 0.5) # Each note is 0.5 seconds long
        frequencies = [65.41, 49.00, 58.27, 43.65] # Frequencies for C2, G1, A#1, F1
        music_sound_list = []
        for freq in frequencies:
            for i in range(note_duration):
                amplitude = 12000 * (1 - (i / note_duration)) # Decay envelope
                sample = amplitude * math.sin(2 * math.pi * freq * i / SAMPLE_RATE)
                music_sound_list.append(int(sample))
        music_sound_1d = np.array(music_sound_list, dtype=np.int16)
        music_sound_data = np.column_stack((music_sound_1d, music_sound_1d))
        self.background_music = pygame.mixer.Sound(pygame.sndarray.make_sound(music_sound_data))

        # List of all sounds to easily manage volume
        self.all_sounds = [self.laser_sound, self.explosion_sound, self.menu_click_sound, self.level_up_sound, self.harvest_sound, self.hurt_sound, self.background_music]
        self.update_volumes()

    def play_background_music(self):
        """Plays the background music on a loop if it's not already playing."""
        if not self.music_is_playing:
            self.background_music.play(loops=-1)
            self.music_is_playing = True

    def stop_background_music(self):
        """Stops the background music."""
        self.background_music.stop()
        self.music_is_playing = False

    def update_volumes(self):
        """Sets the volume for all sound effects based on the self.volume attribute."""
        for sound in self.all_sounds:
            sound.set_volume(self.volume)

    def draw_text(self, text, font, color, surface, x, y, center=True):
        textobj = font.render(text, 1, color)
        textrect = textobj.get_rect()
        if center:
            textrect.center = (x, y)
        else:
            textrect.x = x
            textrect.y = y
        surface.blit(textobj, textrect)
        return textobj, textrect

    def draw_lifebar(self, current_lives, max_lives):
        bar_width = 30
        bar_height = 15
        bar_spacing = 10
        
        start_x = 15
        start_y = 15
        
        for i in range(max_lives):
            bar_rect = pygame.Rect(start_x + i * (bar_width + bar_spacing), start_y, bar_width, bar_height)
            color = LIFE_COLOR if i < current_lives else DARK_BLUE
            pygame.draw.rect(self.screen, color, bar_rect)
            pygame.draw.rect(self.screen, WHITE, bar_rect, 2) # Outline

    def animate_background(self):
        self.screen.fill(DARK_BLUE)
        for star in self.stars:
            star.update()
            star.draw(self.screen)
            
    def draw_pause_symbol(self):
        overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        bar_width = 30
        bar_height = 100
        spacing = 20
        total_width = (bar_width * 2) + spacing
        
        center_x = self.SCREEN_WIDTH // 2
        center_y = self.SCREEN_HEIGHT // 2
        
        left_bar_rect = pygame.Rect(center_x - total_width // 2, center_y - bar_height // 2, bar_width, bar_height)
        right_bar_rect = pygame.Rect(center_x - total_width // 2 + bar_width + spacing, center_y - bar_height // 2, bar_width, bar_height)
        
        pygame.draw.rect(self.screen, WHITE, left_bar_rect)
        pygame.draw.rect(self.screen, WHITE, right_bar_rect)
        
    def draw_pause_menu(self, event):
        overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        menu_items = ["Resume", "Save Game", "Load Game", "Exit to Menu"]
        item_spacing = 80
        start_y = self.SCREEN_HEIGHT // 2
        
        exit_game = False
        resume_game = False
        load_game = False
        save_game = False # New state for the save game option

        for i, item in enumerate(menu_items):
            x = self.SCREEN_WIDTH // 2
            y = start_y + i * item_spacing
            
            text_surface = self.menu_font.render(item, True, MENU_TEXT_COLOR)
            text_rect = text_surface.get_rect(center=(x, y))

            if text_rect.collidepoint(pygame.mouse.get_pos()):
                text_surface = self.menu_font.render(item, True, HOVER_TEXT_COLOR)
                if event and event.type == pygame.MOUSEBUTTONDOWN:
                    self.menu_click_sound.play()
                    if item == "Resume":
                        resume_game = True
                    elif item == "Save Game":
                        save_game = True
                    elif item == "Load Game":
                        load_game = True
                    elif item == "Exit to Menu":
                        exit_game = True

            self.screen.blit(text_surface, text_rect)
        
        return resume_game, load_game, exit_game, save_game

    def title_screen(self):
        title_text = "Tristar Mania"
        fade_alpha = 0

        running = True
        start_time = pygame.time.get_ticks()
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN or pygame.time.get_ticks() - start_time > 3000:
                    self.menu_click_sound.play()
                    running = False

            self.animate_background()
            self.draw_text(title_text, self.font, WHITE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2)

            if fade_alpha < 255:
                fade_alpha += 5
            
            fade_surface = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
            fade_surface.fill(DARK_BLUE)
            fade_surface.set_alpha(255 - fade_alpha)
            self.screen.blit(fade_surface, (0, 0))

            pygame.display.flip()
            self.clock.tick(self.FPS)

    def video_settings_menu(self):
        pygame.mouse.set_visible(True) # Show cursor
        video_items = ["Fullscreen: ", "Resolution: ", "Back"]
        item_spacing = 100
        
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if fullscreen_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        self.FULLSCREEN = not self.FULLSCREEN
                        flags = pygame.FULLSCREEN if self.FULLSCREEN else 0
                        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), flags)
                    elif resolution_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        self.current_resolution_index = (self.current_resolution_index + 1) % len(self.resolutions)
                        self.SCREEN_WIDTH, self.SCREEN_HEIGHT = self.resolutions[self.current_resolution_index]
                        flags = pygame.FULLSCREEN if self.FULLSCREEN else 0
                        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), flags)
                        self.stars = [Star(self.SCREEN_WIDTH, self.SCREEN_HEIGHT) for _ in range(300)]
                    elif back_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        running = False
            
            self.animate_background()
            start_y = self.SCREEN_HEIGHT // 2 - (len(video_items) * item_spacing) // 2

            self.draw_text("Video Settings", self.font, WHITE, self.screen, self.SCREEN_WIDTH // 2, start_y - 100)
            
            fullscreen_text = f"Fullscreen: {'ON' if self.FULLSCREEN else 'OFF'}"
            _, fullscreen_rect = self.draw_and_get_rect(fullscreen_text, self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, start_y)
            
            current_res = f"{self.resolutions[self.current_resolution_index][0]}x{self.resolutions[self.current_resolution_index][1]}"
            resolution_text = f"Resolution: {current_res}"
            _, resolution_rect = self.draw_and_get_rect(resolution_text, self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, start_y + item_spacing)

            _, back_rect = self.draw_and_get_rect("Back", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, start_y + 2 * item_spacing)

            pygame.display.flip()
            self.clock.tick(self.FPS)

    def draw_and_get_rect(self, text, font, color, hover_color, x, y):
        mx, my = pygame.mouse.get_pos()
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(x, y))
        if text_rect.collidepoint((mx, my)):
            text_surface = font.render(text, True, hover_color)
        self.screen.blit(text_surface, text_rect)
        return text_surface, text_rect

    def audio_settings_menu(self):
        pygame.mouse.set_visible(True) # Show cursor
        item_spacing = 100
        start_y = self.SCREEN_HEIGHT // 2 - (2 * item_spacing) // 2

        slider_x = self.SCREEN_WIDTH // 2 - 150
        slider_y = start_y
        slider_width = 300
        slider_height = 20
        handle_width = 20
        
        running = True
        dragging_slider = False
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if handle_rect.collidepoint(event.pos):
                        dragging_slider = True
                    if back_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        running = False
                elif event.type == pygame.MOUSEBUTTONUP:
                    if dragging_slider:
                        self.menu_click_sound.play() # Play sound on release
                        dragging_slider = False
                elif event.type == pygame.MOUSEMOTION and dragging_slider:
                    mouse_x, _ = event.pos
                    new_volume = (mouse_x - slider_x) / slider_width
                    self.volume = max(0, min(1, new_volume))
                    self.update_volumes()

            self.animate_background()
            
            self.draw_text("Audio Settings", self.font, WHITE, self.screen, self.SCREEN_WIDTH // 2, start_y - 100)

            slider_rect = pygame.Rect(slider_x, slider_y, slider_width, slider_height)
            pygame.draw.rect(self.screen, SLIDER_BG_COLOR, slider_rect, border_radius=5)
            
            handle_x = slider_x + self.volume * slider_width - handle_width / 2
            handle_rect = pygame.Rect(handle_x, slider_y - 5, handle_width, slider_height + 10)
            pygame.draw.rect(self.screen, SLIDER_HANDLE_COLOR, handle_rect, border_radius=5)
            
            self.draw_text(f"Volume: {int(self.volume * 100)}%", self.small_font, WHITE, self.screen, slider_x + slider_width + 100, slider_y + 10)
            
            _, back_rect = self.draw_and_get_rect("Back", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, start_y + item_spacing)

            pygame.display.flip()
            self.clock.tick(self.FPS)
            
    def controls_settings_menu(self):
        pygame.mouse.set_visible(True) # Show cursor
        item_spacing = 100
        
        running = True
        while running:
            self.animate_background()
            start_y = self.SCREEN_HEIGHT // 2 - (len(self.keybinds) * item_spacing) // 2

            self.draw_text("Controls Settings", self.font, WHITE, self.screen, self.SCREEN_WIDTH // 2, start_y - 100)
            
            control_rects = {}
            for i, (action, key) in enumerate(self.keybinds.items()):
                # Get the key name, handling the special case for spacebar
                key_name = pygame.key.name(key).upper()
                if key == pygame.K_SPACE:
                    key_name = "SPACEBAR"
                text = f"{action}: {key_name}"
                _, rect = self.draw_and_get_rect(text, self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, start_y + i * item_spacing)
                control_rects[action] = rect

            _, back_rect = self.draw_and_get_rect("Back", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, start_y + len(self.keybinds) * item_spacing)

            if self.remapping_key_for:
                self.draw_text("Press any key...", self.font, WHITE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2)

            pygame.display.flip()
            self.clock.tick(self.FPS)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self.remapping_key_for:
                    if event.type == pygame.KEYDOWN:
                        self.menu_click_sound.play()
                        self.keybinds[self.remapping_key_for] = event.key
                        self.remapping_key_for = None
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if back_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        running = False
                    else:
                        for action, rect in control_rects.items():
                            if rect.collidepoint(event.pos):
                                self.menu_click_sound.play()
                                self.remapping_key_for = action
                                break
    def options_menu(self):
        options_items = ["Video", "Audio", "Controls", "Back"]
        item_spacing = 100
        
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if video_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        self.video_settings_menu()
                    elif audio_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        self.audio_settings_menu()
                    elif controls_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        self.controls_settings_menu()
                    elif back_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        running = False

            self.animate_background()
            start_y = self.SCREEN_HEIGHT // 2 - (len(options_items) * item_spacing) // 2

            self.draw_text("Options", self.font, WHITE, self.screen, self.SCREEN_WIDTH // 2, start_y - 100)
            
            _, video_rect = self.draw_and_get_rect("Video", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, start_y)
            _, audio_rect = self.draw_and_get_rect("Audio", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, start_y + item_spacing)
            _, controls_rect = self.draw_and_get_rect("Controls", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, start_y + 2 * item_spacing)
            _, back_rect = self.draw_and_get_rect("Back", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, start_y + 3 * item_spacing)
            
            pygame.display.flip()
            self.clock.tick(self.FPS)
            
    def main_menu(self):
        pygame.mouse.set_visible(True) # Show cursor
        menu_items = ["New Game", "Load Game", "Leaderboards", "Options", "Exit"]
        item_spacing = 100
        
        running = True
        while running:
            self.play_background_music() # Ensure music is playing in the menu
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if new_game_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        self.start_game_animation()
                    elif load_game_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        self.load_game_menu()
                    elif leaderboard_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        self.leaderboard_menu()
                    elif options_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        self.options_menu()
                    elif exit_rect.collidepoint(event.pos):
                        pygame.quit()
                        sys.exit()

            self.animate_background()
            
            # Draw the title and main menu text
            self.draw_text("Tristar Mania", self.font, WHITE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 250)
            self.draw_text("Main Menu", self.font, WHITE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 150)
            
            # Start the menu items further down to prevent overlap
            menu_start_y = self.SCREEN_HEIGHT // 2
            
            _, new_game_rect = self.draw_and_get_rect("New Game", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, menu_start_y)
            _, load_game_rect = self.draw_and_get_rect("Load Game", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, menu_start_y + item_spacing)
            _, leaderboard_rect = self.draw_and_get_rect("Leaderboards", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, menu_start_y + 2 * item_spacing)
            _, options_rect = self.draw_and_get_rect("Options", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, menu_start_y + 3 * item_spacing)
            _, exit_rect = self.draw_and_get_rect("Exit", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, menu_start_y + 4 * item_spacing)
            
            pygame.display.flip()
            self.clock.tick(self.FPS)

    def leaderboard_menu(self):
        """Displays the temporary leaderboard."""
        pygame.mouse.set_visible(True) # Show cursor
        
        running = True
        while running:
            self.animate_background()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if back_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        return # Exit the leaderboard menu

            self.draw_text("LEADERBOARD", self.font, LIGHT_BLUE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 200)

            # Draw the leaderboard
            for i, score in enumerate(self.high_scores):
                self.draw_text(f"{i + 1}. {score}", self.small_font, WHITE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 100 + i * 40)
            
            _, back_rect = self.draw_and_get_rect("Back", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT - 100)
            
            pygame.display.flip()
            self.clock.tick(self.FPS)
    
    def level_to_code(self, level):
        """Encodes a level number into a 4-letter code using base-26 + offset."""
        offset = 100000  # lowered so 4 letters can hold the value
        encoded_level = level + offset

        code_chars = []
        for _ in range(4):
            encoded_level, remainder = divmod(encoded_level, 26)
            code_chars.append(LETTER_MAPPING[remainder])

        # Reverse to get the correct order
        return ''.join(reversed(code_chars))

    def code_to_level(self, code):
        """Decodes a 4-letter code back into a level number."""
        offset = 100000
        if len(code) != 4:
            return 1  # default to level 1 if code length is wrong

        value = 0
        for char in code:
            if char not in LETTER_MAPPING:
                return 1  # invalid characters fallback
            value = value * 26 + LETTER_MAPPING.index(char)

        decoded_level = value - offset
        return max(1, decoded_level)

 # Ensure level is at least 1
    
    def save_game_screen(self, level):
        """Displays the save code for the current level."""
        pygame.mouse.set_visible(True) # Show cursor
        save_code = self.level_to_code(level)
        
        running = True
        while running:
            self.animate_background()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.menu_click_sound.play()
                    return # Exit save screen and return to pause menu

            self.draw_text("SAVE CODE", self.font, WHITE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 150)
            
            # Display the generated code
            self.draw_text(save_code, self.font, LIGHT_BLUE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2)
            
            self.draw_text("Write this code down to load this level later.", self.small_font, MENU_TEXT_COLOR, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 + 100)
            self.draw_text("Click to return to the menu", self.small_font, MENU_TEXT_COLOR, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT - 50)
            
            pygame.display.flip()
            self.clock.tick(self.FPS)

    def load_game_menu(self):
        """Handles the text input for the load code."""
        pygame.mouse.set_visible(True) # Show cursor
        input_text = ""
        input_box_rect = pygame.Rect(self.SCREEN_WIDTH // 2 - 150, self.SCREEN_HEIGHT // 2 - 25, 300, 50)
        
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.menu_click_sound.play()
                        initial_level = self.code_to_level(input_text)
                        self.start_game_animation(start_level=initial_level)
                        return # Exit the load menu
                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    else:
                        if len(input_text) < 4:
                            input_text += event.unicode.upper()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if back_rect.collidepoint(event.pos):
                        self.menu_click_sound.play()
                        return # Exit the load menu
            
            self.animate_background()
            self.draw_text("Enter 4-letter code", self.font, WHITE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 100)

            # Draw the input box
            pygame.draw.rect(self.screen, LIGHT_BLUE, input_box_rect, 2)
            input_text_surface = self.menu_font.render(input_text, True, WHITE)
            self.screen.blit(input_text_surface, (input_box_rect.x + 10, input_box_rect.y + 10))
            
            _, back_rect = self.draw_and_get_rect("Back", self.menu_font, MENU_TEXT_COLOR, HOVER_TEXT_COLOR, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 + 100)

            pygame.display.flip()
            self.clock.tick(self.FPS)

    def game_over_screen(self, final_score):
        """Displays the game over screen with the temporary leaderboard."""
        pygame.mouse.set_visible(True) # Show cursor
        self.high_scores.append(final_score)
        self.high_scores.sort(reverse=True)
        # Keep only the top 5 scores
        self.high_scores = self.high_scores[:5]
        
        # Calculate level based on the new incremental formula
        if final_score < 0: final_score = 0
        # Formula to find level L from score S: 25L^2 + 425L - (450 + S) = 0
        # Using the quadratic formula solution for L
        final_level = int((-425 + math.sqrt(225625 + 100 * final_score)) / 50)
        
        save_code = self.level_to_code(final_level)

        running = True
        while running:
            self.animate_background()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.menu_click_sound.play()
                    return # Exit the game over screen and return to main menu

            self.draw_text("GAME OVER", self.font, ENEMY_COLOR, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 200)
            self.draw_text(f"Your Score: {final_score}", self.menu_font, WHITE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 100)
            
            self.draw_text(f"Level Code: {save_code}", self.menu_font, LIGHT_BLUE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 40)
            
            # Draw the leaderboard
            self.draw_text("LEADERBOARD", self.leaderboard_font, LIGHT_BLUE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2)
            for i, score in enumerate(self.high_scores):
                self.draw_text(f"{i + 1}. {score}", self.small_font, WHITE, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 + 50 + i * 40)
            
            self.draw_text("Click to return to menu", self.small_font, MENU_TEXT_COLOR, self.screen, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT - 50)
            
            pygame.display.flip()
            self.clock.tick(self.FPS)

    def start_game_animation(self, start_level=1):
        """
        Starts the game with a flight animation.
        start_level: The level to begin at.
        """
        self.stop_background_music() # Stop menu music when game starts
        
        spaceship = Spaceship(self.SCREEN_WIDTH, self.SCREEN_HEIGHT)
        is_paused = False
        frame_counter = 0
        
        # Set initial score and level based on start_level and new progression
        level = start_level
        # Total score S to reach level L: S(L) = (L-1) * (450 + 25L)
        score = int((start_level - 1) * (450 + 25 * start_level)) if start_level > 1 else 0
        # Score required for next level (L+1): S(L+1) = L * (475 + 25L)
        score_for_next_level = int(level * (475 + 25 * level))

        lives = 4 # Start with 4 lives
        max_lives = 4 # Track maximum lives
        boss_spawned_this_level = False # New flag for boss spawning

        # Lists for obstacles and lasers
        rocks = []
        enemies = []
        neutrals = []
        bosses = [] # New list for bosses
        player_lasers = []
        enemy_lasers = []
        harvest_particles = []

        # Initial flight animation phase
        pygame.mouse.set_visible(False) # Hide cursor during gameplay
        while spaceship.y > self.SCREEN_HEIGHT / 3:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            
            self.animate_background()
            spaceship.y -= spaceship.max_velocity
            spaceship.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(self.FPS)
        
        # Player control phase
        running = True
        while running:
            event = None
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        self.menu_click_sound.play()
                        is_paused = not is_paused
                    if not is_paused and e.key == self.keybinds["Shoot"]:
                        self.laser_sound.play()
                        # Create a new laser from the spaceship's position and direction, passing the current level
                        new_laser = Laser(spaceship.x, spaceship.y, spaceship.direction, self.SCREEN_WIDTH, self.SCREEN_HEIGHT, level=level)
                        player_lasers.append(new_laser)
                event = e
            
            if not is_paused:
                pygame.mouse.set_visible(False)
                # Handle spaceship movement
                keys = pygame.key.get_pressed()
                if keys[self.keybinds["Move Up"]] or keys[pygame.K_UP]:
                    spaceship.move_forward()
                elif keys[self.keybinds["Move Down"]] or keys[pygame.K_DOWN]:
                    spaceship.move_backward()
                else:
                    spaceship.stop()

                if keys[self.keybinds["Move Left"]] or keys[pygame.K_LEFT]:
                    spaceship.rotate_left()
                if keys[self.keybinds["Move Right"]] or keys[pygame.K_RIGHT]:
                    spaceship.rotate_right()
                
                spaceship.update()

                # Spawn obstacles periodically
                frame_counter += 1
                if frame_counter % SPAWN_RATE == 0:
                    obstacle_type = random.choice(["rock", "enemy", "neutral"])
                    if obstacle_type == "rock":
                        rocks.append(SpaceRock(self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
                    elif obstacle_type == "enemy":
                        enemies.append(EnemySpaceship(self.SCREEN_WIDTH, self.SCREEN_HEIGHT, level))
                    elif obstacle_type == "neutral":
                        neutrals.append(NeutralSpaceship(self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
                
                # Spawn boss if conditions are met
                if level >= 4 and not boss_spawned_this_level and not bosses:
                    bosses.append(Boss(self.SCREEN_WIDTH, self.SCREEN_HEIGHT, level))
                    boss_spawned_this_level = True


                # Update and draw obstacles and lasers
                for rock in rocks:
                    rock.update()
                for enemy in enemies:
                    enemy.update((spaceship.x, spaceship.y), level)
                    if enemy.can_shoot(pygame.time.get_ticks(), level):
                        self.laser_sound.play()
                        enemy_lasers.append(enemy.shoot((spaceship.x, spaceship.y)))
                for neutral in neutrals:
                    neutral.update()
                for boss in bosses:
                    boss.update((spaceship.x, spaceship.y))
                    if boss.can_shoot(pygame.time.get_ticks(), level):
                        self.laser_sound.play()
                        enemy_lasers.append(boss.shoot((spaceship.x, spaceship.y)))
                for laser in player_lasers:
                    laser.update()
                for laser in enemy_lasers:
                    laser.update()

                # Update explosions
                for explosion in self.explosions:
                    explosion.update()
                self.explosions = [exp for exp in self.explosions if not exp.is_done]
                
                # Update harvest particles
                for particle in harvest_particles:
                    particle.update((spaceship.x, spaceship.y))
                harvest_particles = [p for p in harvest_particles if p.lifespan > 0]
            
            self.animate_background()
            
            # Draw all objects
            spaceship.draw(self.screen)
            for rock in rocks:
                rock.draw(self.screen)
            for enemy in enemies:
                enemy.draw(self.screen)
            for neutral in neutrals:
                neutral.draw(self.screen)
            for boss in bosses: # Draw boss
                boss.draw(self.screen)
            for laser in player_lasers:
                laser.draw(self.screen)
            for laser in enemy_lasers:
                laser.draw(self.screen)

            # Draw explosions on top
            for explosion in self.explosions:
                explosion.draw(self.screen)
            
            # Draw harvest particles on top
            for particle in harvest_particles:
                particle.draw(self.screen)


            # Check for collisions only when not paused
            if not is_paused:
                # Check for collisions that destroy the player
                if not spaceship.invulnerable:
                    player_collided_physically = False
                    # Player vs Rocks
                    for rock in rocks[:]:
                        if spaceship.check_collision(rock.rect):
                            self.hurt_sound.play()
                            self.explosions.append(Explosion(rock.rect.centerx, rock.rect.centery))
                            lives -= 1
                            rocks.remove(rock)
                            player_collided_physically = True
                            break
                    # Player vs Enemies
                    if not player_collided_physically:
                        for enemy in enemies[:]:
                            if spaceship.check_collision(enemy.rect):
                                self.hurt_sound.play()
                                self.explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery))
                                lives -= 1
                                enemies.remove(enemy)
                                player_collided_physically = True
                                break
                    # Player vs Boss
                    if not player_collided_physically:
                        for boss in bosses[:]:
                            if spaceship.check_collision(boss.rect):
                                self.hurt_sound.play()
                                self.explosions.append(Explosion(spaceship.rect.centerx, spaceship.rect.centery, num_particles=50))
                                lives -= 2  # Boss collision is more punishing
                                player_collided_physically = True
                                break # Only one boss, but good practice
                    
                    # If a physical collision happened, respawn the ship
                    if player_collided_physically:
                        if lives <= 0:
                            self.game_over_screen(score)
                            return
                        else:
                            spaceship.respawn()
                    
                    # Player vs Enemy Lasers (handled separately, does not trigger respawn)
                    # This check happens only if the ship isn't invulnerable from a recent respawn
                    if not spaceship.invulnerable:
                        for laser in enemy_lasers[:]:
                            if spaceship.check_collision(laser.rect):
                                self.hurt_sound.play()
                                self.explosions.append(Explosion(laser.rect.centerx, laser.rect.centery))
                                lives -= 1
                                enemy_lasers.remove(laser)
                                if lives <= 0:
                                    self.game_over_screen(score)
                                    return
                                # No respawn, no invulnerability for laser hits
                                break # Process one laser hit per frame

                # Check for collisions between player's lasers and obstacles
                for laser in player_lasers[:]:
                    collided = False
                    for rock in rocks[:]:
                        if laser.rect.colliderect(rock.rect):
                            self.explosion_sound.play()
                            self.explosions.append(Explosion(rock.rect.centerx, rock.rect.centery))
                            score += rock.score_value
                            player_lasers.remove(laser)
                            rocks.remove(rock)
                            if rock.is_life_rock:
                                self.harvest_sound.play()
                                for _ in range(10):
                                    harvest_particles.append(HarvestParticle(rock.rect.centerx, rock.rect.centery))
                            if lives < max_lives:
                                lives += 1
                            collided = True
                            break
                    if collided: continue

                    for enemy in enemies[:]:
                        if laser.rect.colliderect(enemy.rect):
                            self.explosion_sound.play()
                            self.explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery))
                            score += enemy.score_value
                            player_lasers.remove(laser)
                            enemies.remove(enemy)
                            collided = True
                            break
                    if collided: continue

                    for neutral in neutrals[:]:
                        if laser.rect.colliderect(neutral.rect):
                            self.explosion_sound.play()
                            self.explosions.append(Explosion(neutral.rect.centerx, neutral.rect.centery))
                            player_lasers.remove(laser)
                            neutrals.remove(neutral)
                            self.hurt_sound.play()
                            lives -= 1
                            if lives <= 0:
                                self.game_over_screen(score)
                                return
                            break
                    if collided: continue

                    for boss in bosses[:]:
                        if laser.rect.colliderect(boss.rect):
                            player_lasers.remove(laser)
                            boss.take_damage(1)
                            if boss.is_destroyed:
                                self.explosion_sound.play()
                                # Bigger explosion for the boss
                                self.explosions.append(Explosion(boss.rect.centerx, boss.rect.centery, num_particles=100))
                                score += boss.score_value # This will now add 0
                                bosses.remove(boss)
                            collided = True
                            break
                        
                # Check for collisions between player and harvest particles
                for particle in harvest_particles[:]:
                    if spaceship.check_collision(particle.rect):
                        score += 5
                        harvest_particles.remove(particle)

                # Update the level based on the new incremental score requirement
                if score >= score_for_next_level:
                    level += 1
                    self.level_up_sound.play()
                    max_lives += 1
                    lives += 1
                    boss_spawned_this_level = False
                    # Calculate the score required for the *new* next level
                    score_for_next_level = int(level * (475 + 25 * level))

                # Remove off-screen objects
                rocks = [rock for rock in rocks if not rock.is_off_screen()]
                enemies = [enemy for enemy in enemies if not enemy.is_off_screen()]
                bosses = [boss for boss in bosses if not boss.is_off_screen()] # Remove off-screen boss
                player_lasers = [laser for laser in player_lasers if not laser.is_off_screen()]
                enemy_lasers = [laser for laser in enemy_lasers if not laser.is_off_screen()]

            # Draw the lifebar
            self.draw_lifebar(lives, max_lives)
            
            # Draw score and level on the left side
            self.draw_text(f"Score: {score}", self.score_font, WHITE, self.screen, 15, 60, center=False)
            self.draw_text(f"Level: {level}", self.score_font, WHITE, self.screen, 15, 105, center=False)

            if is_paused:
                pygame.mouse.set_visible(True)
                resume_game, load_game, exit_game, save_game = self.draw_pause_menu(event)
                if resume_game:
                    is_paused = False
                elif save_game:
                    self.save_game_screen(level)
                    is_paused = True
                elif load_game:
                    self.load_game_menu()
                    return
                elif exit_game:
                    return

            pygame.display.flip()
            self.clock.tick(self.FPS)

# --- Start the game ---
if __name__ == "__main__":
    game = Game()
    game.title_screen()
    game.main_menu()
