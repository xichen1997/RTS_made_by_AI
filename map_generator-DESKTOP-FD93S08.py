# map_generator.py
import pygame
import random
from noise import snoise2

TILE_SIZE = 32
MAP_WIDTH = 100
MAP_HEIGHT = 75

WATER_LEVEL = 0.3
LAND_LEVEL = 0.5
PLATEAU_LEVEL = 0.7

class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, tile_type):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        if tile_type == 'water':
            self.image.fill((0, 0, 255))  # 蓝色代表水
        elif tile_type == 'land':
            self.image.fill((0, 255, 0))  # 绿色代表平地
        elif tile_type == 'plateau':
            self.image.fill((139, 69, 19))  # 棕色代表高原
        self.rect = self.image.get_rect(topleft=(x * TILE_SIZE, y * TILE_SIZE))
        self.type = tile_type

def generate_map():
    tiles = pygame.sprite.Group()
    
    # 使用Perlin噪声生成高度图
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

# 生成并返回地图
map_tiles = generate_map()