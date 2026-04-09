# this is the client code
import socket
import os

# Remote server address and port used when sending files
SERVER_IP = input("Enter server IP: ")
SERVER_PORT = 5005
# Local port used to receive incoming file transfers from the server
CLIENT_PORT = 5006
# Maximum size of each data chunk sent over UDP
CHUNK_SIZE = 1024

# Separate sockets for send and receive to avoid port reuse conflicts
send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receive_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receive_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
receive_sock.bind(("0.0.0.0", CLIENT_PORT))


def send_file(filename):
    """Send a file to the configured server.

    The client uses a separate send socket for outgoing packets, and it
    waits for the server READY response before streaming numbered chunks.
    """
    if not os.path.exists(filename):
        print("File not found")
        return

    size = os.path.getsize(filename)
    send_sock.sendto(f"SEND {filename} {size}".encode(), (SERVER_IP, SERVER_PORT))

    send_sock.settimeout(10)
    try:
        data, _ = send_sock.recvfrom(1024)
        if data != b"READY":
            print("Server not ready")
            return
    except socket.timeout:
        print("No READY from server")
        return

    with open(filename, "rb") as f:
        seq = 0
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break

            packet = seq.to_bytes(4, "big") + chunk

            while True:
                send_sock.sendto(packet, (SERVER_IP, SERVER_PORT))
                try:
                    send_sock.settimeout(1)
                    ack, _ = send_sock.recvfrom(1024)
                    if ack.startswith(b"ACK") and int(ack.decode().split()[1]) == seq:
                        seq += 1
                        break
                except socket.timeout:
                    print("Resending", seq)

    send_sock.sendto(b"END", (SERVER_IP, SERVER_PORT))
    send_sock.settimeout(None)
    print("File sent")


def receive_file():
    """Receive a file sent by the server.

    This function listens on CLIENT_PORT and replies READY before accepting
    sequence-numbered chunks, acknowledging each valid packet.
    """
    print("Waiting for file...")

    data, addr = receive_sock.recvfrom(65536)

    if not data.startswith(b"SEND"):
        print("Invalid request")
        return

    _, fname, size = data.decode().split()
    print(f"Receiving {fname}...")

    print(f"Received handshake from {addr}, sending READY")
    receive_sock.sendto(b"READY", addr)

    with open("download_" + fname, "wb") as f:
        expected_seq = 0
        while True:
            data, sender = receive_sock.recvfrom(65536)

            if data == b"END":
                break

            seq = int.from_bytes(data[:4], "big")
            chunk = data[4:]

            if seq == expected_seq:
                f.write(chunk)
                receive_sock.sendto(f"ACK {seq}".encode(), sender)
                expected_seq += 1
            else:
                last_ack = expected_seq - 1 if expected_seq > 0 else 0
                receive_sock.sendto(f"ACK {last_ack}".encode(), sender)

    print("File received:", fname)


while True:
    print("\n1. Send File\n2. Receive File\n3. Exit")
    choice = input("Choose: ")

    if choice == "1":
        fname = input("Enter filename: ")
        send_file(fname)

    elif choice == "2":
        receive_file()

    elif choice == "3":
        # Close both sockets cleanly before exiting
        send_sock.close()
        receive_sock.close()
        break