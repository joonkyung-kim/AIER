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

        # Add a BooleanVar for "calibrate" if you need keyboard calibration
        self.calibrate_var = tk.BooleanVar(value=False)

        # Create the main frames
        self.create_main_frames()

        # Bind keys (if you want robot control via keyboard)
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)

    def create_main_frames(self):
        """
        Create two main frames, side by side:
          - left_frame  for server controls, video, crosshair, etc.
          - right_frame for the log.
        """
        # This main_frame will contain left_frame and right_frame side by side
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # Left side frame
        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side="left", fill="y", padx=5, pady=5)

        # Right side frame (for the log)
        self.right_frame = tk.Frame(self.main_frame)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        # Now build the left_frame's layout with grid
        self.create_left_side_ui()

        # Create the log in the right_frame
        self.create_log_ui()

    def create_left_side_ui(self):
        """
        Build the controls (connection, video, crosshair, etc.) in left_frame using grid.
        """
        # Row 0: Server connection
        row_idx = 0
        tk.Label(self.left_frame, text="Server Address:").grid(row=row_idx, column=0, padx=5, pady=2, sticky="e")
        self.server_address_entry = tk.Entry(self.left_frame, width=15)
        self.server_address_entry.insert(0, "localhost")
        self.server_address_entry.grid(row=row_idx, column=1, padx=5, pady=2)

        tk.Label(self.left_frame, text="Server Port:").grid(row=row_idx, column=2, padx=5, pady=2, sticky="e")
        self.server_port_entry = tk.Entry(self.left_frame, width=10)
        self.server_port_entry.insert(0, "5000")
        self.server_port_entry.grid(row=row_idx, column=3, padx=5, pady=2)

        self.connect_button = tk.Button(self.left_frame, text="Connect", command=self.connect_to_server)
        self.connect_button.grid(row=row_idx, column=4, padx=5, pady=2)

        self.disconnect_button = tk.Button(
            self.left_frame, text="Disconnect", command=self.disconnect_from_server, state=tk.DISABLED
        )
        self.disconnect_button.grid(row=row_idx, column=5, padx=5, pady=2)

        # Row 1: System state
        row_idx += 1
        tk.Label(self.left_frame, text="System State:").grid(row=row_idx, column=0, padx=5, pady=2, sticky="e")
        self.state_var = tk.StringVar(value="SAFE")
        self.state_dropdown = tk.OptionMenu(self.left_frame, self.state_var, "SAFE", "ARMED", "ENGAGED")
        self.state_dropdown.grid(row=row_idx, column=1, padx=5, pady=2)

        self.send_state_button = tk.Button(self.left_frame, text="Send State", command=self.send_state)
        self.send_state_button.grid(row=row_idx, column=2, padx=5, pady=2)

        # Row 1 (continued): Command
        tk.Label(self.left_frame, text="Command:").grid(row=row_idx, column=3, padx=5, pady=2, sticky="e")
        self.command_entry = tk.Entry(self.left_frame, width=20)
        self.command_entry.grid(row=row_idx, column=4, padx=5, pady=2)

        self.send_command_button = tk.Button(self.left_frame, text="Send Command", command=self.send_command)
        self.send_command_button.grid(row=row_idx, column=5, padx=5, pady=2)

        # Row 2: Video label + FPS
        row_idx += 1
        tk.Label(self.left_frame, text="Video Stream:").grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
        self.fps_label = tk.Label(self.left_frame, text="FPS: 0", font=("Arial", 10))
        self.fps_label.grid(row=row_idx, column=5, padx=5, pady=2, sticky="e")

        # Row 3: The actual video feed
        row_idx += 1
        self.video_label = tk.Label(self.left_frame)
        self.video_label.grid(row=row_idx, column=0, columnspan=6, padx=5, pady=5)

        # Row 4: Video buttons + calibrate
        row_idx += 1
        self.start_video_button = tk.Button(self.left_frame, text="Start Video Stream", command=self.start_video_stream)
        self.start_video_button.grid(row=row_idx, column=0, padx=5, pady=2)

        self.stop_video_button = tk.Button(
            self.left_frame, text="Stop Video Stream", command=self.stop_video_stream, state=tk.DISABLED
        )
        self.stop_video_button.grid(row=row_idx, column=1, padx=5, pady=2)

        self.save_video_button = tk.Button(self.left_frame, text="Start Saving Video", command=self.start_saving_video)
        self.save_video_button.grid(row=row_idx, column=2, padx=5, pady=2)

        self.stop_saving_button = tk.Button(
            self.left_frame, text="Stop Saving Video", command=self.stop_saving_video, state=tk.DISABLED
        )
        self.stop_saving_button.grid(row=row_idx, column=3, padx=5, pady=2)

        calibrate_check = tk.Checkbutton(self.left_frame, text="Calibrate", variable=self.calibrate_var)
        calibrate_check.grid(row=row_idx, column=4, padx=5, pady=2)

        # Row 5: Crosshair Controls
        row_idx += 1
        tk.Label(self.left_frame, text="Crosshair Controls:").grid(row=row_idx, column=0, padx=5, pady=5, sticky="w")

        # Next row for crosshair buttons
        row_idx += 1
        tk.Button(self.left_frame, text="Up", command=lambda: self.move_crosshair(0, -10)).grid(
            row=row_idx, column=1, pady=2
        )
        tk.Button(self.left_frame, text="Left", command=lambda: self.move_crosshair(-10, 0)).grid(
            row=row_idx, column=0, pady=2
        )
        tk.Button(self.left_frame, text="Right", command=lambda: self.move_crosshair(10, 0)).grid(
            row=row_idx, column=2, pady=2
        )
        tk.Button(self.left_frame, text="Down", command=lambda: self.move_crosshair(0, 10)).grid(
            row=row_idx, column=3, pady=2
        )
        tk.Button(self.left_frame, text="Reset", command=self.reset_crosshair).grid(row=row_idx, column=4, pady=2)

    def create_log_ui(self):
        """
        Put the Log label and Text widget in right_frame.
        """
        log_label = tk.Label(self.right_frame, text="Log:")
        log_label.pack(anchor="nw", padx=5, pady=(0, 5))

        self.log_text = tk.Text(self.right_frame, width=50, height=30, state=tk.DISABLED)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    # --------------------------------------------------------------------------
    # Networking/Commands
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # Video Handling
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # Video Recording
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # Crosshair
    # --------------------------------------------------------------------------
    def reset_crosshair(self):
        self.crosshair_position = [320, 240]  # Reset to the center
        self.log("Reset crosshair to center.")

    def move_crosshair(self, dx, dy):
        if self.crosshair_position:
            self.crosshair_position[0] += dx
            self.crosshair_position[1] += dy
            self.log(f"Moved crosshair to: {self.crosshair_position}")

    # --------------------------------------------------------------------------
    # Keyboard Handlers (Optional)
    # --------------------------------------------------------------------------
    def on_key_press(self, event):
        """
        Example: If you want to replicate the turret/motion control:
        (Assumes the server recognizes these commands.)
        """
        if not self.client or not self.client.is_connected:
            return

        key = event.keysym.lower()
        calibrate_mode = self.calibrate_var.get()

        send_code = None
        if calibrate_mode:
            if key == "j":
                send_code = "CALIB_DEC_X"
            elif key == "l":
                send_code = "CALIB_INC_X"
            elif key == "i":
                send_code = "CALIB_INC_Y"
            elif key == "m":
                send_code = "CALIB_DEC_Y"
        else:
            if key == "j":
                send_code = "PAN_LEFT_START"
            elif key == "l":
                send_code = "PAN_RIGHT_START"
            elif key == "i":
                send_code = "PAN_UP_START"
            elif key == "m":
                send_code = "PAN_DOWN_START"
            elif key == "f":
                send_code = "FIRE_START"

        if send_code:
            self.client.send_data(send_code.encode())
            self.log(f"Key Pressed: {key} => {send_code}")

    def on_key_release(self, event):
        if not self.client or not self.client.is_connected:
            return

        # In calibrate mode, no STOP commands are sent (mirroring C++ logic).
        if self.calibrate_var.get():
            return

        key = event.keysym.lower()
        send_code = None
        if key == "j":
            send_code = "PAN_LEFT_STOP"
        elif key == "l":
            send_code = "PAN_RIGHT_STOP"
        elif key == "i":
            send_code = "PAN_UP_STOP"
        elif key == "m":
            send_code = "PAN_DOWN_STOP"
        elif key == "f":
            send_code = "FIRE_STOP"

        if send_code:
            self.client.send_data(send_code.encode())
            self.log(f"Key Released: {key} => {send_code}")

    # --------------------------------------------------------------------------
    # Logging helper
    # --------------------------------------------------------------------------
    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = ClientControlApp(root)
    root.mainloop()
