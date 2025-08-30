#TO DO:
#   GUI using tkinter
#   delete messages (probably not, as I just don't want that)
#   add server accounts to be signed into

import socket
import threading
import sqlite3
import time
from threading import Lock
import os
import signal

HOST = "127.0.0.1" #local host
PORT = 8888 #chosen port number

# maps client socket -> username
usernames = {}
#list of immediate connections
clients = []

usernames_lock = Lock()  # protect access for multi-threadding
db_lock = Lock()
clients_lock = Lock()


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[LISTENING] Server is running on {HOST}:{PORT}")

    while True:
        client_socket, addr = server.accept()
        with clients_lock:
            clients.append(client_socket)
        thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        thread.start()


#default thread func for each user
def handle_client(client_socket, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    
    # Ask for username
    while True:
        client_socket.send("Enter a username: ".encode())
        username = client_socket.recv(1024).decode().strip()
        if not username:
            continue
        
        # check uniqueness
        with usernames_lock:
            if username not in usernames.values():
                client_socket.send("[SERVER] Username accepted.\n".encode())
                usernames[client_socket] = username
                break
            else:
                client_socket.send("[SERVER] Username already taken, try another.\n".encode())
    
    # Send last 24h messages
    recent_messages = get_recent_messages()
    for u_name, message, timestamp in recent_messages:
        try:
            client_socket.send(f"[{timestamp}] {u_name}: {message}\n".encode())
        except:
            pass
    
    # MAIN RECEIVE LOOP (handler for new messages)
    try:
        while True:
            #client_socket.send("Type your messages below:".encode())
            msg = client_socket.recv(1024)
            if not msg:
                break
            decoded_msg = msg.decode().strip()
            print(f"[{usernames[client_socket]}] {decoded_msg}")
            save_message(usernames[client_socket], decoded_msg)
            broadcast(f"{usernames[client_socket]}: {decoded_msg}", client_socket)
    except (ConnectionResetError, OSError):
        pass  # client disconnected abruptly
    finally:
        with clients_lock:
            if client_socket in clients:
                clients.remove(client_socket)
        with usernames_lock:
            if client_socket in usernames:
                del usernames[client_socket]
        client_socket.close()
        print(f"[DISCONNECT] {addr} disconnected.")


# send message to every connection, including the sender
def broadcast(message, client_socket):
    to_remove = []
    with clients_lock:
        for client in clients:
            try:
                client.send(message.encode())
            except Exception:
                # mark client for removal if sending fails
                to_remove.append(client)

        # remove any clients that failed
        for client in to_remove:
            if client in clients:
                clients.remove(client)



def server_commands():
    while True:
        cmd = input()
        if cmd.strip() == "/clear":
            clear_history()
        elif cmd.strip() == "/shutdown":
            print("[SERVER] Shutting down.")
            os.kill(os.getpid(), signal.SIGINT)  # kill entire process



#define the table if it doesn't exist
def init_db():
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def get_recent_messages():
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    
    c.execute("""
        SELECT username, message, timestamp
        FROM messages
        WHERE timestamp >= datetime('now', '-1 day')
        ORDER BY timestamp ASC
    """)
    
    rows = c.fetchall()  # fetch all results
    conn.close()
    return rows

#save message sent from each user to teh database
def save_message(username, message):
    with db_lock:
        conn = sqlite3.connect("chat.db")
        c = conn.cursor()
        c.execute("INSERT INTO messages (username, message) VALUES (?, ?)", (username, message))
        conn.commit()
        conn.close()


#delete messages after 24H of being sent originally
def cleanup_messages():
    while True:
        with db_lock:
            conn = sqlite3.connect("chat.db")
            c = conn.cursor()
            c.execute("DELETE FROM messages WHERE timestamp <= datetime('now', '-1 day')")
            conn.commit()
            conn.close()
        time.sleep(60)  # check once a minute


def clear_history():
    with db_lock:
        conn = sqlite3.connect("chat.db")
        c = conn.cursor()
        c.execute("DELETE FROM messages")
        conn.commit()
        conn.close()
        print("[SERVER] Chat history cleared.")










if __name__ == "__main__":
    print("[STARTING] Server is starting...")
    print(f"[DATABASE] M-Server creating/pulling database")
    init_db()  # ensure DB and table exist before any operations

    # start cleanup thread as daemon
    threading.Thread(target=cleanup_messages, daemon=True).start()
    # start server commands listener in a separate daemon thread
    threading.Thread(target=server_commands, daemon=True).start()

    # start the main server loop
    try:
        start_server()
    except KeyboardInterrupt:
        print("[SERVER] Shutdown signal received, exiting...")
