# perf_eval.py Documentation

## Purpose

`perf_eval.py` is a performance evaluation script for the UDP file transfer system. It simulates multiple concurrent clients sending files to the server and measures latency and throughput metrics.

## Main Components

### Global configuration
- `SERVER_IP`: Server IP address used for testing (`127.0.0.1`).
- `SERVER_PORT`: UDP server port (`5005`).
- `CLIENT_PORT_BASE`: Base port for client receive sockets (`5006`).
- `CHUNK_SIZE`: Data chunk size in bytes (`1024`).
- `NUM_CLIENTS`: Number of concurrent simulated clients.
- `FILES_PER_CLIENT`: Number of files each simulated client will send.
- `TEST_FILE_SIZE`: Size of each test file in bytes (`100 KB`).

### Test file creation
- A temporary test file named `test_file.txt` is created at runtime.
- It contains repeated `A` bytes to match the configured size.

## Key Functions

### `client_simulation(client_id)`
- Simulates a single UDP client instance.
- Creates a send socket and a receive socket bound to a unique port.
- Performs the following for `FILES_PER_CLIENT` files:
  1. Sends `SEND <filename> <size>` to the server.
  2. Waits for `READY` and measures connection latency.
  3. Streams file chunks with 4-byte sequence headers.
  4. Waits for matching `ACK` values for each chunk.
  5. Sends `END` after the file is complete.
- Measures per-chunk latency and per-file throughput.

### `run_performance_test()`
- Starts a thread for each simulated client.
- Waits for all threads to finish.
- Computes aggregate metrics:
  - Total test time
  - Total files transferred
  - Total data transferred
  - Overall throughput
  - Connection latency statistics
  - Bid (chunk) latency statistics
  - Throughput statistics

## Measured Metrics

- **Connection latency**: Time from initial `SEND` request to `READY` response.
- **Bid latency**: Time between sending a chunk and receiving a matching `ACK`.
- **Throughput**: Kilobytes per second calculated for each file transfer.

## Behavior Notes

- The script creates `NUM_CLIENTS` concurrent sender threads.
- Each thread binds to a unique local receive port.
- The script currently uses local loopback (`127.0.0.1`) for testing.
- After the test finishes, the temporary file is removed.

## Limitations

- Assumes a server is already running on `127.0.0.1:5005`.
- Does not validate server responses beyond basic `READY` and `ACK` parsing.
- Designed for local testing; not intended for production networking.
- The current test file is recreated on every run.

## Usage

```bash
python perf_eval.py
```

- Run this while the UDP server is active.
- Review the printed metrics to compare latency and throughput.
- Use these results to update project documentation and performance analysis.
