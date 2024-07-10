# map_generator.py
import pygame
import random
from noise import snoise2
import threading
import noise

TILE_SIZE = 32
MAP_WIDTH = 5000
MAP_HEIGHT = 5000
CHUNK_SIZE = 5


TERRAIN_TYPES = {
    'deep_water': (0, 0, 139),    # 深蓝
    'shallow_water': (65, 105, 225),  # 蓝色
    'beach': (238, 214, 175),      # 浅棕
    'grassland': (34, 139, 34),    # 绿色
    'forest': (0, 100, 0),         # 深绿
    'hills': (160, 82, 45),        # 赭石色
    'mountains': (139, 137, 137),  # 灰色
    'snow_peaks': (255, 250, 250)  # 雪白
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

class MapGenerator:
    def __init__(self):
        self.chunks = {}
        self.lock = threading.Lock()
        self.seed = random.randint(0, 1000)

    def get_chunk(self, chunk_x, chunk_y):
        chunk_key = (chunk_x, chunk_y)
        print(f"Requesting chunk: {chunk_key}")
        with self.lock:
            if chunk_key not in self.chunks:
                print(f"Generating new chunk: {chunk_key}")
                self.chunks[chunk_key] = self.generate_chunk(chunk_x, chunk_y)
            else:
                print(f"Returning existing chunk: {chunk_key}")
        return self.chunks[chunk_key]

    def generate_chunk(self, chunk_x, chunk_y):
        chunk = [[None for _ in range(CHUNK_SIZE)] for _ in range(CHUNK_SIZE)]
        
        base_x = chunk_x * CHUNK_SIZE
        base_y = chunk_y * CHUNK_SIZE
        
        for y in range(CHUNK_SIZE):
            for x in range(CHUNK_SIZE):
                world_x = base_x + x
                world_y = base_y + y
                
                # 使用多层噪声
                elevation = noise.snoise2(world_x / 100, world_y / 100, octaves=6, persistence=0.5, lacunarity=2.0, repeatx=1024, repeaty=1024, base=self.seed)
                moisture = noise.snoise2(world_x / 50, world_y / 50, octaves=4, persistence=0.6, lacunarity=2.0, repeatx=1024, repeaty=1024, base=self.seed + 1)
                
                # 根据高度和湿度确定地形
                if elevation < -0.3:
                    terrain = 'deep_water'
                elif elevation < -0.1:
                    terrain = 'shallow_water'
                elif elevation < 0:
                    terrain = 'beach'
                elif elevation < 0.3:
                    if moisture < 0:
                        terrain = 'grassland'
                    else:
                        terrain = 'forest'
                elif elevation < 0.6:
                    terrain = 'hills'
                elif elevation < 0.8:
                    terrain = 'mountains'
                else:
                    terrain = 'snow_peaks'
                
                chunk[y][x] = Tile(world_x, world_y, terrain)
        
        return chunk

    def get_visible_tiles(self, camera_x, camera_y, screen_width, screen_height):
        visible_tiles = []
        start_chunk_x = max(0, camera_x // (CHUNK_SIZE * TILE_SIZE))
        start_chunk_y = max(0, camera_y // (CHUNK_SIZE * TILE_SIZE))
        end_chunk_x = min(MAP_WIDTH // CHUNK_SIZE, (camera_x + screen_width) // (CHUNK_SIZE * TILE_SIZE) + 1)
        end_chunk_y = min(MAP_HEIGHT // CHUNK_SIZE, (camera_y + screen_height) // (CHUNK_SIZE * TILE_SIZE) + 1)

        for chunk_y in range(start_chunk_y, end_chunk_y):
            for chunk_x in range(start_chunk_x, end_chunk_x):
                chunk = self.get_chunk(chunk_x, chunk_y)
                for row in chunk:
                    for tile in row:
                        if (camera_x <= tile.x * TILE_SIZE < camera_x + screen_width and
                            camera_y <= tile.y * TILE_SIZE < camera_y + screen_height):
                            visible_tiles.append(tile)
        
        return visible_tiles

map_generator = MapGenerator()

def get_map():
    return map_generator