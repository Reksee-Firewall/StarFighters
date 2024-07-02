import pygame

from spaceship import Spaceship, ShipController

class KeyboardShipController(ShipController):
    def __init__(self, ship: Spaceship):
        super().__init__(ship)

    def update(self, dt: float, *args, **kwargs):
        keys = pygame.key.get_pressed()

        if keys[pygame.K_UP] and keys[pygame.K_DOWN]:
            self.gas = 5.0
        elif keys[pygame.K_UP]:
            self.gas = 5.0
        elif keys[pygame.K_DOWN]:
            self.gas = -1
        else:
            self.gas = 0

        steer = 0
        if keys[pygame.K_LEFT]:
            steer += 5
        if keys[pygame.K_RIGHT]:
            steer -= 5
        self.steer = steer

        if keys[pygame.K_SPACE]:
            self.brake = 1
        else:
            self.brake = 0

        super().update(dt, *args, **kwargs)
