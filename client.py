import socket
import threading
import os

HOST = "127.0.0.1"  # Must match server
PORT = 8888

def start_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    # Start background listener
    thread = threading.Thread(target=receive_messages, args=(sock,))
    thread.daemon = True
    thread.start()

    while True:
        msg = input()
        if msg.lower() == "/quit":
            break
        sock.send(msg.encode())

    sock.close()

def receive_messages(sock):
    while True:
        try:
            msg = sock.recv(1024).decode()
            if msg:
                print(msg)
            else:
                break
        except:
            print("[ERROR] Lost connection to server.")
            sock.close()
            break

if __name__ == "__main__":
    start_client()
