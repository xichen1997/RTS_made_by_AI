# map_generator.py
import pygame
import random
from noise import snoise2
import threading
import noise

TILE_SIZE = 32
MAP_WIDTH = 10000
MAP_HEIGHT = 10000
CHUNK_SIZE = 40


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

# 定义四叉树节点
class QuadTreeNode:
    def __init__(self, boundary, capacity):
        self.boundary = boundary  # 边界矩形
        self.capacity = capacity  # 节点容量
        self.tiles = []  # 存储瓦片
        self.divided = False  # 是否已分割
        self.northwest = None  # 西北子节点
        self.northeast = None  # 东北子节点
        self.southwest = None  # 西南子节点
        self.southeast = None  # 东南子节点

    def insert(self, tile):
        # 如果瓦片不在边界内,则不插入
        if  not self.boundary.colliderect(tile.rect):
            return False

        # 如果节点未达到容量且未分割,则直接插入
        if len(self.tiles) < self.capacity and not self.divided:
            self.tiles.append(tile)
            return True

        # 如果节点未分割,则进行分割
        if not self.divided:
            self.subdivide()

        # 尝试将瓦片插入到子节点
        if self.northwest.insert(tile): return True
        if self.northeast.insert(tile): return True
        if self.southwest.insert(tile): return True
        if self.southeast.insert(tile): return True

        # 如果都插入失败,返回False(理论上不应该发生)
        return False

    def subdivide(self):
        # 分割当前节点为四个子节点
        x, y, w, h = self.boundary
        half_w, half_h = w // 2, h // 2
        self.northwest = QuadTreeNode(pygame.Rect(x, y, half_w, half_h), self.capacity)
        self.northeast = QuadTreeNode(pygame.Rect(x + half_w, y, w - half_w, half_h), self.capacity)
        self.southwest = QuadTreeNode(pygame.Rect(x, y + half_h, half_w, h - half_h), self.capacity)
        self.southeast = QuadTreeNode(pygame.Rect(x + half_w, y + half_h, w - half_w, h - half_h), self.capacity)
        self.divided = True
        # 将现有的瓦片重新分配到子节点
        # for tile in self.tiles:
        #     self.insert(tile)
        # self.tiles = []
        # self.divided = True

    def query(self, range_rect, found_tiles):
        # 如果查询范围与当前节点边界不相交,则返回
        if not self.boundary.colliderect(range_rect):
            return

        # 检查当前节点中的瓦片
        for tile in self.tiles:
            if range_rect.colliderect(tile.rect):
                found_tiles.append(tile)

        # 如果已分割,则递归查询子节点
        if self.divided:
            self.northwest.query(range_rect, found_tiles)
            self.northeast.query(range_rect, found_tiles)
            self.southwest.query(range_rect, found_tiles)
            self.southeast.query(range_rect, found_tiles)



# 四叉树类
class QuadTree:
    def __init__(self, boundary, capacity):
        self.root = QuadTreeNode(boundary, capacity)

    def insert(self, tile):
        return self.root.insert(tile)

    def query(self, range_rect):
        found_tiles = []
        self.root.query(range_rect, found_tiles)
        return found_tiles



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
        self.quadtree = QuadTree(pygame.Rect(0, 0, MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE), 4)
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
                tile = Tile(world_x, world_y, terrain)
                chunk[y][x] = tile
                self.quadtree.insert(tile)
        
        return chunk

    def get_visible_tiles(self, camera_x, camera_y, screen_width, screen_height):
        visible_rect = pygame.Rect(camera_x, camera_y, screen_width, screen_height)        
        return self.quadtree.query(visible_rect)

map_generator = MapGenerator()

def get_map():
    return map_generator