from dataclasses import dataclass
import pygame
import math
from typing import Callable, Sequence

from map import Coordinate

Coordinate_Cast = Sequence[float] 
PlayerWallCondition = Callable[[Coordinate, 'Spaceship'], bool]

@dataclass
class RayCastResult:
    start_position: Coordinate
    hit_position: Coordinate | None  # none if missed
    angle: float  # radians
    distance: int  # steps, but works as distance as well; max distance used if missed

    @property
    def hit(self):
        return self.hit_position is not None

    def draw(self, surface, color: pygame.Color, width=1):
        if self.hit:
            pygame.draw.line(surface, color, self.start_position, self.hit_position, width)

class Heart(pygame.sprite.Sprite):
    def __init__(self, image_path, position):
        super().__init__()
        self.image = pygame.transform.scale(pygame.image.load(image_path), (30, 30))
        self.rect = self.image.get_rect(center=position)
        
    def hit(self):
        self.kill()
        
    def draw(self, screen):
        screen.blit(self.image, self.rect)
    
class Ammo(pygame.sprite.Sprite):
    def __init__(self, image_path, position):
        super().__init__()
        self.image = pygame.transform.scale(pygame.image.load(image_path), (30, 30))
        self.rect = self.image.get_rect(center=position)
        
    def cooldown(self):
        self.kill()
        
    def draw(self, screen):
        screen.blit(self.image, self.rect)

class Projectile(pygame.sprite.Sprite):
    def __init__(self, imgPath, position: Coordinate, angle: float, iniVelocity: float = 0, acceleration: float = 100):
        super().__init__()
        self.base_image = pygame.transform.scale(pygame.image.load(imgPath), (10, 5))
        self.rect = self.base_image.get_rect(center=position)
        self.position = list(position)
        self.angle = angle
        self.acceleration = acceleration
        self.velocity = max(iniVelocity, 300)
        self.screen_width, self.screen_height = pygame.display.get_surface().get_size()

    def update(self, dt):
        self.velocity += self.acceleration * dt
        self.position[0] += self.velocity * math.sin(self.angle) * dt
        self.position[1] += self.velocity * math.cos(self.angle) * dt
                
        self.image = pygame.transform.rotate(self.base_image, math.degrees(self.angle) - 90)
        self.rect = self.image.get_rect(center=self.position)
        self.rect.center = self.position
        
        # Remove o projétil se ele sair da tela
        if not self.rect.colliderect(pygame.Rect(0, 0, self.screen_width, self.screen_height)):
            self.kill()  # Remove o sprite do grupo de sprites

