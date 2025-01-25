import socket
import threading
import cv2
import struct
import numpy as np


class TCPClient:
    def __init__(self, server_address, server_port):
        self.server_address = server_address
        self.server_port = server_port
        self.socket = None
        self.is_connected = False

    def connect(self):
        """Establish a connection to the server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_address, self.server_port))
            self.is_connected = True
            print(f"Connected to server at {self.server_address}:{self.server_port}")
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            self.is_connected = False

    def send_data(self, data):
        """Send data to the server."""
        if not self.is_connected:
            print("Not connected to the server.")
            return

        try:
            self.socket.sendall(data)
            print(f"Sent data: {data}")
        except Exception as e:
            print(f"Failed to send data: {e}")

    def receive_data(self, buffer_size=1024):
        """Receive data from the server in blocking mode."""
        if not self.is_connected:
            print("Not connected to the server.")
            return None

        try:
            data = self.socket.recv(buffer_size)
            print(f"Received data: {data}")
            return data
        except Exception as e:
            print(f"Failed to receive data: {e}")
            return None

    def receive_data_non_blocking(self, buffer_size=1024):
        """Receive data from the server in non-blocking mode."""
        if not self.is_connected:
            print("Not connected to the server.")
            return None

        try:
            self.socket.setblocking(False)
            data = self.socket.recv(buffer_size)
            print(f"Received data (non-blocking): {data}")
            return data
        except socket.error as e:
            # No data received in non-blocking mode
            return None
        except Exception as e:
            print(f"Failed to receive data: {e}")
            return None

    def disconnect(self):
        """Close the connection to the server."""
        if self.socket:
            self.socket.close()
            self.is_connected = False
            print("Disconnected from the server.")

    def receive_video_stream(self, display_callback):
        """Receive video frames and call the display callback."""
        if not self.is_connected:
            print("Not connected to the server.")
            return

        try:
            while True:
                # Receive frame size
                packed_size = self.socket.recv(4)
                if not packed_size:
                    break
                frame_size = struct.unpack(">L", packed_size)[0]

                # Receive frame data
                frame_data = b""
                while len(frame_data) < frame_size:
                    frame_data += self.socket.recv(frame_size - len(frame_data))

                # Decode and display the frame
                frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    display_callback(frame)
        except Exception as e:
            print(f"Error receiving video stream: {e}")


# Example Usage
if __name__ == "__main__":
    # Replace with actual server address and port
    client = TCPClient("raspberrypi.local", 5000)

    # Connect to the server
    client.connect()

    # Send a sample message
    client.send_data(b"Hello, server!")

    # Receive a response
    response = client.receive_data()

    # Disconnect
    client.disconnect()
