# map_generator.py
import pygame
import random
from noise import snoise2

TILE_SIZE = 32
MAP_WIDTH = 200
MAP_HEIGHT = 200

# 定义不同的地形类型
TERRAIN_TYPES = {
    'deep_water': (0, 0, 139),    # 深蓝
    'shallow_water': (0, 191, 255),  # 浅蓝
    'sand': (238, 214, 175),      # 浅棕
    'grass': (34, 139, 34),       # 绿色
    'forest': (0, 100, 0),        # 深绿
    'mountain': (139, 137, 137)   # 灰色
}

class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, terrain_type):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(TERRAIN_TYPES[terrain_type])
        self.rect = self.image.get_rect(topleft=(x * TILE_SIZE, y * TILE_SIZE))
        self.type = terrain_type
        self.x = x
        self.y = y

def generate_map():
    tiles = [[None for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
    
    # 使用Perlin噪声生成高度图
    scale = 50.0
    octaves = 6
    persistence = 0.5
    lacunarity = 2.0
    seed = random.randint(0, 1000)
    
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            nx = x / MAP_WIDTH - 0.5
            ny = y / MAP_HEIGHT - 0.5
            elevation = snoise2(nx * scale + seed, 
                                ny * scale + seed, 
                                octaves=octaves, 
                                persistence=persistence, 
                                lacunarity=lacunarity)
            
            # 根据海拔高度确定地形类型
            if elevation < -0.2:
                terrain_type = 'deep_water'
            elif elevation < 0:
                terrain_type = 'shallow_water'
            elif elevation < 0.1:
                terrain_type = 'sand'
            elif elevation < 0.3:
                terrain_type = 'grass'
            elif elevation < 0.6:
                terrain_type = 'forest'
            else:
                terrain_type = 'mountain'
            
            tiles[y][x] = Tile(x, y, terrain_type)
    
    return tiles

# 生成并返回地图
def get_map():
    return generate_map()