class Spaceship(pygame.sprite.Sprite):
    MAX_VELOCITY_FORWARD = 200
    MAX_VELOCITY_BACKWARD = 20
    ACCELERATION_FACTOR_FORWARD = 100
    ACCELERATION_FACTOR_BACKWARD = 100
    BRAKING_FACTOR = 50
    IDLE_DECAY_FACTOR = 5
    STEER_DECAY_FACTOR = 20

    def __init__(self, imgPath, position: Coordinate, angle: float = 0, enemy_position: Coordinate = (0, 0)):
        super().__init__()
        self.size = (56, 56) 
        self.base_image = pygame.transform.scale(pygame.image.load(imgPath), (self.size[0], self.size[1]))
        self.position = list(position)
        self.velocity: float = 30
        self.angle = angle  # radians
        self.enemy_position = enemy_position
        self.default_wall_condition: PlayerWallCondition = lambda x_y, spaceship: \
            self.is_near_enemy(x_y, self.enemy_position)
        self.projectiles = pygame.sprite.Group()
        
        self.shoot_cooldown: float = 1.0  # Tempo de cooldown entre disparos
        self.shoot_timer = 0.0  # Temporizador para controle de cooldown
        
        self.health = 3 
        self.max_health = 3 
        
        self.health_cooldown: float = 1.0
        self.health_timer = 0.0
        
        self.blink_cooldown: float = 0.25
        self.blink_timer = 0.0
        self.blink_counter = 0
        
        self.screen_width, self.screen_height = pygame.display.get_surface().get_size()
    
    def receive_damage(self):
        if self.health_timer <= 0: 
            self.health -= 1
            if self.health <= 0:
                self.health = 0
            # Define o cooldown antes do próximo dano
            self.health_timer = self.health_cooldown
            self.blink_timer = self.blink_cooldown
            self.blink_counter = 0
            
    def check_collision(self, projectiles):
        for projectile in projectiles:
            if pygame.sprite.collide_rect(self, projectile):
                self.receive_damage()

    def check_screen_boundaries(self):
        if (self.position[0] < 0 + self.size[0] / 2): 
            self.receive_damage()
            self.position[0] = self.screen_width / 2
            self.position[1] = self.screen_height / 2
            self.velocity = 1
        if (self.position[0] > self.screen_width - self.size[0] / 2):
            self.receive_damage()
            self.position[0] = self.screen_width / 2
            self.position[1] = self.screen_height / 2
            self.velocity = 1
        if (self.position[1] < 0 + self.size[1] / 2):
            self.receive_damage()
            self.position[0] = self.screen_width / 2
            self.position[1] = self.screen_height / 2
            self.velocity = 1
        if (self.position[1] > self.screen_height - self.size[1] / 2): 
            self.receive_damage()
            self.position[0] = self.screen_width / 2
            self.position[1] = self.screen_height / 2
            self.velocity = 1
        
    
    @property
    def width(self):
        return self.size[0]

    @property
    def height(self):
        return self.size[1]

    def update(self, dt: float):
        self.brake(dt * Spaceship.IDLE_DECAY_FACTOR)

        self.position[0] += self.velocity * math.sin(self.angle) * dt
        self.position[1] += self.velocity * math.cos(self.angle) * dt

        self.image = pygame.transform.rotate(self.base_image, math.degrees(self.angle) - 90)
        self.rect = self.image.get_rect(center=self.position)        
        
        self.projectiles.update(dt)
        
        # Health Cooldown
        self.health_timer = max(0, self.health_timer - dt)
        if self.health_timer > 0:
            self.blink_timer = max(0, self.blink_timer - dt)
            if self.blink_timer <= 0 and self.blink_counter <= 4:
                self.blink_counter += 1
                self.blink_timer = self.blink_cooldown
        
        # Ammo Cooldown
        self.shoot_timer = max(0, self.shoot_timer - dt)

    def set_opacity(self, alpha: int):
        """Set the opacity of the spaceship image."""
        # self.image = self.base_image.copy()
        self.image.set_alpha(alpha)

    def accelerate(self, value: float):
        self.velocity += value

    def brake(self, value: float):
        s = math.copysign(1.0, self.velocity)
        self.velocity = s * max(0, abs(self.velocity) - value)

    def rotate(self, angle_delta: float):
        self.angle += angle_delta

    def fire_projectiles(self, t: int = 0):
        if self.shoot_timer <= 0:
            # Tamanho da imagem da nave
            ship_width, ship_height = self.base_image.get_size()

            # Raio da ponta da nave (ajustável)
            tip_radius = (ship_width / 2) - 2.5

            # Calcula a posição inicial dos projéteis considerando a direção da nave
            bullet_01_pos_x = self.position[0] + tip_radius * math.cos(self.angle)
            bullet_01_pos_y = self.position[1] - tip_radius * math.sin(self.angle)
            
            bullet_02_pos_x = self.position[0] - tip_radius * math.cos(self.angle)
            bullet_02_pos_y = self.position[1] + tip_radius * math.sin(self.angle)
        
            if t == 0:
                projectile_01 = Projectile("assets/blue_laser_bullet.png", (bullet_01_pos_x, bullet_01_pos_y), self.angle, self.velocity)
                projectile_02 = Projectile("assets/blue_laser_bullet.png", (bullet_02_pos_x, bullet_02_pos_y), self.angle, self.velocity)
            else:
                projectile_01 = Projectile("assets/red_laser_bullet.png", (bullet_01_pos_x, bullet_01_pos_y), self.angle, self.velocity)
                projectile_02 = Projectile("assets/red_laser_bullet.png", (bullet_02_pos_x, bullet_02_pos_y), self.angle, self.velocity)
            self.projectiles.add(projectile_01)
            self.projectiles.add(projectile_02)
        
            # Define o cooldown antes do próximo disparo
            self.shoot_timer = self.shoot_cooldown

    def is_near_enemy(self, position: Coordinate, enemy_position: Coordinate, threshold_distance: float = 50):
        distance = math.sqrt((position[0] - enemy_position[0]) ** 2 + (position[1] - enemy_position[1]) ** 2)
        return distance < threshold_distance
    
    def cast_ray_to_ship(self, 
                         position: Sequence[float], 
                         angle: float, 
                         max_distance: int = 500, 
                         condition: PlayerWallCondition = None):
        if condition is None:
            condition = self.default_wall_condition
        dx, dy = math.sin(angle), math.cos(angle)
        x, y = position
        for distance in range(0, max_distance, 1):
            x += dx
            # if x < 0 or self.width <= x:
            #     break # misses
            y += dy
            # if y < 0 or self.height <= y:
            #     break # misses
            if condition((x, y), self):
                return RayCastResult(position, (x, y), angle, distance)  # hit
        return RayCastResult(position, None, angle, max_distance)  # missed
    

class ShipController():
    def __init__(self, ship: Spaceship):
        self.ship = ship
        self.brake: float = 0
        self.gas: float = 0
        self.steer: float = 0

    def update(self, dt: float, *args, **kwargs):
        self.brake = max(0, min(1, self.brake))
        self.gas   = max(-1, min(1, self.gas))
        self.steer = max(-1, min(1, self.steer))

        if self.gas > 0:
            if self.ship.velocity < 0:
                self.ship.brake(dt * Spaceship.BRAKING_FACTOR)
            else:
                self.ship.accelerate(dt * Spaceship.ACCELERATION_FACTOR_FORWARD * (1.1 - self.ship.velocity / Spaceship.MAX_VELOCITY_FORWARD))
                self.ship.velocity = min(self.ship.velocity, Spaceship.MAX_VELOCITY_FORWARD)
        elif self.gas < 0:
            if self.ship.velocity > 0:
                self.ship.brake(dt * Spaceship.BRAKING_FACTOR)
            else:
                self.ship.accelerate(-dt * Spaceship.ACCELERATION_FACTOR_BACKWARD * (1.1 - self.ship.velocity / Spaceship.MAX_VELOCITY_BACKWARD))
                self.ship.velocity = max(-Spaceship.MAX_VELOCITY_BACKWARD, self.ship.velocity)

        if self.brake > 0:
            self.ship.brake(dt * Spaceship.BRAKING_FACTOR * self.brake)

        if self.steer != 0:
            self.ship.rotate(math.radians(dt * 100) * self.steer)
            self.ship.brake(dt * Spaceship.STEER_DECAY_FACTOR)
