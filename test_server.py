import socket

def run_test_server(host="0.0.0.0", port=5000):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Server listening on {host}:{port}")

    conn, addr = server_socket.accept()
    print(f"Connection established with {addr}")

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print(f"Received from client: {data}")
            # Echo the received data back to the client
            conn.sendall(data)
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        conn.close()
        server_socket.close()
        print("Server shut down.")

if __name__ == "__main__":
    run_test_server()
