# Client.py Documentation

## Purpose

`Client.py` implements the UDP client side of the file transfer system. It can send files to the server and receive files from the server over UDP.

## Main Components

### Global configuration
- `SERVER_IP`: IP address of the server entered by the user.
- `SERVER_PORT`: UDP port used by the server (`5005`).
- `CLIENT_PORT`: Local UDP port for receiving incoming file transfers (`5006`).
- `CHUNK_SIZE`: Maximum payload size per UDP packet (`1024` bytes).

### Socket setup
- `send_sock`: UDP socket used for outbound file transfer packets.
- `receive_sock`: UDP socket bound to `0.0.0.0:5006` for incoming transfers.
- `SO_REUSEADDR` is enabled on the receive socket to help with restart behavior.

## Key Functions

### `send_file(filename)`
- Sends a selected file to the server.
- Protocol:
  1. Send `SEND filename size` to the server.
  2. Wait for `READY` from the server.
  3. Send file chunks with a 4-byte sequence number header.
  4. Wait for a matching `ACK <seq>` before sending the next chunk.
  5. Send `END` after the final chunk.
- If the server does not reply with `READY`, the client prints an error and aborts.
- The function retries each chunk until it receives the correct ACK.

### `receive_file()`
- Listens for an incoming `SEND` request from the server.
- Verifies the packet format and sends back `READY`.
- Receives chunk packets and writes them to `download_<filename>`.
- Acknowledges each valid, ordered chunk with `ACK <seq>`.
- If a packet does not match the expected sequence, the client re-sends the last ACK.

## Main Loop

- Displays a simple interactive menu:
  1. Send File
  2. Receive File
  3. Exit
- Option 1 calls `send_file()`.
- Option 2 calls `receive_file()`.
- Option 3 closes both sockets and exits.

## Behavior Notes

- The client uses a single send socket for all outbound traffic.
- `receive_sock` remains bound to the local client port to receive server transfers.
- Filenames are sent as plain text in the initial handshake message.
- The client does not currently sanitize incoming filenames, so it writes received files directly as `download_<filename>`.

## Limitations

- Does not support secure communication or authentication.
- No retry limit for the initial `READY` handshake.
- File names are not sanitized on receive, which may allow unexpected names in the local directory.
- The receive port is fixed, so only one client process can run on the same machine unless the port is changed.
