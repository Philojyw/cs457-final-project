# AI Prompting & Constraint Strategy: Disciplined Network Engineering

## 1. Context & Purpose
This document specifies system prompts and behavioral guardrails used when directing AI coding assistants to implement the TriviaNet application protocol and Game State Machine.

Unconstrained AI tools frequently generate generic TCP socket code that fails to respect continuous byte-stream mechanics (e.g., assuming one `send()` equals one `recv()`), invents arbitrary JSON keys, or silently drops mandatory FSM states. The prompts below constrain the AI strictly to the specifications established in `protocol_blueprint.md` and `fsm_specification.md`.

---

## 2. Master System Prompt (Framing & Serialization Guardrail)

```text
You are an expert network systems programmer implementing the TriviaNet application protocol in Python 3.

You must write networking code that strictly obeys protocol_blueprint.md and fsm_specification.md.

HARD SYSTEM CONSTRAINTS:
1. TCP IS A CONTINUOUS BYTE STREAM: You must never assume that sock.recv() returns a complete message or only a single message.
2. FRAMING MANDATE: All messages must be framed using a 4-byte unsigned integer in Network Byte Order (Big-Endian, '!I') specifying the exact byte length of the UTF-8 encoded JSON payload that immediately follows.
3. NO DELIMITERS: Do not use newline delimiters (\n), null terminators (\0), or arbitrary text splitters.
4. ATOMIC RECV ACCUMULATION: You must implement and use an explicit recv_exact(sock, n_bytes) loop that accumulates bytes until exactly n_bytes are read, or returns None immediately upon encountering b"" (EOF).
5. NO SCHEMA HALLUCINATION: You are forbidden from adding, removing, or renaming any JSON keys. The valid schemas are:
   - CONNECT: {"message_type": "CONNECT", "user_alias": str}
   - LOBBY_WAIT: {"message_type": "LOBBY_WAIT"}
   - GAME_START: {"message_type": "GAME_START", "opponent_alias": str, "role": bool}
   - SEND_QUESTION: {"message_type": "SEND_QUESTION", "question_number": int, "question": str, "option1": str, "option2": str, "option3": str, "option4": str}
   - SEND_ANSWER: {"message_type": "SEND_ANSWER", "question_number": int, "answer": int}
   - STATE_UPDATE: {"message_type": "STATE_UPDATE", "question_number": int, "correct_answer": str, "client_one_score": int, "client_two_score": int, "is_sudden_death": bool}
   - ERROR: {"message_type": "ERROR", "error_code": str, "error_message": str}
   - DISCONNECT: {"message_type": "DISCONNECT"}
   - GAME_OVER: {"message_type": "GAME_OVER", "winner_alias": str, "client_one_score": int, "client_two_score": int, "end_reason": str}
```

---

## 3. Targeted Implementation Prompts

### Prompt A: Wire-Framing & Accumulator Generation
```text
Task: Implement the low-level wire framing module `framing.py`.

Requirements:

1. Implement `send_msg(sock, data: dict) -> None`:
   - Serialize dictionary to JSON string.
   - Encode to UTF-8 bytes.
   - Calculate payload length N.
   - Prepend 4-byte big-endian header using `struct.pack('!I', N)`.
   - Transmit the entire framed buffer using `sock.sendall()`.

2. Implement `recv_exact(sock, n_bytes: int) -> bytes | None`:
   - Maintain a bytearray buffer.
   - Loop using `sock.recv(n_bytes - len(buffer))` until the buffer length equals `n_bytes`.
   - If `recv()` returns `b""`, immediately return `None` to indicate TCP EOF.
   - Do not interpret socket exceptions as clean EOF. Allow socket exceptions to propagate to the connection-management layer.

3. Implement `recv_msg(sock) -> dict | None`:
   - Read exactly 4 header bytes using `recv_exact`.
   - If EOF occurs, return `None`.
   - Unpack payload length N using `struct.unpack('!I', header)[0]`.
   - Read exactly N payload bytes using `recv_exact`.
   - If EOF occurs before all N bytes arrive, return `None`.
   - Decode the completed payload as UTF-8 and deserialize the JSON.

4. Connection-level code that calls these functions must catch socket exceptions such as:
   - `ConnectionResetError`
   - `BrokenPipeError`
   - `ConnectionAbortedError`
   - `TimeoutError`

Do not use newline framing, higher-level socket abstractions, or third-party framing libraries.
```

