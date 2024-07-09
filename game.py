# game.py
import pygame
from map_generator import get_map, TILE_SIZE, MAP_WIDTH, MAP_HEIGHT

# 常量定义
TILE_WIDTH = 64
TILE_HEIGHT = 32
MAP_WIDTH = 50
MAP_HEIGHT = 50
# 更新SCREEN_WIDTH和SCREEN_HEIGHT以适应更大的地图
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600


MINIMAP_SIZE = 150

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

            self.update()
            self.render()
            pygame.display.flip()
            self.clock.tick(60)

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 2:  # Middle mouse button
                self.dragging = True
                self.drag_start = event.pos
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:  # Middle mouse button
                self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                dx = event.pos[0] - self.drag_start[0]
                dy = event.pos[1] - self.drag_start[1]
                self.camera_x += dx
                self.camera_y += dy
                self.drag_start = event.pos
        if event.type == pygame.MOUSEWHEEL:
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
        start_x = max(0, int(-self.camera_x / scaled_tile_size))
        end_x = min(MAP_WIDTH, int((-self.camera_x + SCREEN_WIDTH) / scaled_tile_size) + 1)
        start_y = max(0, int(-self.camera_y / scaled_tile_size))
        end_y = min(MAP_HEIGHT, int((-self.camera_y + SCREEN_HEIGHT) / scaled_tile_size) + 1)

        # 只渲染可见的瓦片
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = self.map[y][x]
                scaled_image = pygame.transform.scale(tile.image, (scaled_tile_size, scaled_tile_size))
                self.screen.blit(scaled_image, (
                    x * scaled_tile_size + self.camera_x,
                    y * scaled_tile_size + self.camera_y
                ))
        self.render_minimap()


    def render_minimap(self):
        self.minimap_surface.fill((0, 0, 0))
        minimap_tile_size = MINIMAP_SIZE / max(MAP_WIDTH, MAP_HEIGHT)

        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                tile = self.map[y][x]
                color = tile.image.get_at((0, 0))  # 获取瓦片的颜色
                pygame.draw.rect(self.minimap_surface, color, (
                    x * minimap_tile_size,
                    y * minimap_tile_size,
                    minimap_tile_size,
                    minimap_tile_size
                ))

        # 绘制当前视图区域
        view_rect = pygame.Rect(
            -self.camera_x / (TILE_SIZE * self.zoom) * minimap_tile_size,
            -self.camera_y / (TILE_SIZE * self.zoom) * minimap_tile_size,
            SCREEN_WIDTH / (TILE_SIZE * self.zoom) * minimap_tile_size,
            SCREEN_HEIGHT / (TILE_SIZE * self.zoom) * minimap_tile_size
        )
        pygame.draw.rect(self.minimap_surface, (255, 0, 0), view_rect, 1)

        # 将小地图绘制到主屏幕
        self.screen.blit(self.minimap_surface, (SCREEN_WIDTH - MINIMAP_SIZE - 10, 10))
def main():
    pygame.init()
    game = Game()
    game.run()
    pygame.quit()

if __name__ == "__main__":
    main()