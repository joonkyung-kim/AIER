import cv2
import socket
import struct

def run_video_stream_server(host="0.0.0.0", port=5000):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Server listening for video stream on {host}:{port}")

    conn, addr = server_socket.accept()
    print(f"Video stream connection established with {addr}")

    cap = cv2.VideoCapture(0)  # Use webcam for testing
    if not cap.isOpened():
        print("Failed to access the webcam.")
        conn.close()
        server_socket.close()
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Encode the frame as JPEG
            _, encoded_frame = cv2.imencode('.jpg', frame)

            # Send the frame size first
            conn.sendall(struct.pack(">L", len(encoded_frame)))

            # Send the frame data
            conn.sendall(encoded_frame)
    except Exception as e:
        print(f"Error during streaming: {e}")
    finally:
        cap.release()
        conn.close()
        server_socket.close()
        print("Video stream server shut down.")

if __name__ == "__main__":
    run_video_stream_server()
