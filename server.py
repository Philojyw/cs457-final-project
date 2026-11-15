#!/usr/bin/env python3
"""TriviaNet authoritative two-player trivia server."""

from __future__ import annotations

import argparse
import json
import selectors
import socket
import struct
from dataclasses import dataclass, field
from typing import Any

HEADER_FORMAT = "!I"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_MESSAGE_SIZE = 1_048_576
NORMAL_ROUNDS = 3

QUESTIONS = [
    {
        "question": "What are the words of House Stark?",
        "options": [
            "Winter is Coming",
            "Ours is the Fury",
            "Hear Me Roar!",
            "Fire and Blood",
        ],
        "correct_option": 1,
    },
    {
        "question": "Who is Eddard Stark's wife?",
        "options": [
            "Lysa Arryn",
            "Catelyn Tully",
            "Cersei Lannister",
            "Asha Greyjoy",
        ],
        "correct_option": 2,
    },
    {
        "question": "What is the ancestral seat of House Lannister?",
        "options": [
            "Highgarden",
            "Storm's End",
            "Casterly Rock",
            "The Eyrie",
        ],
        "correct_option": 3,
    },
    {
        "question": "What is the name of House Stark's greatsword?",
        "options": [
            "Longclaw",
            "Ice",
            "Heartsbane",
            "Dark Sister",
        ],
        "correct_option": 2,
    },
    {
        "question": "Which castle is the main seat of the Night's Watch?",
        "options": [
            "Castle Black",
            "Eastwatch-by-the-Sea",
            "The Shadow Tower",
            "Queenscrown",
        ],
        "correct_option": 1,
    },
    {
        "question": "Which house rules the Iron Islands from Pyke?",
        "options": [
            "House Mormont",
            "House Tully",
            "House Greyjoy",
            "House Tyrell",
        ],
        "correct_option": 3,
    },
    {
        "question": "What title is given to the ruler of Dorne?",
        "options": [
            "Lord Paramount",
            "Prince or Princess",
            "Warden",
            "King Beyond the Wall",
        ],
        "correct_option": 2,
    },
    {
        "question": "Which city contains the Iron Throne?",
        "options": [
            "Oldtown",
            "Braavos",
            "King's Landing",
            "White Harbor",
        ],
        "correct_option": 3,
    },
]

ACTIVE_GAME_STATES = {
    "GAME_START",
    "WAITING_FOR_ANSWERS",
    "EVALUATE_ANSWERS",
    "UPDATE_STATE",
    "CHECK_GAME_STATUS",
    "SUDDEN_DEATH",
}


@dataclass(eq=False)
class ClientSession:
    """State associated with one accepted TCP connection."""

    sock: socket.socket
    addr: tuple[str, int]
    player_number: int | None = None
    user_alias: str | None = None
    registered: bool = False
    has_answered: bool = False
    answer: int | None = None
    in_buffer: bytearray = field(default_factory=bytearray)
    out_buffer: bytearray = field(default_factory=bytearray)
    expected_payload_len: int | None = None
    close_after_write: bool = False
    closed: bool = False


