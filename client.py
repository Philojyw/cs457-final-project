#!/usr/bin/env python3
"""Interactive TriviaNet TCP client."""

from __future__ import annotations

import argparse
import json
import socket
import struct
import sys
from typing import Any

HEADER_FORMAT = "!I"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_MESSAGE_SIZE = 1_048_576


def valid_port(value: str) -> int:
    """Return a validated non-privileged TCP port for argparse."""
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc

    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1024 and 65535")
    return port


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Connect to a TriviaNet game server.",
    )
    parser.add_argument(
        "-i",
        "--ip",
        dest="hostname",
        required=True,
        help="server DNS hostname or IPv4 address",
    )
    parser.add_argument(
        "-p",
        "--port",
        required=True,
        type=valid_port,
        help="server TCP port (1024-65535)",
    )
    return parser.parse_args()


def resolve_server(hostname: str) -> str:
    """Resolve the configured server name while handling DNS errors cleanly."""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        print(f"[ERROR] Unable to resolve DNS hostname '{hostname}'.")
        print(
            "Please check your Cisco router DNS configuration "
            "('ip dns server' / 'ip host') or verify domain spelling."
        )
        sys.exit(1)


def send_message(sock: socket.socket, message: dict[str, Any]) -> None:
    """Serialize and send one length-prefixed UTF-8 JSON message."""
    payload = json.dumps(message).encode("utf-8")
    frame = struct.pack(HEADER_FORMAT, len(payload)) + payload
    sock.sendall(frame)


def recv_exact(sock: socket.socket, byte_count: int) -> bytes | None:
    """Read exactly byte_count bytes, or return None on clean TCP EOF."""
    buffer = bytearray()
    while len(buffer) < byte_count:
        chunk = sock.recv(byte_count - len(buffer))
        if chunk == b"":
            return None
        buffer.extend(chunk)
    return bytes(buffer)


def recv_message(sock: socket.socket) -> dict[str, Any] | None:
    """Read and decode one complete TriviaNet frame."""
    header = recv_exact(sock, HEADER_SIZE)
    if header is None:
        return None

    payload_len = struct.unpack(HEADER_FORMAT, header)[0]
    if payload_len == 0 or payload_len > MAX_MESSAGE_SIZE:
        raise ValueError("Server sent an invalid framed payload length.")

    payload = recv_exact(sock, payload_len)
    if payload is None:
        return None

    message = json.loads(payload.decode("utf-8"))
    if not isinstance(message, dict):
        raise ValueError("Server message must be a JSON object.")
    return message


def prompt_alias() -> str:
    """Prompt until the user supplies an alias allowed by the protocol."""
    while True:
        alias = input("Choose a player alias (1-16 characters): ").strip()
        if 1 <= len(alias) <= 16:
            return alias
        print("Alias must contain between 1 and 16 characters.")


def prompt_answer(question_number: int) -> int:
    """Prompt for one answer choice in the protocol's allowed range."""
    while True:
        answer_text = input(
            f"Your answer for question {question_number} (1-4): "
        ).strip()
        try:
            answer = int(answer_text)
        except ValueError:
            print("Please enter a number from 1 through 4.")
            continue

        if 1 <= answer <= 4:
            return answer
        print("Please enter a number from 1 through 4.")


def display_question(message: dict[str, Any]) -> None:
    """Render a SEND_QUESTION payload as a readable CLI prompt."""
    print()
    print(f"Question {message['question_number']}: {message['question']}")
    for number in range(1, 5):
        print(f"  {number}. {message[f'option{number}']}")


def process_server_message(
    sock: socket.socket,
    message: dict[str, Any],
) -> bool:
    """Handle one server message; return False when the session is complete."""
    message_type = message.get("message_type")

    if message_type == "LOBBY_WAIT":
        print("Waiting for Player 2...")

    elif message_type == "GAME_START":
        role = "Player 1" if message["role"] else "Player 2"
        print()
        print("Game started!")
        print(f"You are {role}.")
        print(f"Opponent: {message['opponent_alias']}")

    elif message_type == "SEND_QUESTION":
        display_question(message)
        answer = prompt_answer(message["question_number"])
        send_message(
            sock,
            {
                "message_type": "SEND_ANSWER",
                "question_number": message["question_number"],
                "answer": answer,
            },
        )
        print("Answer submitted. Waiting for the other player...")

    elif message_type == "STATE_UPDATE":
        print()
        print(f"Round {message['question_number']} complete.")
        print(f"Correct answer: {message['correct_answer']}")
        print(
            "Score - "
            f"Player 1: {message['client_one_score']} | "
            f"Player 2: {message['client_two_score']}"
        )
        if message["is_sudden_death"]:
            print("Sudden death is active.")

    elif message_type == "ERROR":
        print(
            f"[ERROR] {message['error_code']}: "
            f"{message['error_message']}"
        )

    elif message_type == "GAME_OVER":
        print()
        print("Game over!")
        print(f"Winner: {message['winner_alias']}")
        print(
            "Final score - "
            f"Player 1: {message['client_one_score']} | "
            f"Player 2: {message['client_two_score']}"
        )
        print(f"End reason: {message['end_reason']}")
        return False

    else:
        raise ValueError(f"Unexpected server message type: {message_type!r}")

    return True


def run_client(hostname: str, port: int) -> None:
    """Resolve, connect, register, and run the interactive game loop."""
    server_ip = resolve_server(hostname)
    print(f"Resolved {hostname} to {server_ip}")

    alias = prompt_alias()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((server_ip, port))
        print(f"Connected to {hostname}:{port}")
        send_message(
            sock,
            {
                "message_type": "CONNECT",
                "user_alias": alias,
            },
        )

        keep_running = True
        while keep_running:
            message = recv_message(sock)
            if message is None:
                print("Server closed the connection.")
                break
            keep_running = process_server_message(sock, message)

    except (KeyboardInterrupt, EOFError):
        print("\nDisconnecting from TriviaNet...")
        try:
            send_message(sock, {"message_type": "DISCONNECT"})
        except OSError:
            pass
    except ConnectionRefusedError:
        print(f"[ERROR] Connection refused by {hostname}:{port}.")
        print(
            "Verify that the TriviaNet server is running and the "
            "port is correct."
        )
        sys.exit(1)
    except (
        ConnectionResetError,
        BrokenPipeError,
        ConnectionAbortedError,
        TimeoutError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        ValueError,
        OSError,
    ) as exc:
        print(f"[ERROR] Network or protocol failure: {exc}")
        sys.exit(1)
    finally:
        sock.close()


def main() -> None:
    args = parse_args()
    run_client(args.hostname, args.port)


if __name__ == "__main__":
    main()
