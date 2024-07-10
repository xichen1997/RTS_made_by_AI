# game.py
import pygame
from map_generator import get_map, TILE_SIZE, MAP_WIDTH, MAP_HEIGHT, CHUNK_SIZE, TERRAIN_TYPES
# 常量定义
TILE_WIDTH = 64
TILE_HEIGHT = 32
MAP_WIDTH = 50
MAP_HEIGHT = 50
# 更新SCREEN_WIDTH和SCREEN_HEIGHT以适应更大的地图
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600


MINIMAP_SIZE = 200

EDGE_SCROLL_MARGIN = 20
SCROLL_SPEED = 5

# 颜色定义
COLORS = {
    0: (0, 0, 255),    # 深蓝 - 水
    1: (0, 128, 255),  # 浅蓝 - 浅水
    2: (0, 255, 0),    # 绿色 - 平原
    3: (0, 200, 0),    # 深绿 - 小丘
    4: (150, 75, 0),   # 棕色 - 山丘
    5: (100, 100, 100) # 灰色 - 高山
}

class IsometricTile(pygame.sprite.Sprite):
    def __init__(self, x, y, height):
        super().__init__()
        self.x = x
        self.y = y
        self.height = height
        self.color = COLORS[height]
        self.image = self.create_tile_image()
        self.rect = self.image.get_rect()
        self.rect.x = (x - y) * TILE_WIDTH // 2
        self.rect.y = (x + y) * TILE_HEIGHT // 2 - height * 8

    def create_tile_image(self):
        image = pygame.Surface((TILE_WIDTH, TILE_HEIGHT + 16), pygame.SRCALPHA)
        points = [
            (TILE_WIDTH // 2, 0),
            (TILE_WIDTH, TILE_HEIGHT // 2),
            (TILE_WIDTH // 2, TILE_HEIGHT),
            (0, TILE_HEIGHT // 2)
        ]
        pygame.draw.polygon(image, self.color, points)
        pygame.draw.polygon(image, (min(self.color[0] + 50, 255), min(self.color[1] + 50, 255), min(self.color[2] + 50, 255)), 
                            [(points[0][0], points[0][1]), 
                             (points[1][0], points[1][1]), 
                             (points[1][0], points[1][1] + 16), 
                             (points[0][0], points[0][1] + 16)])
        pygame.draw.polygon(image, (max(self.color[0] - 50, 0), max(self.color[1] - 50, 0), max(self.color[2] - 50, 0)), 
                            [(points[1][0], points[1][1]), 
                             (points[2][0], points[2][1]), 
                             (points[2][0], points[2][1] + 16), 
                             (points[1][0], points[1][1] + 16)])
        return image

def generate_height_map():
    height_map = [[0 for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
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
            height_map[y][x] = int((elevation + 1) * 2.5)  # 将值映射到0-5范围
    return height_map

class Unit(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.image = pygame.Surface((20, 20))
        self.image.fill((255, 0, 0))  # 红色表示单位
        self.rect = self.image.get_rect()
        self.update_position()

    def update_position(self):
        self.rect.x = (self.x - self.y) * TILE_WIDTH // 2 + TILE_WIDTH // 2 - 10
        self.rect.y = (self.x + self.y) * TILE_HEIGHT // 2 - 10

    def move(self, dx, dy, height_map):
        new_x = self.x + dx
        new_y = self.y + dy
        if 0 <= new_x < MAP_WIDTH and 0 <= new_y < MAP_HEIGHT:
            height_diff = abs(height_map[new_y][new_x] - height_map[self.y][self.x])
            if height_diff <= 1:  # 允许最多1级的高度差
                self.x = new_x
                self.y = new_y
                self.update_position()


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Isometric RTS")
        self.clock = pygame.time.Clock()
        self.map = get_map()
        self.camera_x = 0
        self.camera_y = 0
        self.dragging = False
        self.drag_start = None
        self.zoom = 1.0
        self.min_zoom = 0.5
        self.max_zoom = 2.0
        self.target_camera_x = 0
        self.target_camera_y = 0

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self.handle_input(event)
                print(f"Camera position: ({self.camera_x}, {self.camera_y})")
                print(f"Zoom level: {self.zoom}")

            self.update()
            self.render()
            pygame.display.flip()
            self.clock.tick(60)

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 2:  # 鼠标中键
                self.dragging = True
                self.last_mouse_pos = pygame.mouse.get_pos()
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:  # 鼠标中键
                self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                current_mouse_pos = pygame.mouse.get_pos()
                dx = current_mouse_pos[0] - self.last_mouse_pos[0]
                dy = current_mouse_pos[1] - self.last_mouse_pos[1]
                self.target_camera_x += dx
                self.target_camera_y += dy
                self.last_mouse_pos = current_mouse_pos
        elif event.type == pygame.MOUSEWHEEL:
            # 缩放功能
            zoom_speed = 0.1
            self.zoom += event.y * zoom_speed
            self.zoom = max(min(self.zoom, self.max_zoom), self.min_zoom)

    def update(self):
        mouse_pos = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed()

        # 更新目标相机位置
        if mouse_pos[0] < EDGE_SCROLL_MARGIN:
            self.target_camera_x += SCROLL_SPEED
        elif mouse_pos[0] > SCREEN_WIDTH - EDGE_SCROLL_MARGIN:
            self.target_camera_x -= SCROLL_SPEED
        if mouse_pos[1] < EDGE_SCROLL_MARGIN:
            self.target_camera_y += SCROLL_SPEED
        elif mouse_pos[1] > SCREEN_HEIGHT - EDGE_SCROLL_MARGIN:
            self.target_camera_y -= SCROLL_SPEED

        # 键盘滚动
        if keys[pygame.K_LEFT]:
            self.target_camera_x += SCROLL_SPEED
        elif keys[pygame.K_RIGHT]:
            self.target_camera_x -= SCROLL_SPEED
        if keys[pygame.K_UP]:
            self.target_camera_y += SCROLL_SPEED
        elif keys[pygame.K_DOWN]:
            self.target_camera_y -= SCROLL_SPEED

        # 限制相机移动
        max_x = 0
        max_y = 0
        min_x = -(MAP_WIDTH * TILE_SIZE * self.zoom - SCREEN_WIDTH)
        min_y = -(MAP_HEIGHT * TILE_SIZE * self.zoom - SCREEN_HEIGHT)
        self.target_camera_x = max(min(self.target_camera_x, max_x), min_x)
        self.target_camera_y = max(min(self.target_camera_y, max_y), min_y)

        # 平滑过渡
        lerp_factor = 0.1
        self.camera_x += (self.target_camera_x - self.camera_x) * lerp_factor
        self.camera_y += (self.target_camera_y - self.camera_y) * lerp_factor

    def render(self):
        self.screen.fill((0, 0, 0))  # Clear the screen
        self.minimap_surface = pygame.Surface((MINIMAP_SIZE, MINIMAP_SIZE))

        # 计算缩放后的瓦片大小
        scaled_tile_size = int(TILE_SIZE * self.zoom)

        # 计算可见区域
        visible_tiles = self.map.get_visible_tiles(
            int(-self.camera_x / self.zoom), 
            int(-self.camera_y / self.zoom), 
            int(SCREEN_WIDTH / self.zoom), 
            int(SCREEN_HEIGHT / self.zoom)
        )

        for tile in visible_tiles:
            scaled_image = pygame.transform.scale(tile.image, (scaled_tile_size, scaled_tile_size))
            self.screen.blit(scaled_image, (
                int(tile.x * scaled_tile_size + self.camera_x),
                int(tile.y * scaled_tile_size + self.camera_y)
            ))

        self.render_minimap()

    def render_minimap(self):
        print("Rendering minimap...")
        self.minimap_surface = pygame.Surface((MINIMAP_SIZE, MINIMAP_SIZE))
        self.minimap_surface.fill((50, 50, 50))  # 深灰色背景
        minimap_tile_size = max(1, MINIMAP_SIZE / max(MAP_WIDTH, MAP_HEIGHT))

        print(f"Minimap tile size: {minimap_tile_size}")
        print(f"MAP_WIDTH: {MAP_WIDTH}, MAP_HEIGHT: {MAP_HEIGHT}, CHUNK_SIZE: {CHUNK_SIZE}")
        colors_used = set()

        chunks_x = max(1, MAP_WIDTH // CHUNK_SIZE)
        chunks_y = max(1, MAP_HEIGHT // CHUNK_SIZE)
        print(f"Chunks to render: {chunks_x} x {chunks_y}")

        for chunk_y in range(chunks_y):
            for chunk_x in range(chunks_x):
                chunk = self.map.get_chunk(chunk_x, chunk_y)
                for y in range(CHUNK_SIZE):
                    for x in range(CHUNK_SIZE):
                        tile = chunk[y][x]
                        base_color = TERRAIN_TYPES[tile.type]
                        
                        # 添加高度渐变
                        elevation = (tile.x + tile.y) / (MAP_WIDTH + MAP_HEIGHT)  # 简化的高度计算
                        color = tuple(max(0, min(255, c + int(elevation * 50))) for c in base_color)
                        
                        pygame.draw.rect(self.minimap_surface, color, (
                            int((chunk_x * CHUNK_SIZE + x) * minimap_tile_size),
                            int((chunk_y * CHUNK_SIZE + y) * minimap_tile_size),
                            max(1, int(minimap_tile_size)),
                            max(1, int(minimap_tile_size))
                        ))

        print(f"Colors used in minimap: {colors_used}")
        print(f"Total chunks rendered: {chunks_x * chunks_y}")

        # 绘制当前视图区域
        view_rect = pygame.Rect(
            int(-self.camera_x / (TILE_SIZE * self.zoom) * minimap_tile_size),
            int(-self.camera_y / (TILE_SIZE * self.zoom) * minimap_tile_size),
            max(1, int(SCREEN_WIDTH / (TILE_SIZE * self.zoom) * minimap_tile_size)),
            max(1, int(SCREEN_HEIGHT / (TILE_SIZE * self.zoom) * minimap_tile_size))
        )
        pygame.draw.rect(self.minimap_surface, (255, 0, 0), view_rect, 1)

        # 将小地图绘制到主屏幕
        minimap_pos = (SCREEN_WIDTH - MINIMAP_SIZE - 10, 10)
        self.screen.blit(self.minimap_surface, minimap_pos)

        # 添加边框以使小地图更容易看见
        pygame.draw.rect(self.screen, (255, 255, 255), (*minimap_pos, MINIMAP_SIZE, MINIMAP_SIZE), 2)

        print(f"Minimap drawn at position: {minimap_pos}, size: {MINIMAP_SIZE}x{MINIMAP_SIZE}")

def main():
    print(f"MAP_WIDTH: {MAP_WIDTH}")
    print(f"MAP_HEIGHT: {MAP_HEIGHT}")
    print(f"CHUNK_SIZE: {CHUNK_SIZE}")
    pygame.init()
    game = Game()
    game.run()
    pygame.quit()

if __name__ == "__main__":
    main()