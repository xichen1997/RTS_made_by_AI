# game.py
import pygame
from network import client

class Unit(pygame.sprite.Sprite):
    def __init__(self, x, y, player):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill((0, 255, 0) if player == client.player else (255, 0, 0))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.player = player
        self.health = 100
        self.attack_damage = 10
        self.attack_cooldown = 1000
        self.last_attack_time = pygame.time.get_ticks()
        self.speed = 5

    def update(self):
        self.check_attack()

    def check_attack(self):
        now = pygame.time.get_ticks()
        if now - self.last_attack_time >= self.attack_cooldown:
            enemies = [unit for unit in units if unit.player != self.player and self.rect.colliderect(unit.rect)]
            if enemies:
                target = enemies[0]
                target.health -= self.attack_damage
                self.last_attack_time = now
                if target.health <= 0:
                    target.kill()

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

units = pygame.sprite.Group()

player_resources = {1: 1000, 2: 1000}

def update():
    units.update()
    sync_game_state_with_network()

def render(screen):
    screen.fill((0, 0, 0))
    units.draw(screen)
    render_hud(screen)

def render_hud(screen):
    font = pygame.font.Font(None, 36)
    text = font.render(f"Player 1 Resources: {player_resources[1]}", True, (255, 255, 255))
    screen.blit(text, (10, 10))
    text = font.render(f"Player 2 Resources: {player_resources[2]}", True, (255, 255, 255))
    screen.blit(text, (10, 50))

def sync_game_state_with_network():
    units_list = [{'x': unit.rect.x, 'y': unit.rect.y, 'player': unit.player, 'health': unit.health} for unit in units]
    client.send_game_state(units_list)

    if client.game_state['units']:
        existing_units = {(unit.rect.x, unit.rect.y, unit.player): unit for unit in units}
        for unit_data in client.game_state['units']:
            key = (unit_data['x'], unit_data['y'], unit_data['player'])
            if key in existing_units:
                unit = existing_units[key]
                unit.health = unit_data['health']
            else:
                unit = Unit(unit_data['x'], unit_data['y'], unit_data['player'])
                unit.health = unit_data['health']
                units.add(unit)
