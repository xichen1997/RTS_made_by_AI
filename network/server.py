# network/server.py
import socket
import threading
import pickle

clients = []
game_state = {
    'units': []
}

def handle_client(client_socket):
    while True:
        try:
            message = client_socket.recv(4096)
            if not message:
                break
            data = pickle.loads(message)
            if data['type'] == 'state_update':
                game_state['units'] = data['units']
                broadcast_state()
        except:
            break

    client_socket.close()
    clients.remove(client_socket)

def broadcast_state():
    for client in clients:
        try:
            client.send(pickle.dumps({'type': 'state_update', 'units': game_state['units']}))
        except:
            clients.remove(client)

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 9999))
    server.listen(5)
    print("Server started")

    while True:
        client_socket, addr = server.accept()
        print(f"Connection from {addr}")
        clients.append(client_socket)
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()

if __name__ == "__main__":
    start_server()
