import threading
from PIL import Image, ImageTk
import numpy as np
import cv2
import tkinter as tk
from tkinter import messagebox
from networking_module import TCPClient
import time
import datetime


class ClientControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Client Control Interface")

        # Networking client
        self.client = None

        # Video stream and saving
        self.video_stream_thread = None
        self.is_streaming = False
        self.video_writer = None
        self.crosshair_position = None
        self.last_frame_times = []  # For stable FPS calculation
        self.fps_label = None

        # UI Elements
        self.create_ui()

    def create_ui(self):
        # Server connection controls
        tk.Label(self.root, text="Server Address:").grid(row=0, column=0, padx=5, pady=5)
        self.server_address_entry = tk.Entry(self.root, width=15)
        self.server_address_entry.insert(0, "localhost")
        self.server_address_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self.root, text="Server Port:").grid(row=0, column=2, padx=5, pady=5)
        self.server_port_entry = tk.Entry(self.root, width=10)
        self.server_port_entry.insert(0, "5000")
        self.server_port_entry.grid(row=0, column=3, padx=5, pady=5)

        self.connect_button = tk.Button(self.root, text="Connect", command=self.connect_to_server)
        self.connect_button.grid(row=0, column=4, padx=5, pady=5)

        self.disconnect_button = tk.Button(
            self.root, text="Disconnect", command=self.disconnect_from_server, state=tk.DISABLED
        )
        self.disconnect_button.grid(row=0, column=5, padx=5, pady=5)

        # System state controls
        tk.Label(self.root, text="System State:").grid(row=1, column=0, padx=5, pady=5)
        self.state_var = tk.StringVar(value="SAFE")
        self.state_dropdown = tk.OptionMenu(self.root, self.state_var, "SAFE", "ARMED", "ENGAGED")
        self.state_dropdown.grid(row=1, column=1, padx=5, pady=5)

        self.send_state_button = tk.Button(self.root, text="Send State", command=self.send_state)
        self.send_state_button.grid(row=1, column=2, padx=5, pady=5)

        # Command controls
        tk.Label(self.root, text="Command:").grid(row=1, column=3, padx=5, pady=5)
        self.command_entry = tk.Entry(self.root, width=30)
        self.command_entry.grid(row=1, column=4, padx=5, pady=5)

        self.send_command_button = tk.Button(self.root, text="Send Command", command=self.send_command)
        self.send_command_button.grid(row=1, column=5, padx=5, pady=5)

        # Video display area
        tk.Label(self.root, text="Video Stream:").grid(row=2, column=0, padx=5, pady=5)
        self.video_label = tk.Label(self.root)
        self.video_label.grid(row=3, column=0, columnspan=6, padx=5, pady=5)

        # FPS Display
        self.fps_label = tk.Label(self.root, text="FPS: 0", font=("Arial", 12))
        self.fps_label.grid(row=2, column=5, padx=5, pady=5, sticky="e")

        # Video stream controls
        self.start_video_button = tk.Button(self.root, text="Start Video Stream", command=self.start_video_stream)
        self.start_video_button.grid(row=4, column=0, padx=5, pady=5)

        self.stop_video_button = tk.Button(
            self.root, text="Stop Video Stream", command=self.stop_video_stream, state=tk.DISABLED
        )
        self.stop_video_button.grid(row=4, column=1, padx=5, pady=5)

        self.save_video_button = tk.Button(self.root, text="Start Saving Video", command=self.start_saving_video)
        self.save_video_button.grid(row=4, column=2, padx=5, pady=5)

        self.stop_saving_button = tk.Button(
            self.root, text="Stop Saving Video", command=self.stop_saving_video, state=tk.DISABLED
        )
        self.stop_saving_button.grid(row=4, column=3, padx=5, pady=5)

        # Crosshair controls
        tk.Label(self.root, text="Crosshair Controls:").grid(row=5, column=0, padx=5, pady=5)
        tk.Button(self.root, text="Up", command=lambda: self.move_crosshair(0, -10)).grid(
            row=5, column=2, padx=5, pady=5
        )
        tk.Button(self.root, text="Left", command=lambda: self.move_crosshair(-10, 0)).grid(
            row=6, column=1, padx=5, pady=5
        )
        tk.Button(self.root, text="Reset", command=self.reset_crosshair).grid(row=6, column=2, padx=5, pady=5)
        tk.Button(self.root, text="Right", command=lambda: self.move_crosshair(10, 0)).grid(
            row=6, column=3, padx=5, pady=5
        )
        tk.Button(self.root, text="Down", command=lambda: self.move_crosshair(0, 10)).grid(
            row=7, column=2, padx=5, pady=5
        )

        # Log display
        tk.Label(self.root, text="Log:").grid(row=8, column=0, padx=5, pady=5)
        self.log_text = tk.Text(self.root, width=85, height=10, state=tk.DISABLED)
        self.log_text.grid(row=9, column=0, columnspan=6, padx=5, pady=5)

    def connect_to_server(self):
        server_address = self.server_address_entry.get()
        server_port = int(self.server_port_entry.get())

        try:
            self.client = TCPClient(server_address, server_port)
            self.client.connect()
            self.log(f"Connected to server at {server_address}:{server_port}")

            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to server: {e}")

    def disconnect_from_server(self):
        if self.client:
            self.client.disconnect()
            self.log("Disconnected from the server.")

        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)

    def send_state(self):
        if not self.client or not self.client.is_connected:
            messagebox.showerror("Error", "Not connected to the server.")
            return

        state = self.state_var.get()
        self.client.send_data(f"STATE:{state}".encode())
        self.log(f"Sent system state: {state}")

    def send_command(self):
        if not self.client or not self.client.is_connected:
            messagebox.showerror("Error", "Not connected to the server.")
            return

        command = self.command_entry.get()
        if not command:
            messagebox.showwarning("Warning", "Command cannot be empty.")
            return

        self.client.send_data(command.encode())
        self.log(f"Sent command: {command}")

    def start_video_stream(self):
        if not self.client or not self.client.is_connected:
            messagebox.showerror("Error", "Not connected to the server.")
            return

        self.stop_video_button.config(state=tk.NORMAL)
        self.start_video_button.config(state=tk.DISABLED)

        # Initialize crosshair position
        self.crosshair_position = [320, 240]  # Center of a 640x480 frame
        self.last_frame_times = []  # Clear FPS tracking

        # Start the video stream in a separate thread
        self.is_streaming = True
        self.video_stream_thread = threading.Thread(
            target=self.client.receive_video_stream, args=(self.update_video_frame,)
        )
        self.video_stream_thread.daemon = True
        self.video_stream_thread.start()

    def stop_video_stream(self):
        self.stop_video_button.config(state=tk.DISABLED)
        self.start_video_button.config(state=tk.NORMAL)
        self.is_streaming = False

        if self.video_stream_thread and self.video_stream_thread.is_alive():
            self.video_stream_thread.join(timeout=1)

    def update_video_frame(self, frame):
        if not self.is_streaming:
            return

        # Calculate stable FPS using a sliding window of frame times
        current_time = time.time()
        self.last_frame_times.append(current_time)
        if len(self.last_frame_times) > 30:  # Keep the last 30 frame times
            self.last_frame_times.pop(0)

        if len(self.last_frame_times) > 1:
            fps = len(self.last_frame_times) / (self.last_frame_times[-1] - self.last_frame_times[0])
            self.fps_label.config(text=f"FPS: {fps:.2f}")

        # Draw crosshair on the frame
        if self.crosshair_position:
            x, y = self.crosshair_position
            cv2.line(frame, (x - 20, y), (x + 20, y), (0, 0, 255), 2)
            cv2.line(frame, (x, y - 20), (x, y + 20), (0, 0, 255), 2)

        # Convert the OpenCV frame to a format compatible with Tkinter
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image)
        image_tk = ImageTk.PhotoImage(image)

        # Update the video label
        self.video_label.config(image=image_tk)
        self.video_label.image = image_tk

        # Save the frame if video saving is active
        if self.video_writer:
            self.video_writer.write(frame)

    def start_saving_video(self):
        if self.video_writer is None:
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            filename = datetime.datetime.now().strftime("video_%Y%m%d_%H%M%S.avi")
            self.video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
            self.log(f"Started saving video to {filename}.")
            self.save_video_button.config(state=tk.DISABLED)
            self.stop_saving_button.config(state=tk.NORMAL)

    def stop_saving_video(self):
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            self.log("Stopped saving video.")
            self.save_video_button.config(state=tk.NORMAL)
            self.stop_saving_button.config(state=tk.DISABLED)

    def reset_crosshair(self):
        self.crosshair_position = [320, 240]  # Reset to the center
        self.log("Reset crosshair to center.")

    def move_crosshair(self, dx, dy):
        if self.crosshair_position:
            self.crosshair_position[0] += dx
            self.crosshair_position[1] += dy
            self.log(f"Moved crosshair to: {self.crosshair_position}")

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = ClientControlApp(root)
    root.mainloop()
