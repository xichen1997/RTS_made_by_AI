import pygame
from map_generator import MapGenerator, TILE_SIZE, MAP_WIDTH, MAP_HEIGHT, CHUNK_SIZE, TERRAIN_TYPES

# 常量定义
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
MINIMAP_SIZE = 200
EDGE_SCROLL_MARGIN = 20
SCROLL_SPEED = 5

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

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Isometric RTS")
        self.clock = pygame.time.Clock()
        self.map_generator = MapGenerator()
        self.camera_x = 0
        self.camera_y = 0
        self.dragging = False
        self.drag_start = None
        self.zoom = 1.0
        self.min_zoom = 0.5
        self.max_zoom = 2.0
        self.target_camera_x = 0
        self.target_camera_y = 0
        self.quadtree = QuadTreeNode(pygame.Rect(0, 0, MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE), 4)
        self.init_quadtree()

    def init_quadtree(self):
        for chunk_y in range(MAP_HEIGHT // CHUNK_SIZE):
            for chunk_x in range(MAP_WIDTH // CHUNK_SIZE):
                chunk = self.map_generator.get_chunk(chunk_x, chunk_y)
                chunk.rect = pygame.Rect(chunk_x * CHUNK_SIZE * TILE_SIZE, chunk_y * CHUNK_SIZE * TILE_SIZE,
                                         CHUNK_SIZE * TILE_SIZE, CHUNK_SIZE * TILE_SIZE)
                self.quadtree.insert(chunk)

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
            zoom_speed = 0.1
            self.zoom += event.y * zoom_speed
            self.zoom = max(min(self.zoom, self.max_zoom), self.min_zoom)

    def update(self):
        mouse_pos = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed()

        if mouse_pos[0] < EDGE_SCROLL_MARGIN:
            self.target_camera_x += SCROLL_SPEED
        elif mouse_pos[0] > SCREEN_WIDTH - EDGE_SCROLL_MARGIN:
            self.target_camera_x -= SCROLL_SPEED
        if mouse_pos[1] < EDGE_SCROLL_MARGIN:
            self.target_camera_y += SCROLL_SPEED
        elif mouse_pos[1] > SCREEN_HEIGHT - EDGE_SCROLL_MARGIN:
            self.target_camera_y -= SCROLL_SPEED

        if keys[pygame.K_LEFT]:
            self.target_camera_x += SCROLL_SPEED
        elif keys[pygame.K_RIGHT]:
            self.target_camera_x -= SCROLL_SPEED
        if keys[pygame.K_UP]:
            self.target_camera_y += SCROLL_SPEED
        elif keys[pygame.K_DOWN]:
            self.target_camera_y -= SCROLL_SPEED

        max_x = 0
        max_y = 0
        min_x = -(MAP_WIDTH * TILE_SIZE * self.zoom - SCREEN_WIDTH)
        min_y = -(MAP_HEIGHT * TILE_SIZE * self.zoom - SCREEN_HEIGHT)
        self.target_camera_x = max(min(self.target_camera_x, max_x), min_x)
        self.target_camera_y = max(min(self.target_camera_y, max_y), min_y)

        lerp_factor = 0.1
        self.camera_x += (self.target_camera_x - self.camera_x) * lerp_factor
        self.camera_y += (self.target_camera_y - self.camera_y) * lerp_factor

    def render(self):
        self.screen.fill((0, 0, 0))  # Clear the screen

        visible_rect = pygame.Rect(-self.camera_x / self.zoom, -self.camera_y / self.zoom,
                                   SCREEN_WIDTH / self.zoom, SCREEN_HEIGHT / self.zoom)
        visible_chunks = []
        self.quadtree.query(visible_rect, visible_chunks)

        for chunk in visible_chunks:
            chunk_surface = chunk.render()
            scaled_size = int(CHUNK_SIZE * TILE_SIZE * self.zoom)
            scaled_chunk = pygame.transform.scale(chunk_surface, (scaled_size, scaled_size))
            self.screen.blit(scaled_chunk, (
                int(chunk.rect.x * self.zoom + self.camera_x),
                int(chunk.rect.y * self.zoom + self.camera_y)
            ))

        self.render_minimap()

    def render_minimap(self):
        minimap_surface = pygame.Surface((MINIMAP_SIZE, MINIMAP_SIZE))
        minimap_surface.fill((50, 50, 50))
        minimap_tile_size = max(1, MINIMAP_SIZE / max(MAP_WIDTH, MAP_HEIGHT))

        for chunk_y in range(MAP_HEIGHT // CHUNK_SIZE):
            for chunk_x in range(MAP_WIDTH // CHUNK_SIZE):
                chunk = self.map_generator.get_chunk(chunk_x, chunk_y)
                for y in range(CHUNK_SIZE):
                    for x in range(CHUNK_SIZE):
                        tile = chunk.get_tile(x, y)
                        color = TERRAIN_TYPES[tile.type]
                        pygame.draw.rect(minimap_surface, color, (
                            int((chunk_x * CHUNK_SIZE + x) * minimap_tile_size),
                            int((chunk_y * CHUNK_SIZE + y) * minimap_tile_size),
                            max(1, int(minimap_tile_size)),
                            max(1, int(minimap_tile_size))
                        ))

        view_rect = pygame.Rect(
            int(-self.camera_x / (TILE_SIZE * self.zoom) * minimap_tile_size),
            int(-self.camera_y / (TILE_SIZE * self.zoom) * minimap_tile_size),
            max(1, int(SCREEN_WIDTH / (TILE_SIZE * self.zoom) * minimap_tile_size)),
            max(1, int(SCREEN_HEIGHT / (TILE_SIZE * self.zoom) * minimap_tile_size))
        )
        pygame.draw.rect(minimap_surface, (255, 0, 0), view_rect, 1)

        minimap_pos = (SCREEN_WIDTH - MINIMAP_SIZE - 10, 10)
        self.screen.blit(minimap_surface, minimap_pos)
        pygame.draw.rect(self.screen, (255, 255, 255), (*minimap_pos, MINIMAP_SIZE, MINIMAP_SIZE), 2)

def main():
    game = Game()
    game.run()
    pygame.quit()

if __name__ == "__main__":
    main()