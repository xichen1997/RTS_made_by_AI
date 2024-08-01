import pygame
import random
import noise

# 常量定义
TILE_SIZE = 32
MAP_WIDTH = 256
MAP_HEIGHT = 256
CHUNK_SIZE = 16  # 每个chunk包含16x16个瓦片

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

class Tile:
    def __init__(self, x, y, terrain_type):
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.type = terrain_type
        self.image = self.create_tile_image()

    def create_tile_image(self):
        image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        image.fill(TERRAIN_TYPES[self.type])
        return image

class Chunk:
    def __init__(self, chunk_x, chunk_y):
        self.x = chunk_x
        self.y = chunk_y
        self.rect = pygame.Rect(chunk_x * CHUNK_SIZE * TILE_SIZE, chunk_y * CHUNK_SIZE * TILE_SIZE,
                                CHUNK_SIZE * TILE_SIZE, CHUNK_SIZE * TILE_SIZE)
        self.tiles = [[None for _ in range(CHUNK_SIZE)] for _ in range(CHUNK_SIZE)]
        self.surface = None

    def get_tile(self, x, y):
        return self.tiles[y][x]

    def set_tile(self, x, y, tile):
        self.tiles[y][x] = tile
        self.surface = None  # Reset surface so it will be re-rendered

    def render(self):
        if self.surface is None:
            self.surface = pygame.Surface((CHUNK_SIZE * TILE_SIZE, CHUNK_SIZE * TILE_SIZE))
            for y in range(CHUNK_SIZE):
                for x in range(CHUNK_SIZE):
                    tile = self.tiles[y][x]
                    self.surface.blit(tile.image, (x * TILE_SIZE, y * TILE_SIZE))
        return self.surface

class QuadTreeNode:
    def __init__(self, boundary, capacity):
        self.boundary = boundary
        self.capacity = capacity
        self.chunks = []
        self.divided = False
        self.northwest = None
        self.northeast = None
        self.southwest = None
        self.southeast = None

    def insert(self, chunk):
        if not self.boundary.colliderect(chunk.rect):
            return False

        if len(self.chunks) < self.capacity:
            self.chunks.append(chunk)
            return True

        if not self.divided:
            self.subdivide()

        return (self.northwest.insert(chunk) or
                self.northeast.insert(chunk) or
                self.southwest.insert(chunk) or
                self.southeast.insert(chunk))

    def subdivide(self):
        x, y, w, h = self.boundary
        half_w, half_h = w // 2, h // 2

        self.northwest = QuadTreeNode(pygame.Rect(x, y, half_w, half_h), self.capacity)
        self.northeast = QuadTreeNode(pygame.Rect(x + half_w, y, w - half_w, half_h), self.capacity)
        self.southwest = QuadTreeNode(pygame.Rect(x, y + half_h, half_w, h - half_h), self.capacity)
        self.southeast = QuadTreeNode(pygame.Rect(x + half_w, y + half_h, w - half_w, h - half_h), self.capacity)

        self.divided = True

    def query(self, range_rect, found_chunks):
        if not self.boundary.colliderect(range_rect):
            return

        for chunk in self.chunks:
            if range_rect.colliderect(chunk.rect):
                found_chunks.append(chunk)

        if self.divided:
            self.northwest.query(range_rect, found_chunks)
            self.northeast.query(range_rect, found_chunks)
            self.southwest.query(range_rect, found_chunks)
            self.southeast.query(range_rect, found_chunks)

class MapGenerator:
    def __init__(self):
        self.seed = random.randint(0, 1000)
        self.quadtree = QuadTreeNode(pygame.Rect(0, 0, MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE), 4)
        self.chunks = {}

    def get_chunk(self, chunk_x, chunk_y):
        chunk_key = (chunk_x, chunk_y)
        if chunk_key not in self.chunks:
            new_chunk = self.generate_chunk(chunk_x, chunk_y)
            self.chunks[chunk_key] = new_chunk
            self.quadtree.insert(new_chunk)
        return self.chunks[chunk_key]

    def generate_chunk(self, chunk_x, chunk_y):
        chunk = Chunk(chunk_x, chunk_y)
        for y in range(CHUNK_SIZE):
            for x in range(CHUNK_SIZE):
                world_x = chunk_x * CHUNK_SIZE + x
                world_y = chunk_y * CHUNK_SIZE + y
                elevation = self.get_elevation(world_x, world_y)
                moisture = self.get_moisture(world_x, world_y)
                terrain_type = self.get_terrain_type(elevation, moisture)
                tile = Tile(world_x, world_y, terrain_type)
                chunk.set_tile(x, y, tile)
        return chunk

    def get_elevation(self, x, y):
        octaves = 6
        persistence = 0.5
        lacunarity = 2.0
        return noise.pnoise2(x/MAP_WIDTH, y/MAP_HEIGHT, 
                             octaves=octaves, 
                             persistence=persistence, 
                             lacunarity=lacunarity, 
                             repeatx=1024, 
                             repeaty=1024, 
                             base=self.seed)

    def get_moisture(self, x, y):
        octaves = 4
        persistence = 0.6
        lacunarity = 2.0
        return noise.pnoise2(x/MAP_WIDTH, y/MAP_HEIGHT, 
                             octaves=octaves, 
                             persistence=persistence, 
                             lacunarity=lacunarity, 
                             repeatx=1024, 
                             repeaty=1024, 
                             base=self.seed + 1)

    def get_terrain_type(self, elevation, moisture):
        if elevation < -0.3:
            return 'deep_water'
        elif elevation < -0.1:
            return 'shallow_water'
        elif elevation < 0:
            return 'beach'
        elif elevation < 0.3:
            if moisture < 0:
                return 'grassland'
            else:
                return 'forest'
        elif elevation < 0.6:
            return 'hills'
        elif elevation < 0.8:
            return 'mountains'
        else:
            return 'snow_peaks'

    def get_visible_chunks(self, view_rect):
        visible_chunks = []
        self.quadtree.query(view_rect, visible_chunks)
        return visible_chunks

    def get_tile(self, x, y):
        chunk_x, chunk_y = x // CHUNK_SIZE, y // CHUNK_SIZE
        local_x, local_y = x % CHUNK_SIZE, y % CHUNK_SIZE
        chunk = self.get_chunk(chunk_x, chunk_y)
        return chunk.get_tile(local_x, local_y)