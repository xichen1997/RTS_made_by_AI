# main.py
import pygame
import game
import threading
from network import server, client
import random

selected_unit = None

def start_network(role):
    if role == "server":
        server_thread = threading.Thread(target=server.start_server)
        server_thread.start()
    elif role == "client":
        client_thread = threading.Thread(target=client.start_client)
        client_thread.start()

def spawn_unit(player):
    x, y = random.randint(100, 700), random.randint(100, 500)
    unit = game.Unit(x, y, player)
    game.units.add(unit)
    return unit

def main():
    global selected_unit

    role = input("Enter role (server/client): ")
    start_network(role)
    
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Simplified RTS Game")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    if client.player == 1 and game.player_resources[1] >= 100:
                        game.player_resources[1] -= 100
                        selected_unit = spawn_unit(client.player)
                    elif client.player == 2 and game.player_resources[2] >= 100:
                        game.player_resources[2] -= 100
                        selected_unit = spawn_unit(client.player)
                elif event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                    if selected_unit:
                        if event.key == pygame.K_UP:
                            selected_unit.move(0, -selected_unit.speed)
                        elif event.key == pygame.K_DOWN:
                            selected_unit.move(0, selected_unit.speed)
                        elif event.key == pygame.K_LEFT:
                            selected_unit.move(-selected_unit.speed, 0)
                        elif event.key == pygame.K_RIGHT:
                            selected_unit.move(selected_unit.speed, 0)

        game.update()
        game.render(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
