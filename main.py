import os
from time import sleep
import pygame
import sys
import math
import numpy as np
import skfuzzy
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.backends.backend_agg as agg
from fuzzy_ship_controller import FuzzyShipController

from map import Map
from spaceship import Ammo, Spaceship, ShipController, Heart
from keyboard_ship_controller import KeyboardShipController

def get_env_boolean(key: str, default: bool) -> bool:
    return os.getenv(key, 'y' if default else 'n').lower()[0] in ('t', '1', 'y')

USE_PYGAME_MATPLOTLIB_BACKEND = get_env_boolean('USE_PYGAME_MATPLOTLIB_BACKEND', False)

if USE_PYGAME_MATPLOTLIB_BACKEND:
    matplotlib.use('module://pygame_matplotlib.backend_pygame')
else:
    matplotlib.use('Agg')

pygame.init()
pygame.font.init()

FPS = 60
MAX_WIDTH = 900
MAX_HEIGHT = 900
CHARTS_AREA_WIDTH = 0

map = Map('maps/2.png', MAX_WIDTH - CHARTS_AREA_WIDTH, MAX_HEIGHT) 
map.default_wall_condition = lambda x_y, map : map.surface.get_at((int(x_y[0]), int(x_y[1])))[1] > 100 # green

screen = pygame.display.set_mode((map.width + CHARTS_AREA_WIDTH, map.height))
pygame.display.set_caption("Fuzzy Space Shooter!")

try:
    my_font = pygame.font.SysFont('consolas', 16)
except:
    my_font = pygame.font.SysFont('dejavusansmono', 16)
    pass

def draw_text(
        text: str, 
        position, 
        size: int,
        font: pygame.font.Font = my_font, 
        surface: pygame.Surface = screen, 
        color: pygame.Color = (0, 0, 0)):
    position = list(position)
    for line in text.splitlines():
        text_surface = my_font.render(line, True, color)
        surface.blit(text_surface, position)
        position[1] += font.get_height()
        font.set_point_size(size)
        font.set_bold(True)

def restart_game():
      enemySpaceship.position[0] =  map.starting_position[0] + 90
      enemySpaceship.position[1] =  map.starting_position[1] + 0
      enemySpaceship.angle = map.starting_angle
      enemySpaceship.health = 3
      
      playerSpaceship.position[0] =  map.starting_position[0] - 60
      playerSpaceship.position[1] =  map.starting_position[1] + 0
      playerSpaceship.angle = map.starting_angle
      playerSpaceship.health = 3

clock = pygame.time.Clock()

enemySpaceship = Spaceship("enemy_ship.png", tuple(a + b for a, b in zip(map.starting_position, (90,0))), map.starting_angle)
playerSpaceship = Spaceship("player_ship.png", tuple(a + b for a, b in zip(map.starting_position, (-60,0))), map.starting_angle, enemySpaceship.position)

# Health & Ammo
initPlayerHealthPosX = pygame.display.get_surface().get_size()[0] - (30 * 3)
playerHealthArray = [Heart("assets/heart.png", (initPlayerHealthPosX, 30)),
                    Heart("assets/heart.png", (initPlayerHealthPosX + 30, 30)),
                    Heart("assets/heart.png", (initPlayerHealthPosX + 60, 30))]
playerAmmo = Ammo("assets/charge.png", (initPlayerHealthPosX - 30, 30))

initEnemyHealthPosY = pygame.display.get_surface().get_size()[1] - (30 * 1)
enemyHealthArray = [Heart("assets/black_heart.png", (30, initEnemyHealthPosY)),
                    Heart("assets/black_heart.png", (30 + 30, initEnemyHealthPosY)),
                    Heart("assets/black_heart.png", (30 + 60, initEnemyHealthPosY))]
enemyAmmo = Ammo("assets/charge.png", (30 + 90, initEnemyHealthPosY - 1.5))

enemySpaceship.default_wall_condition = lambda x_y, spaceship: spaceship.is_near_enemy(x_y, playerSpaceship.position)
playerSpaceship.default_wall_condition = lambda x_y, spaceship: spaceship.is_near_enemy(x_y, enemySpaceship.position)

sensors_angles = {
    'head': math.radians(0),
    'left': math.radians(30),
    'right': math.radians(-30),
    'hard_left': math.radians(90),
    'hard_right': math.radians(-90),
}

keyboard_ship_controller = KeyboardShipController(playerSpaceship)
fuzzy_ship_controller = FuzzyShipController(enemySpaceship)

player_controller: ShipController = keyboard_ship_controller
enemy_controller: ShipController = fuzzy_ship_controller

