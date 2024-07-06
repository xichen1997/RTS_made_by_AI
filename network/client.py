# network/client.py
import socket
import threading
import pickle

server_socket = None
game_state = {
    'units': []
}
player = None

def handle_server():
    global game_state
    while True:
        try:
            message = server_socket.recv(4096)
            if not message:
                break
            data = pickle.loads(message)
            if data['type'] == 'state_update':
                game_state['units'] = data['units']
        except:
            break

def start_client():
    global server_socket, player
    player = int(input("Enter your player number (1 or 2): "))
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect(("127.0.0.1", 9999))
    
    server_thread = threading.Thread(target=handle_server)
    server_thread.start()

def send_game_state(units):
    if server_socket:
        state = {'type': 'state_update', 'units': units}
        server_socket.send(pickle.dumps(state))
