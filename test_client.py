from networking_module import TCPClient  # Adjust the import path if needed

if __name__ == "__main__":
    # Replace 'localhost' with the server's IP address if they are on different machines
    client = TCPClient("localhost", 5000)

    # Connect to the test server
    client.connect()

    # Send a test message
    client.send_data(b"Test message from client!")

    # Receive and print the echoed response
    response = client.receive_data()
    if response:
        print(f"Response from server: {response}")

    # Disconnect from the server
    client.disconnect()