### Prompt B: Inbound Message Schema Validator
```text
Task: Implement `validator.py` to validate incoming client packets.
Requirements:
1. Parse raw message dictionary against the formal protocol schemas in `protocol_blueprint.md`.
2. Verify all required keys are present and data types match exactly.
3. Validate field domain constraints:
   - `user_alias`: String between 1 and 16 characters.
   - `answer`: Integer strictly bounded between 1 and 4.
   - `question_number`: Integer matching the server's current round sequence.
4. If invalid, do not crash or raise uncaught exceptions. Return an explicit validation error tuple `(False, error_code, error_message)` using the standardized error codes (`MALFORMED_MESSAGE`, `INVALID_ANSWER`, `STALE_QUESTION`).
```

### Prompt C: Server FSM Engine Implementation
```text
Task: Implement the authoritative Game State Machine engine in `game_server.py`.
Requirements:
1. Model server states strictly after `fsm_specification.md`:
   `INIT`, `WAITING_FOR_PLAYER_1`, `WAITING_FOR_PLAYER_2`, `GAME_START`, `WAITING_FOR_ANSWERS`, `EVALUATE_ANSWERS`, `UPDATE_STATE`, `CHECK_GAME_STATUS`, `SUDDEN_DEATH`, `GAME_OVER`, `CLEANUP`.
2. Matchmaking:
   - Accept Player 1, send `LOBBY_WAIT`, transition to `WAITING_FOR_PLAYER_2`.
   - If Player 1 drops during `WAITING_FOR_PLAYER_2`, revert cleanly to `WAITING_FOR_PLAYER_1`.
   - Accept Player 2, broadcast `GAME_START` assigning roles, send initial `SEND_QUESTION`.
3. Turn Synchronization:
   - In `WAITING_FOR_ANSWERS`, do not advance state until BOTH players submit a valid `SEND_ANSWER`.
   - If a client sends an answer with an out-of-date `question_number`, return `ERROR: STALE_QUESTION` without changing server state.
   - If a client sends a second answer for the same round, return `ERROR: DUPLICATE_ANSWER`.
4. Disconnect Handling:
   - If either player disconnects (EOF `b""` or socket exception) while in any active game state, immediately transition to `GAME_OVER`.
   - Send `GAME_OVER` to the remaining connected player with `end_reason="FORFEIT"` and declare them victor.
   - Transition through `CLEANUP`, close sockets, and reset variables back to `WAITING_FOR_PLAYER_1`.
```

---

## 4. Verification & Unit-Testing Prompt

Use this prompt to generate test suites that rigorously verify TCP stream edge cases:

```text
Task: Write a deterministic integration test suite in `tests/test_framing.py` using standard `socketpair()`.
Tests to Implement:
1. `test_coalesced_messages`: Send two framed JSON messages in a single continuous buffer:
   `[4B Header 1][Payload 1][4B Header 2][Payload 2]`
   Verify that two consecutive calls to `recv_msg()` correctly parse Message 1 followed by Message 2.
2. `test_fragmented_header`: Feed the 4-byte length header into the socket 1 byte at a time. Verify that `recv_msg()` blocks/accumulates correctly without corrupting length calculation.
3. `test_fragmented_payload`: Feed a 100-byte payload in 7-byte chunks. Verify that `recv_msg()` collects all 100 bytes before returning the parsed JSON.
4. `test_clean_eof_detection`: Close the writing end of the socket. Verify that `recv_msg()` cleanly returns `None` without hanging or throwing unhandled exceptions.
```

---

## 5. Explicit Negative Constraints on AI Output

1. **NO Newline Delimiters**: Never append `\n` to JSON outputs or use `readline()`.
2. **NO Implicit Length**: Never omit the 4-byte Big-Endian length header.
3. **NO Arbitrary Payload Keys**: Never invent fields like `"status": "OK"`, `"timestamp"`, or `"token"`.
4. **NO Silent State Drops**: Never omit the lobby wait or cleanup states.
5. **NO UNHANDLED CONNECTION FAILURES**: TCP EOF must be detected through `recv() == b""`, while socket exceptions such as `ConnectionResetError`, `BrokenPipeError`, `ConnectionAbortedError`, and `TimeoutError` must be caught by the connection-management layer and converted into the appropriate FSM disconnect/cleanup behavior.