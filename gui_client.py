import socket
import threading
import tkinter as tk
from tkinter import scrolledtext

HOST = "127.0.0.1"  # Must match server
PORT = 8888

class ChatClient:
    def __init__(self, host, port):
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        # --- GUI setup ---
        self.root = tk.Tk()
        self.root.title("Chatroom GUI")

        self.chat_area = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, state="disabled", width=50, height=20
        )
        self.chat_area.pack(padx=10, pady=10)

        self.entry = tk.Entry(self.root, width=40)
        self.entry.pack(side=tk.LEFT, padx=(10, 0), pady=(0, 10))
        self.entry.bind("<Return>", self.send_message)

        self.send_button = tk.Button(self.root, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=(5, 10), pady=(0, 10))

        # Start background thread for receiving messages
        thread = threading.Thread(target=self.receive_messages, daemon=True)
        thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        thread = threading.Thread(target=self.receive_messages, daemon=True)
        thread.start()
        self.root.mainloop()

    def send_message(self, event=None):
        msg = self.entry.get()
        if msg:
            if msg.lower() == "/quit":
                self.on_close()
                return
            try:
                self.sock.send(msg.encode())
            except:
                self.append_message("[ERROR] Could not send message.")
            self.entry.delete(0, tk.END)

    def receive_messages(self):
        while self.running:
            try:
                msg = self.sock.recv(1024).decode()
                if not msg:
                    break
                self.append_message(msg)
            except:
                self.append_message("[ERROR] Lost connection to server.")
                break

    def append_message(self, message):
        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.yview(tk.END)
        self.chat_area.config(state="disabled")

    def on_close(self):
        self.running = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except:
            pass
        self.root.destroy()


if __name__ == "__main__":
    ChatClient(HOST, PORT)