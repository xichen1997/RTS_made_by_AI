import subprocess
import time
import os
import signal

def start_server():
    return subprocess.Popen(['python', 'network/server.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def start_client(player_number):
    process = subprocess.Popen(['python', 'main.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(1)  # 确保客户端进程启动
    process.stdin.write(b'client\n')
    process.stdin.write(f'{player_number}\n'.encode())
    process.stdin.flush()
    return process

def main():
    # 启动服务器
    server_process = start_server()
    time.sleep(2)  # 确保服务器已启动

    # 启动第一个客户端
    client1_process = start_client(1)

    # 启动第二个客户端
    client2_process = start_client(2)

    try:
        # 等待服务器和客户端完成
        server_process.wait()
        client1_process.wait()
        client2_process.wait()
    except KeyboardInterrupt:
        # 在手动中断时，确保所有进程都被终止
        os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
        os.killpg(os.getpgid(client1_process.pid), signal.SIGTERM)
        os.killpg(os.getpgid(client2_process.pid), signal.SIGTERM)

if __name__ == "__main__":
    main()
