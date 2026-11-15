# TriviaNet - CS 457 Final Project

TriviaNet is a two-player terminal trivia game based on *A Song of Ice and Fire*. The server is authoritative and uses non-blocking TCP I/O multiplexing with Python `selectors`.

## Sprint 3 Quick Start

Requirements: Python 3.x, standard library only.

Start the server:

```bash
python3 server.py -p 65432
```

In two separate terminals, start two clients:

```bash
python3 client.py -i localhost -p 65432
```

For the later CML/DNS deployment, replace `localhost` with the configured server hostname:

```bash
python3 client.py -i server.leman.edu -p 65432
```

## CLI Help

```bash
python3 client.py -h
python3 server.py -h
```

Both applications validate ports in the range `1024-65535`. The client resolves hostnames with `socket.gethostbyname()` and handles DNS failures cleanly.

## Protocol

All TriviaNet messages use:

- TCP (`AF_INET`, `SOCK_STREAM`)
- UTF-8 JSON payloads
- a 4-byte unsigned big-endian length prefix (`!I`)

The full message schemas are documented in `protocol_blueprint.md`. The server FSM is documented in `fsm_specification.md`, and the selector concurrency design is documented in `concurrency_design.md`.

## Sprint 3 Demonstration

`demo_execution_log.txt` contains a successful localhost demonstration with two clients completing three rounds. Additional local testing verified sudden-death resolution and disconnect/forfeit behavior.
