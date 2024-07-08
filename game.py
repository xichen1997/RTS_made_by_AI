# game.py
import pygame
import random
from noise import snoise2

# 假设这些导入是正确的，如果不是，你可能需要调整
from network import client

# 地图设置
TILE_SIZE = 32
MAP_WIDTH = 50
MAP_HEIGHT = 40

WATER_LEVEL = 0.3
LAND_LEVEL = 0.5
PLATEAU_LEVEL = 0.7

# 颜色定义
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
BROWN = (139, 69, 19)
RED = (255, 0, 0)
WHITE = (255, 255, 255)

class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, tile_type):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        if tile_type == 'water':
            self.image.fill(BLUE)
        elif tile_type == 'land':
            self.image.fill(GREEN)
        elif tile_type == 'plateau':
            self.image.fill(BROWN)
        self.rect = self.image.get_rect(topleft=(x * TILE_SIZE, y * TILE_SIZE))
        self.type = tile_type

class Unit(pygame.sprite.Sprite):
    def __init__(self, x, y, player):
        super().__init__()
        self.image = pygame.Surface((20, 20))
        self.image.fill(RED if player == 1 else BLUE)
        self.rect = self.image.get_rect(center=(x, y))
        self.player = player
        self.health = 100
        self.attack_damage = 10
        self.attack_cooldown = 1000
        self.last_attack_time = pygame.time.get_ticks()
        self.speed = 2

    def update(self, map_tiles):
        self.check_attack()
        self.move_on_terrain(map_tiles)

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

    def move_on_terrain(self, map_tiles):
        terrain = pygame.sprite.spritecollide(self, map_tiles, False)[0]
        if terrain.type == 'water':
            self.speed = 1
        elif terrain.type == 'land':
            self.speed = 2
        elif terrain.type == 'plateau':
            self.speed = 3

    def move(self, dx, dy):
        self.rect.x += dx * self.speed
        self.rect.y += dy * self.speed

def generate_map():
    tiles = pygame.sprite.Group()
    scale = 10.0
    octaves = 6
    persistence = 0.5
    lacunarity = 2.0
    seed = random.randint(0, 100)
    
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            nx = x / MAP_WIDTH - 0.5
            ny = y / MAP_HEIGHT - 0.5
            elevation = snoise2(nx * scale + seed, 
                                ny * scale + seed, 
                                octaves=octaves, 
                                persistence=persistence, 
                                lacunarity=lacunarity)
            
            if elevation < WATER_LEVEL:
                tile_type = 'water'
            elif elevation < LAND_LEVEL:
                tile_type = 'land'
            else:
                tile_type = 'plateau'
            
            tile = Tile(x, y, tile_type)
            tiles.add(tile)
    
    return tiles

units = pygame.sprite.Group()
map_tiles = generate_map()

player_resources = {1: 1000, 2: 1000}

def update():
    units.update(map_tiles)
    sync_game_state_with_network()

def render(screen):
    map_tiles.draw(screen)
    units.draw(screen)
    render_hud(screen)

def render_hud(screen):
    font = pygame.font.Font(None, 36)
    text = font.render(f"Player 1 Resources: {player_resources[1]}", True, WHITE)
    screen.blit(text, (10, 10))
    text = font.render(f"Player 2 Resources: {player_resources[2]}", True, WHITE)
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

def spawn_unit(player):
    x, y = random.randint(100, 700), random.randint(100, 500)
    unit = Unit(x, y, player)
    units.add(unit)
    return unit

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("RTS Game")
    clock = pygame.time.Clock()

    camera_x, camera_y = 0, 0
    selected_unit = None

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    if client.player == 1 and player_resources[1] >= 100:
                        player_resources[1] -= 100
                        selected_unit = spawn_unit(client.player)
                    elif client.player == 2 and player_resources[2] >= 100:
                        player_resources[2] -= 100
                        selected_unit = spawn_unit(client.player)
                elif event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                    if selected_unit:
                        if event.key == pygame.K_UP:
                            selected_unit.move(0, -1)
                        elif event.key == pygame.K_DOWN:
                            selected_unit.move(0, 1)
                        elif event.key == pygame.K_LEFT:
                            selected_unit.move(-1, 0)
                        elif event.key == pygame.K_RIGHT:
                            selected_unit.move(1, 0)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            camera_x = max(camera_x - 5, 0)
        if keys[pygame.K_d]:
            camera_x = min(camera_x + 5, MAP_WIDTH * TILE_SIZE - 800)
        if keys[pygame.K_w]:
            camera_y = max(camera_y - 5, 0)
        if keys[pygame.K_s]:
            camera_y = min(camera_y + 5, MAP_HEIGHT * TILE_SIZE - 600)

        update()

        screen.fill((0, 0, 0))

        for sprite in map_tiles:
            sprite.rect.x = sprite.rect.x - camera_x
            sprite.rect.y = sprite.rect.y - camera_y
        for unit in units:
            unit.rect.x = unit.rect.x - camera_x
            unit.rect.y = unit.rect.y - camera_y

        render(screen)

        for sprite in map_tiles:
            sprite.rect.x = sprite.rect.x + camera_x
            sprite.rect.y = sprite.rect.y + camera_y
        for unit in units:
            unit.rect.x = unit.rect.x + camera_x
            unit.rect.y = unit.rect.y + camera_y

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()