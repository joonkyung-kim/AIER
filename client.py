import socket
import threading
import cv2
import struct
import numpy as np
from tkinter import Tk, Frame, Label, Button, Entry, StringVar, Text, DISABLED, NORMAL, END
from tkinter import messagebox
from PIL import Image, ImageTk
import time
import datetime


class TCPClient:
    def __init__(self, server_address, server_port):
        self.server_address = server_address
        self.server_port = server_port
        self.socket = None
        self.is_connected = False

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # Set timeout for connection
            self.socket.connect((self.server_address, self.server_port))
            self.is_connected = True
            print(f"Connected to server at {self.server_address}:{self.server_port}")
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            self.is_connected = False

    def send_data(self, data):
        if not self.is_connected:
            print("Not connected to the server.")
            return

        try:
            self.socket.sendall(data)
            print(f"Sent data: {data}")
        except Exception as e:
            print(f"Failed to send data: {e}")

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.is_connected = False
            print("Disconnected from the server.")

    # def receive_video_stream(self, display_callback):
    #     if not self.is_connected:
    #         print("Not connected to the server.")
    #         return

    #     try:
    #         while True:
    #             # Receive frame size
    #             packed_size = self.socket.recv(4)
    #             if not packed_size:
    #                 break
    #             frame_size = struct.unpack(">L", packed_size)[0]

    #             # Receive frame data
    #             frame_data = b""
    #             while len(frame_data) < frame_size:
    #                 chunk = self.socket.recv(frame_size - len(frame_data))
    #                 if not chunk:
    #                     print("Incomplete frame received.")
    #                     return
    #                 frame_data += chunk

    #             # Decode and display the frame
    #             frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
    #             if frame is not None:
    #                 display_callback(frame)
    #             else:
    #                 print("Failed to decode the frame.")
    #     except Exception as e:
    #         print(f"Error receiving video stream: {e}")

    def receive_video_stream(self, display_callback):
        if not self.is_connected:
            print("Not connected to the server.")
            return

        try:
            while True:
                # Receive frame size (4 bytes)
                packed_size = self.socket.recv(4)
                if not packed_size:
                    print("Connection closed by the server.")
                    break

                # Log the raw size header for debugging
                print(f"Raw size header: {packed_size.hex()}")

                try:
                    frame_size = struct.unpack(">L", packed_size)[0]
                    print(f"Expected frame size: {frame_size} bytes")
                except struct.error as e:
                    print(f"Failed to unpack frame size: {e}. Raw header: {packed_size.hex()}")
                    continue

                # Validate frame size
                if not (1024 <= frame_size <= 10 * 1024 * 1024):  # 1KB to 10MB
                    print(f"Invalid frame size received: {frame_size}. Attempting to resynchronize...")
                    # Consume extra data to resynchronize
                    self.socket.recv(1024)
                    continue

                # Receive frame data
                frame_data = b""
                while len(frame_data) < frame_size:
                    chunk = self.socket.recv(frame_size - len(frame_data))
                    if not chunk:
                        print("Connection lost or incomplete data received.")
                        return
                    frame_data += chunk

                # Verify received data length
                if len(frame_data) != frame_size:
                    print(f"Data size mismatch. Expected {frame_size}, received {len(frame_data)}.")
                    continue

                # Decode the frame
                try:
                    frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        print("Failed to decode the frame. Skipping.")
                        continue
                except Exception as e:
                    print(f"Error during frame decoding: {e}")
                    continue

                # Display the frame
                display_callback(frame)
        except Exception as e:
            print(f"Error receiving video stream: {e}")


class ClientControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Client Control Interface")

        self.client = None
        self.video_stream_thread = None
        self.is_streaming = False
        self.crosshair_position = [320, 240]
        self.last_frame_times = []
        self.video_writer = None

        self.server_address_var = StringVar(value="localhost")
        self.server_port_var = StringVar(value="5000")
        self.state_var = StringVar(value="SAFE")

        self.create_ui()

    def create_ui(self):
        frame = Frame(self.root)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        Label(frame, text="Server Address:").grid(row=0, column=0, sticky="e")
        Entry(frame, textvariable=self.server_address_var).grid(row=0, column=1)

        Label(frame, text="Server Port:").grid(row=0, column=2, sticky="e")
        Entry(frame, textvariable=self.server_port_var).grid(row=0, column=3)

        Button(frame, text="Connect", command=self.connect_to_server).grid(row=0, column=4)
        Button(frame, text="Disconnect", command=self.disconnect_from_server).grid(row=0, column=5)

        Label(frame, text="System State:").grid(row=1, column=0, sticky="e")
        Entry(frame, textvariable=self.state_var).grid(row=1, column=1)

        Button(frame, text="Send State", command=self.send_state).grid(row=1, column=2)

        self.video_label = Label(frame)
        self.video_label.grid(row=2, column=0, columnspan=6, pady=10)

        Button(frame, text="Start Video Stream", command=self.start_video_stream).grid(row=3, column=0)
        Button(frame, text="Stop Video Stream", command=self.stop_video_stream).grid(row=3, column=1)

    def connect_to_server(self):
        address = self.server_address_var.get()
        port = int(self.server_port_var.get())

        self.client = TCPClient(address, port)
        self.client.connect()

    def disconnect_from_server(self):
        if self.client:
            self.client.disconnect()
            self.client = None

    def send_state(self):
        if self.client and self.client.is_connected:
            state = self.state_var.get()
            self.client.send_data(f"STATE:{state}".encode())

    def start_video_stream(self):
        if self.client and self.client.is_connected:
            self.is_streaming = True
            self.video_stream_thread = threading.Thread(
                target=self.client.receive_video_stream, args=(self.update_video_frame,)
            )
            self.video_stream_thread.daemon = True
            self.video_stream_thread.start()

    def stop_video_stream(self):
        self.is_streaming = False
        if self.video_stream_thread and self.video_stream_thread.is_alive():
            self.client.disconnect()
            self.video_stream_thread.join(timeout=1)

    def update_video_frame(self, frame):
        if not self.is_streaming:
            return

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image)
        image_tk = ImageTk.PhotoImage(image)

        self.root.after(0, self.update_video_label, image_tk)

    def update_video_label(self, image_tk):
        self.video_label.config(image=image_tk)
        self.video_label.image = image_tk


if __name__ == "__main__":
    root = Tk()
    app = ClientControlApp(root)
    root.mainloop()
