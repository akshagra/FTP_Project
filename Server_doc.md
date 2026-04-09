# Server.py Documentation

## Purpose

`Server.py` implements the UDP server side of the file transfer system. It listens for incoming `SEND` requests from clients, manages concurrent receive sessions, and can also initiate outbound transfers to remote clients.

## Main Components

### Global configuration
- `PORT`: UDP port the server listens on (`5005`).
- `CHUNK_SIZE`: Maximum data chunk size per UDP packet (`1024` bytes).
- `MAX_RETRIES`: Maximum number of retransmission attempts for each packet.
- `RETRY_TIMEOUT`: Timeout in seconds for waiting on a response.
- `RECEIVE_DIR`: Directory where received files are stored.

### Socket setup
- `recv_sock`: UDP socket bound to `0.0.0.0:5005`.
- Socket option `SO_REUSEADDR` is enabled to allow fast restarts.

### Session management
- `sessions`: Dictionary mapping client addresses to active receive sessions.
- `sessions_lock`: Thread lock that protects access to the `sessions` dictionary.

## Key Functions

### `sanitize_filename(filename)`
- Ensures the filename does not include directory traversal components.
- Uses `os.path.basename()` to keep only the file name.

### `parse_send_request(data)`
- Parses incoming `SEND` request packets.
- Expects the format: `SEND filename size`.
- Returns a tuple `(filename, size)` when valid; otherwise `None`.

### `parse_ack(data)`
- Parses incoming `ACK` packets.
- Expects the format: `ACK <sequence>`.
- Returns the acknowledged sequence number, or `None` on invalid packets.

### `send_file(addr, filename)`
- Sends a file to a client address using the reliable UDP transfer protocol.
- Protocol:
  1. Send `SEND filename size` and wait for `READY`.
  2. Transfer each chunk with a 4-byte sequence header.
  3. Wait for `ACK <seq>` for each chunk before sending the next.
  4. Send `END` after completion.
- Uses a separate UDP socket for sending to avoid interference with the receive socket.

## Receive Session

### `ReceiveSession` class
- A daemon thread that handles one client transfer session.
- Each session has its own queue of incoming packets.
- On initialization, it receives:
  - `addr`: client address
  - `filename`: sanitized file name
  - `expected_size`: advertised file size

### `ReceiveSession.run()`
- Sends `READY` to the client to start the transfer.
- Writes chunks to `received/<filename>`.
- Verifies sequence numbers and sends ACKs.
- If a packet is out of order, it replies with the last acknowledged sequence.
- Cleans up the session on completion.

## Dispatcher and Menu

### `dispatcher_loop()`
- Runs on a separate daemon thread.
- Reads incoming packets from the UDP socket.
- If a packet begins with `SEND`, it either creates a new session or routes it to an existing one.
- Other packets are routed to the appropriate session queue.

### `main_menu()`
- Starts the dispatcher thread.
- Provides a simple interactive menu:
  1. Send File
  2. Show active sessions
  3. Exit
- Option 1 allows the server operator to send a file to a remote client.
- Option 2 prints currently active receive sessions.

## Execution

- When executed directly, the script starts the main menu.
- The server remains available for both inbound receive sessions and manual outbound send operations.

## Notes and Limitations

- Uses UDP, so reliability is implemented at the application layer.
- No encryption is provided.
- The receive directory is created automatically.
- The protocol does not support resume or multiple simultaneous file uploads from the same client address without a new session.