class TriviaServer:
    """Authoritative selector-based server for one two-player match."""

    def __init__(self, port: int) -> None:
        self.port = port
        self.selector = selectors.DefaultSelector()
        self.listen_sock: socket.socket | None = None
        self.sessions: set[ClientSession] = set()

        self.player_1: ClientSession | None = None
        self.player_2: ClientSession | None = None
        self.state = "INIT"
        self.ending_game = False

        self.p1_score = 0
        self.p2_score = 0
        self.question_number = 0
        self.normal_rounds_completed = 0
        self.in_sudden_death = False

    def run(self) -> None:
        """Bind the listening socket and service readiness events forever."""
        self._start_listener()
        print(f"TriviaNet server listening on 0.0.0.0:{self.port}")
        print("Waiting for Player 1...")

        try:
            while True:
                for key, mask in self.selector.select(timeout=None):
                    if key.data is None:
                        self._accept_client(key.fileobj)
                        continue

                    session = key.data
                    try:
                        if mask & selectors.EVENT_READ:
                            self._handle_read(session)
                        if not session.closed and mask & selectors.EVENT_WRITE:
                            self._handle_write(session)
                    except (
                        ConnectionResetError,
                        BrokenPipeError,
                        ConnectionAbortedError,
                        TimeoutError,
                        OSError,
                    ) as exc:
                        print(f"Connection error from {session.addr}: {exc}")
                        self._handle_disconnect(session)
        except KeyboardInterrupt:
            print("\nServer interrupted. Closing connections.")
        finally:
            self._shutdown()

    def _start_listener(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", self.port))
        sock.listen()
        sock.setblocking(False)
        self.selector.register(sock, selectors.EVENT_READ, data=None)
        self.listen_sock = sock
        self.state = "WAITING_FOR_PLAYER_1"

    def _accept_client(self, listening_sock: socket.socket) -> None:
        client_sock, addr = listening_sock.accept()
        client_sock.setblocking(False)
        session = ClientSession(client_sock, addr)
        self.sessions.add(session)
        self.selector.register(
            client_sock,
            selectors.EVENT_READ,
            data=session,
        )
        print(f"Accepted TCP connection from {addr}")

    def _handle_read(self, session: ClientSession) -> None:
        try:
            data = session.sock.recv(4096)
        except BlockingIOError:
            return

        if data == b"":
            self._handle_disconnect(session)
            return

        session.in_buffer.extend(data)
        self._process_buffered_messages(session)

    def _process_buffered_messages(self, session: ClientSession) -> None:
        while not session.closed:
            if session.expected_payload_len is None:
                if len(session.in_buffer) < HEADER_SIZE:
                    return

                header = session.in_buffer[:HEADER_SIZE]
                del session.in_buffer[:HEADER_SIZE]
                session.expected_payload_len = struct.unpack(
                    HEADER_FORMAT,
                    header,
                )[0]

                if (
                    session.expected_payload_len == 0
                    or session.expected_payload_len > MAX_MESSAGE_SIZE
                ):
                    self._queue_error(
                        session,
                        "MALFORMED_MESSAGE",
                        "Invalid framed payload length.",
                    )
                    session.close_after_write = True
                    return

            payload_len = session.expected_payload_len
            if len(session.in_buffer) < payload_len:
                return

            payload = bytes(session.in_buffer[:payload_len])
            del session.in_buffer[:payload_len]
            session.expected_payload_len = None

            try:
                message = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._queue_error(
                    session,
                    "MALFORMED_MESSAGE",
                    "Payload must contain valid UTF-8 JSON.",
                )
                continue

            if not isinstance(message, dict):
                self._queue_error(
                    session,
                    "MALFORMED_MESSAGE",
                    "Application message must be a JSON object.",
                )
                continue

            self._dispatch_message(session, message)
            if session.close_after_write:
                return

    def _handle_write(self, session: ClientSession) -> None:
        if not session.out_buffer:
            self._set_read_only(session)
            return

        try:
            sent = session.sock.send(session.out_buffer)
        except (BlockingIOError, InterruptedError):
            return

        if sent > 0:
            del session.out_buffer[:sent]

        if session.out_buffer:
            return

        if session.close_after_write:
            self._close_session(session)
        else:
            self._set_read_only(session)

    def _set_read_only(self, session: ClientSession) -> None:
        if session.closed:
            return
        self.selector.modify(
            session.sock,
            selectors.EVENT_READ,
            data=session,
        )

    def _dispatch_message(
        self,
        session: ClientSession,
        message: dict[str, Any],
    ) -> None:
        message_type = message.get("message_type")

        if not isinstance(message_type, str):
            self._queue_error(
                session,
                "MALFORMED_MESSAGE",
                "Missing or invalid message_type field.",
            )
            return

        if message_type == "CONNECT":
            self._handle_connect(session, message)
        elif message_type == "SEND_ANSWER":
            self._handle_answer(session, message)
        elif message_type == "DISCONNECT":
            self._handle_disconnect_message(session, message)
        elif message_type in {
            "LOBBY_WAIT",
            "GAME_START",
            "SEND_QUESTION",
            "STATE_UPDATE",
            "ERROR",
            "GAME_OVER",
        }:
            self._queue_error(
                session,
                "OUT_OF_TURN",
                f"Clients may not send {message_type} messages.",
            )
        else:
            self._queue_error(
                session,
                "INVALID_MESSAGE_TYPE",
                f"Unknown message type: {message_type}",
            )

    def _handle_connect(
        self,
        session: ClientSession,
        message: dict[str, Any],
    ) -> None:
        if set(message) != {"message_type", "user_alias"}:
            self._queue_error(
                session,
                "MALFORMED_MESSAGE",
                "CONNECT requires only message_type and user_alias.",
            )
            return

        alias = message.get("user_alias")
        if not isinstance(alias, str) or not 1 <= len(alias) <= 16:
            self._queue_error(
                session,
                "MALFORMED_MESSAGE",
                "user_alias must contain 1 to 16 characters.",
            )
            return

        if session.registered:
            self._queue_error(
                session,
                "OUT_OF_TURN",
                "This client is already registered.",
            )
            return

        if self.player_1 is None and not self.ending_game:
            self._register_player(session, alias, 1)
            self.state = "WAITING_FOR_PLAYER_2"
            self._queue_message(session, {"message_type": "LOBBY_WAIT"})
            print(f"Player 1 registered as {alias!r}")
            return

        if self.player_2 is None and self.player_1 is not None:
            if alias == self.player_1.user_alias:
                self._queue_error(
                    session,
                    "ALIAS_TAKEN",
                    "That player alias is already in use.",
                )
                return

            self._register_player(session, alias, 2)
            print(f"Player 2 registered as {alias!r}")
            self._start_game()
            return

        self._queue_error(
            session,
            "OUT_OF_TURN",
            "A two-player game is already in progress.",
        )
        session.close_after_write = True

    def _register_player(
        self,
        session: ClientSession,
        alias: str,
        player_number: int,
    ) -> None:
        session.registered = True
        session.user_alias = alias
        session.player_number = player_number

        if player_number == 1:
            self.player_1 = session
        else:
            self.player_2 = session

    def _start_game(self) -> None:
        if self.player_1 is None or self.player_2 is None:
            return

        self.state = "GAME_START"
        self.ending_game = False
        self.p1_score = 0
        self.p2_score = 0
        self.normal_rounds_completed = 0
        self.in_sudden_death = False
        self.question_number = 1
        self._reset_round_answers()

        self._queue_message(
            self.player_1,
            {
                "message_type": "GAME_START",
                "opponent_alias": self.player_2.user_alias,
                "role": True,
            },
        )
        self._queue_message(
            self.player_2,
            {
                "message_type": "GAME_START",
                "opponent_alias": self.player_1.user_alias,
                "role": False,
            },
        )
        print(
            "Game starting: "
            f"{self.player_1.user_alias} vs. {self.player_2.user_alias}"
        )
        self._send_current_question()

    def _handle_answer(
        self,
        session: ClientSession,
        message: dict[str, Any],
    ) -> None:
        if set(message) != {"message_type", "question_number", "answer"}:
            self._queue_error(
                session,
                "MALFORMED_MESSAGE",
                "SEND_ANSWER requires message_type, question_number, "
                "and answer.",
            )
            return

        if not session.registered or self.state != "WAITING_FOR_ANSWERS":
            self._queue_error(
                session,
                "OUT_OF_TURN",
                "The server is not currently accepting answers.",
            )
            return

        question_number = message.get("question_number")
        answer = message.get("answer")

        if type(question_number) is not int or type(answer) is not int:
            self._queue_error(
                session,
                "MALFORMED_MESSAGE",
                "question_number and answer must be integers.",
            )
            return

        if question_number != self.question_number:
            self._queue_error(
                session,
                "STALE_QUESTION",
                "question_number does not match the active round.",
            )
            return

        if not 1 <= answer <= 4:
            self._queue_error(
                session,
                "INVALID_ANSWER",
                "answer must be an integer from 1 through 4.",
            )
            return

        if session.has_answered:
            self._queue_error(
                session,
                "DUPLICATE_ANSWER",
                "An answer has already been submitted for this question.",
            )
            return

        session.answer = answer
        session.has_answered = True
        print(
            f"Received Q{self.question_number} answer "
            f"from {session.user_alias}: option {answer}"
        )

        if self._both_players_answered():
            self._evaluate_round()

    def _handle_disconnect_message(
        self,
        session: ClientSession,
        message: dict[str, Any],
    ) -> None:
        if set(message) != {"message_type"}:
            self._queue_error(
                session,
                "MALFORMED_MESSAGE",
                "DISCONNECT contains no additional fields.",
            )
            return
        self._handle_disconnect(session)

    def _send_current_question(self) -> None:
        if self.player_1 is None or self.player_2 is None:
            return

        question = self._current_question()
        payload = {
            "message_type": "SEND_QUESTION",
            "question_number": self.question_number,
            "question": question["question"],
            "option1": question["options"][0],
            "option2": question["options"][1],
            "option3": question["options"][2],
            "option4": question["options"][3],
        }
        self.state = "WAITING_FOR_ANSWERS"
        self._broadcast(payload)
        round_kind = "sudden death" if self.in_sudden_death else "normal"
        print(f"Sent question {self.question_number} ({round_kind} round)")

    def _current_question(self) -> dict[str, Any]:
        index = (self.question_number - 1) % len(QUESTIONS)
        return QUESTIONS[index]

    def _both_players_answered(self) -> bool:
        return bool(
            self.player_1
            and self.player_2
            and self.player_1.has_answered
            and self.player_2.has_answered
        )

    def _evaluate_round(self) -> None:
        if self.player_1 is None or self.player_2 is None:
            return

        self.state = "EVALUATE_ANSWERS"
        question = self._current_question()
        correct_option = question["correct_option"]
        p1_correct = self.player_1.answer == correct_option
        p2_correct = self.player_2.answer == correct_option

        if p1_correct:
            self.p1_score += 1
        if p2_correct:
            self.p2_score += 1

        if not self.in_sudden_death:
            self.normal_rounds_completed += 1

        entering_sudden_death = (
            not self.in_sudden_death
            and self.normal_rounds_completed >= NORMAL_ROUNDS
            and self.p1_score == self.p2_score
        )

        self.state = "UPDATE_STATE"
        state_update = {
            "message_type": "STATE_UPDATE",
            "question_number": self.question_number,
            "correct_answer": question["options"][correct_option - 1],
            "client_one_score": self.p1_score,
            "client_two_score": self.p2_score,
            "is_sudden_death": (
                self.in_sudden_death or entering_sudden_death
            ),
        }
        self._broadcast(state_update)
        print(
            f"Round {self.question_number} complete. "
            f"Score: {self.p1_score}-{self.p2_score}"
        )

        self.state = "CHECK_GAME_STATUS"
        if self.in_sudden_death:
            if self.p1_score != self.p2_score:
                self._finish_game("SUDDEN_DEATH")
            else:
                self.state = "SUDDEN_DEATH"
                self._advance_question()
            return

        if self.normal_rounds_completed < NORMAL_ROUNDS:
            self._advance_question()
            return

        if self.p1_score == self.p2_score:
            self.in_sudden_death = True
            self.state = "SUDDEN_DEATH"
            print("Scores tied. Entering sudden death.")
            self._advance_question()
        else:
            self._finish_game("NORMAL")

    def _advance_question(self) -> None:
        self.question_number += 1
        self._reset_round_answers()
        self._send_current_question()

    def _reset_round_answers(self) -> None:
        for player in (self.player_1, self.player_2):
            if player is not None:
                player.answer = None
                player.has_answered = False

    def _finish_game(self, end_reason: str) -> None:
        if self.player_1 is None or self.player_2 is None:
            return

        self.state = "GAME_OVER"
        self.ending_game = True
        winner = (
            self.player_1
            if self.p1_score > self.p2_score
            else self.player_2
        )
        payload = {
            "message_type": "GAME_OVER",
            "winner_alias": winner.user_alias,
            "client_one_score": self.p1_score,
            "client_two_score": self.p2_score,
            "end_reason": end_reason,
        }
        print(
            f"Game over. Winner: {winner.user_alias} "
            f"({self.p1_score}-{self.p2_score}, {end_reason})"
        )
        for player in (self.player_1, self.player_2):
            self._queue_message(player, payload)
            player.close_after_write = True

    def _handle_disconnect(self, session: ClientSession) -> None:
        if session.closed:
            return

        was_player_1 = session is self.player_1
        was_player_2 = session is self.player_2
        opponent = None
        if was_player_1:
            opponent = self.player_2
        elif was_player_2:
            opponent = self.player_1

        if session.registered:
            print(f"Player disconnected: {session.user_alias}")

        if (
            session.registered
            and self.state in ACTIVE_GAME_STATES
            and opponent is not None
            and not opponent.closed
        ):
            self.state = "GAME_OVER"
            self.ending_game = True
            payload = {
                "message_type": "GAME_OVER",
                "winner_alias": opponent.user_alias,
                "client_one_score": self.p1_score,
                "client_two_score": self.p2_score,
                "end_reason": "FORFEIT",
            }
            self._queue_message(opponent, payload)
            opponent.close_after_write = True
            print(f"Forfeit victory awarded to {opponent.user_alias}")

        self._close_session(session)

        if was_player_1 and self.player_2 is None and not self.ending_game:
            self.state = "WAITING_FOR_PLAYER_1"
            print("Lobby reset. Waiting for Player 1...")

    def _queue_error(
        self,
        session: ClientSession,
        error_code: str,
        error_message: str,
    ) -> None:
        self._queue_message(
            session,
            {
                "message_type": "ERROR",
                "error_code": error_code,
                "error_message": error_message,
            },
        )

    def _broadcast(self, message: dict[str, Any]) -> None:
        for player in (self.player_1, self.player_2):
            if player is not None and not player.closed:
                self._queue_message(player, message)

    def _queue_message(
        self,
        session: ClientSession,
        message: dict[str, Any],
    ) -> None:
        if session.closed:
            return

        payload = json.dumps(message).encode("utf-8")
        frame = struct.pack(HEADER_FORMAT, len(payload)) + payload
        session.out_buffer.extend(frame)
        self.selector.modify(
            session.sock,
            selectors.EVENT_READ | selectors.EVENT_WRITE,
            data=session,
        )

    def _close_session(self, session: ClientSession) -> None:
        if session.closed:
            return

        session.closed = True
        try:
            self.selector.unregister(session.sock)
        except (KeyError, ValueError):
            pass

        try:
            session.sock.close()
        except OSError:
            pass

        self.sessions.discard(session)
        if session is self.player_1:
            self.player_1 = None
        if session is self.player_2:
            self.player_2 = None

        if (
            self.ending_game
            and self.player_1 is None
            and self.player_2 is None
        ):
            self._reset_match()

    def _reset_match(self) -> None:
        self.state = "CLEANUP"
        self.p1_score = 0
        self.p2_score = 0
        self.question_number = 0
        self.normal_rounds_completed = 0
        self.in_sudden_death = False
        self.ending_game = False
        self.state = "WAITING_FOR_PLAYER_1"
        print("Match cleanup complete. Waiting for Player 1...")

    def _shutdown(self) -> None:
        for session in list(self.sessions):
            self._close_session(session)

        if self.listen_sock is not None:
            try:
                self.selector.unregister(self.listen_sock)
            except (KeyError, ValueError):
                pass
            self.listen_sock.close()

        self.selector.close()


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
        description="Run the TriviaNet authoritative game server.",
    )
    parser.add_argument(
        "-p",
        "--port",
        required=True,
        type=valid_port,
        help="TCP listening port (1024-65535)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TriviaServer(args.port).run()


if __name__ == "__main__":
    main()