all_sprites = pygame.sprite.Group()
all_sprites.add(playerSpaceship)
all_sprites.add(enemySpaceship)

# Background
background = pygame.image.load('maps/3.png')
background_rect = background.get_rect(center=(map.width // 2, map.height // 2))
# <--

paused = False
running = True
end = False
playerWon = False

while running:
    dt = clock.tick(FPS) / 1000 # s

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                running = False
            if event.key == pygame.K_r:
                playerSpaceship.position = list(map.starting_position)
                playerSpaceship.angle = map.starting_angle
                playerSpaceship.velocity = 0
            if ((event.key == pygame.K_p) and end==False):
                paused = not paused
            if event.key == pygame.K_f: 
                playerSpaceship.fire_projectiles(0)
            if ((event.key == pygame.K_SPACE) and end==True):             
                paused = False
                running = True
                end = False
                playerWon = False
                restart_game(); 

    wall_ray_casts = {k: map.cast_ray_to_wall(enemySpaceship.position, enemySpaceship.angle + v) 
                      for k, v in sensors_angles.items()}
    
    ship_ray_casts = {k: enemySpaceship.cast_ray_to_ship(enemySpaceship.position, enemySpaceship.angle + v) 
                    for k, v in sensors_angles.items()}
    
    if not paused:
        try:
            fuzzy_ship_controller.update_simulation(wall_sensors=wall_ray_casts, enemy_sensors=ship_ray_casts)
        except ValueError as error:
            print('Error updating simulation:', error)
            try:
                fuzzy_ship_controller.simulation.print_state()
            except ValueError as error:
                print('Further error printing out state:', error)
                print('inputs: ' + ' '.join([f'{v.label}={v.input["current"]}, ' for v in fuzzy_ship_controller.inputs]))
            sleep(0.100)

        playerSpaceship.check_collision(enemySpaceship.projectiles)
        enemySpaceship.check_collision(playerSpaceship.projectiles)
        
        playerSpaceship.check_screen_boundaries()
        enemySpaceship.check_screen_boundaries()
        
        if (playerSpaceship.health == 0):
            end = True
            playerWon = False
        if (enemySpaceship.health == 0):
            end = True
            playerWon = True 

        player_controller.update(dt=dt)
        enemy_controller.update(dt=dt)
        
        all_sprites.update(dt=dt)
        
    screen.blit(map.surface, (0, 0))
    # Cover
    screen.blit(background, background_rect.topleft)
    # <--
    
    # Blink effect
    if (playerSpaceship.health_timer > 0):
        if (playerSpaceship.blink_counter % 2) == 0: 
            playerSpaceship.set_opacity(0)
        else:
            playerSpaceship.set_opacity(255)
    else: 
        playerSpaceship.set_opacity(255)
        
    # Blink effect
    if (enemySpaceship.health_timer > 0):
        if (enemySpaceship.blink_counter % 2) == 0: 
            enemySpaceship.set_opacity(0)
        else:
            enemySpaceship.set_opacity(255)
    else: 
        enemySpaceship.set_opacity(255)
    
    all_sprites.draw(screen)
    
    # Desenha os projéteis do jogador
    playerSpaceship.projectiles.draw(screen)
    enemySpaceship.projectiles.draw(screen)

    # Health
    for i in range(playerSpaceship.health):
        playerHealthArray[i].draw(screen)

    # Health
    for i in range(enemySpaceship.health):
        enemyHealthArray[i].draw(screen)
        
    # # Blink effect
    # if (enemySpaceship.health_timer > 0):
    #     if (enemySpaceship.blink_counter % 2 == 0): 
    #         enemySpaceship.draw(screen)
    # else: 
    #     enemySpaceship.draw(screen)
    
    # Ammo
    if (playerSpaceship.shoot_timer == 0): playerAmmo.draw(screen)
    if (enemySpaceship.shoot_timer == 0): enemyAmmo.draw(screen)


    # for k, v in wall_ray_casts.items():
    #     v.draw(screen, pygame.Color(99, 20, 20), width=2)
        
    for k, v in ship_ray_casts.items():
        v.draw(screen, pygame.Color(0, 0, 100), width=2)

    if (end==True and playerWon==False): 
        paused = True
        draw_text(f'Game Over! =(\nSPACE to try again!', position=(MAX_WIDTH / 5,MAX_HEIGHT / 6.25), color=(255, 0, 0), size=32)
    if (end==True and playerWon==True): 
        paused = True
        draw_text(f'You Win! =)\nSPACE to try again!', position=(MAX_WIDTH / 4,MAX_HEIGHT / 6.25), color=(0, 255, 0), size=32)

    pygame.display.flip()

pygame.quit()
sys.exit()
