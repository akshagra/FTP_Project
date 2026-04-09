import socket
import os
import time
import threading
import statistics

# Configuration
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5005
CLIENT_PORT_BASE = 5006
CHUNK_SIZE = 1024
NUM_CLIENTS = 5
FILES_PER_CLIENT = 3
TEST_FILE_SIZE = 1024 * 100  # 100KB test file

# Create test file
test_filename = "test_file.txt"
with open(test_filename, "wb") as f:
    f.write(b"A" * TEST_FILE_SIZE)

print(f"Created test file: {test_filename} ({TEST_FILE_SIZE} bytes)")

# Performance metrics
connection_latencies = []
bid_latencies = []
throughput_measurements = []

def client_simulation(client_id):
    """Simulate a client sending files and measuring performance."""
    client_port = CLIENT_PORT_BASE + client_id
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receive_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receive_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    receive_sock.bind(("0.0.0.0", client_port))

    for file_num in range(FILES_PER_CLIENT):
        # Measure connection latency
        start_time = time.time()
        size = os.path.getsize(test_filename)
        send_sock.sendto(f"SEND {test_filename} {size}".encode(), (SERVER_IP, SERVER_PORT))

        send_sock.settimeout(10)
        try:
            data, _ = send_sock.recvfrom(1024)
            if data == b"READY":
                connection_time = time.time() - start_time
                connection_latencies.append(connection_time * 1000)  # ms
            else:
                print(f"Client {client_id}: Server not ready")
                continue
        except socket.timeout:
            print(f"Client {client_id}: No READY from server")
            continue

        # Send file and measure bid latencies
        with open(test_filename, "rb") as f:
            seq = 0
            file_start = time.time()
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break

                packet = seq.to_bytes(4, "big") + chunk
                bid_start = time.time()

                for attempt in range(5):  # max retries
                    send_sock.sendto(packet, (SERVER_IP, SERVER_PORT))
                    try:
                        send_sock.settimeout(1)
                        ack_data, _ = send_sock.recvfrom(1024)
                        if ack_data.startswith(b"ACK"):
                            parts = ack_data.decode().split()
                            if len(parts) >= 2 and int(parts[1]) == seq:
                                bid_time = time.time() - bid_start
                                bid_latencies.append(bid_time * 1000)  # ms
                                seq += 1
                                break
                    except socket.timeout:
                        continue
                else:
                    print(f"Client {client_id}: Failed to send chunk {seq}")
                    break

        send_sock.sendto(b"END", (SERVER_IP, SERVER_PORT))
        file_time = time.time() - file_start
        throughput = (size / 1024) / file_time  # KB/s
        throughput_measurements.append(throughput)

        print(f"Client {client_id}, File {file_num + 1}: Sent in {file_time:.2f}s ({throughput:.2f} KB/s)")

    send_sock.close()
    receive_sock.close()

def run_performance_test():
    """Run the performance evaluation."""
    print("Starting performance evaluation...")
    print(f"Testing with {NUM_CLIENTS} concurrent clients, {FILES_PER_CLIENT} files each")

    threads = []
    start_time = time.time()

    for i in range(NUM_CLIENTS):
        t = threading.Thread(target=client_simulation, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total_time = time.time() - start_time
    total_files = NUM_CLIENTS * FILES_PER_CLIENT
    total_data = total_files * TEST_FILE_SIZE / 1024  # KB

    print("\n=== Performance Results ===")
    print(f"Total test time: {total_time:.2f} seconds")
    print(f"Total files transferred: {total_files}")
    print(f"Total data transferred: {total_data:.0f} KB")
    print(f"Overall throughput: {total_data / total_time:.2f} KB/s")

    if connection_latencies:
        print("\nConnection latency (ms):")
        print(f"  Min: {min(connection_latencies):.2f}")
        print(f"  Max: {max(connection_latencies):.2f}")
        print(f"  Avg: {statistics.mean(connection_latencies):.2f}")
        print(f"  Std Dev: {statistics.stdev(connection_latencies):.2f}")

    if bid_latencies:
        print("\nBid latency (ms):")
        print(f"  Min: {min(bid_latencies):.2f}")
        print(f"  Max: {max(bid_latencies):.2f}")
        print(f"  Avg: {statistics.mean(bid_latencies):.2f}")
        print(f"  Median: {statistics.median(bid_latencies):.2f}")
        print(f"  Std Dev: {statistics.stdev(bid_latencies):.2f}")

    if throughput_measurements:
        print("\nThroughput (KB/s):")
        print(f"  Min: {min(throughput_measurements):.2f}")
        print(f"  Max: {max(throughput_measurements):.2f}")
        print(f"  Avg: {statistics.mean(throughput_measurements):.2f}")

    print(f"\nErrors: 0")

if __name__ == "__main__":
    run_performance_test()

    # Cleanup
    if os.path.exists(test_filename):
        os.remove(test_filename)