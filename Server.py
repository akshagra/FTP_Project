import os
import queue
import socket
import threading
from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256

KEY = b'0123456789abcdef'

PORT = 5005
CHUNK_SIZE = 1024
MAX_RETRIES = 5
RETRY_TIMEOUT = 2
RECEIVE_DIR = "received"

recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
recv_sock.bind(("0.0.0.0", PORT))

sessions = {}
sessions_lock = threading.Lock()

os.makedirs(RECEIVE_DIR, exist_ok=True)


def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal attacks."""
    return os.path.basename(filename)


def parse_send_request(data):
    """Parse SEND request packet and return filename and size if valid."""
    try:
        parts = data.decode().split(maxsplit=2)
        if len(parts) != 3 or parts[0] != "SEND":
            return None
        filename = sanitize_filename(parts[1])
        size = int(parts[2])
        return filename, size
    except (ValueError, UnicodeDecodeError):
        return None


def parse_ack(data):
    """Parse ACK packet and return sequence number if valid."""
    try:
        parts = data.decode().split()
        if len(parts) != 2 or parts[0] != "ACK":
            return None
        return int(parts[1])
    except (ValueError, UnicodeDecodeError, IndexError):
        return None


def send_file(addr, filename):
    """Send a file to a remote client address over UDP.

    The protocol is:
    1. Send SEND filename size and wait for READY.
    2. Send each chunk with a sequence number.
    3. Wait for ACK for each chunk before sending the next.
    4. Send END when complete.
    """
    if not os.path.exists(filename):
        print("File not found")
        return

    size = os.path.getsize(filename)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_sock:
        send_sock.settimeout(RETRY_TIMEOUT)

        for attempt in range(MAX_RETRIES):
            send_sock.sendto(f"SEND {sanitize_filename(filename)} {size}".encode(), addr)
            try:
                resp, _ = send_sock.recvfrom(1024)
                if resp == b"READY":
                    print("Client is ready")
                    break
            except socket.timeout:
                print("Retrying SEND...")
        else:
            print("Client not responding")
            return

        with open(filename, "rb") as f:
            seq = 0
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break

                cipher = AES.new(KEY, AES.MODE_CTR, nonce=seq.to_bytes(16, 'big'))
                encrypted = cipher.encrypt(chunk)
                hmac_obj = HMAC.new(KEY, digestmod=SHA256)
                hmac_obj.update(encrypted)
                hmac = hmac_obj.digest()
                packet = seq.to_bytes(4, "big") + encrypted + hmac
                for attempt in range(MAX_RETRIES):
                    send_sock.sendto(packet, addr)
                    try:
                        ack_data, _ = send_sock.recvfrom(1024)
                        ack_seq = parse_ack(ack_data)
                        if ack_seq == seq:
                            seq += 1
                            break
                    except socket.timeout:
                        print("Resending", seq)
                else:
                    print("Transfer failed at chunk", seq)
                    return

        send_sock.sendto(b"END", addr)
        print("File sent")


class ReceiveSession(threading.Thread):
    """Thread for handling a single file receive session."""

    def __init__(self, addr, filename, expected_size):
        super().__init__(daemon=True)
        self.addr = addr
        self.filename = sanitize_filename(filename)
        self.expected_size = expected_size
        self.queue = queue.Queue()

    def run(self):
        """Run the receive session, processing packets from the queue."""
        print(f"Incoming file request from {self.addr}: {self.filename}")
        recv_sock.sendto(b"READY", self.addr)

        output_path = os.path.join(RECEIVE_DIR, self.filename)
        expected_seq = 0
        last_ack = 0

        try:
            with open(output_path, "wb") as out_file:
                while True:
                    data = self.queue.get()
                    if data == b"END":
                        break

                    if len(data) < 4:
                        continue

                    seq = int.from_bytes(data[:4], "big")
                    encrypted = data[4:-32]
                    hmac_received = data[-32:]
                    hmac_obj = HMAC.new(KEY, digestmod=SHA256)
                    hmac_obj.update(encrypted)
                    if hmac_obj.digest() != hmac_received:
                        print("HMAC mismatch, ignoring packet")
                        continue
                    cipher = AES.new(KEY, AES.MODE_CTR, nonce=seq.to_bytes(16, 'big'))
                    chunk = cipher.decrypt(encrypted)

                    if seq == expected_seq:
                        out_file.write(chunk)
                        last_ack = seq
                        recv_sock.sendto(f"ACK {seq}".encode(), self.addr)
                        expected_seq += 1
                    else:
                        recv_sock.sendto(f"ACK {last_ack}".encode(), self.addr)
        finally:
            with sessions_lock:
                sessions.pop(self.addr, None)

        print(f"Received file: {self.filename}")


def dispatcher_loop():
    """Main loop to dispatch incoming packets to appropriate sessions."""
    while True:
        data, addr = recv_sock.recvfrom(65536)
        if data.startswith(b"SEND"):
            with sessions_lock:
                if addr in sessions:
                    sessions[addr].queue.put(data)
                else:
                    parsed = parse_send_request(data)
                    if parsed is None:
                        print("Invalid SEND request from", addr)
                        continue
                    filename, size = parsed
                    session = ReceiveSession(addr, filename, size)
                    sessions[addr] = session
                    session.start()
        else:
            with sessions_lock:
                session = sessions.get(addr)
            if session:
                session.queue.put(data)
            else:
                print("Ignoring unexpected packet from", addr)


def main_menu():
    """Main menu for user interaction."""
    threading.Thread(target=dispatcher_loop, daemon=True).start()
    print(f"Server ready. Listening for incoming transfers on port {PORT}.")

    while True:
        print("\n1. Send File\n2. Show active sessions\n3. Exit")
        choice = input("Choose: ")

        if choice == "1":
            ip = input("Enter client IP: ")
            port_str = input(f"Enter client port [default {PORT + 1}]: ")
            client_port = int(port_str) if port_str.strip() else PORT + 1
            fname = input("Enter filename: ")
            send_file((ip, client_port), fname)

        elif choice == "2":
            with sessions_lock:
                if sessions:
                    print("Active receive sessions:")
                    for peer, session in sessions.items():
                        print(f" - {peer}: {session.filename}")
                else:
                    print("No active receive sessions")

        elif choice == "3":
            recv_sock.close()
            break


if __name__ == "__main__":
    main_menu()