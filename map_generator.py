# map_generator.py
import pygame
import random
from noise import snoise2
import threading

TILE_SIZE = 32
MAP_WIDTH = 2500
MAP_HEIGHT = 2500
CHUNK_SIZE = 50


TERRAIN_TYPES = {
    'deep_water': (0, 0, 139),
    'shallow_water': (0, 191, 255),
    'sand': (238, 214, 175),
    'grass': (34, 139, 34),
    'forest': (0, 100, 0),
    'mountain': (139, 137, 137)
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
        scale = 50.0
        octaves = 6
        persistence = 0.5
        lacunarity = 2.0
        
        for y in range(CHUNK_SIZE):
            for x in range(CHUNK_SIZE):
                world_x = chunk_x * CHUNK_SIZE + x
                world_y = chunk_y * CHUNK_SIZE + y
                nx = world_x / MAP_WIDTH - 0.5
                ny = world_y / MAP_HEIGHT - 0.5
                elevation = snoise2(nx * scale + self.seed, 
                                    ny * scale + self.seed, 
                                    octaves=octaves, 
                                    persistence=persistence, 
                                    lacunarity=lacunarity)
                
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
                
                chunk[y][x] = Tile(world_x, world_y, terrain_type)
        
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