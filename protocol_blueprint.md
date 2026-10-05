# Application Protocol Blueprint: TriviaNet Wire Protocol

**Version:** 1.0.0  
**Transport Protocol:** TCP  
**Serialization:** UTF-8 Encoded JSON  
**Framing Mechanism:** 4-Byte Big-Endian Length-Prefixed Binary Header  

---

## 1. Message Types & Structured Schema Definitions

TriviaNet uses structured JSON payloads. All message schemas require a top-level `"message_type"` string identifier. Field names, types, and constraints must be strictly adhered to by both client and server implementations.

### 1.1 CONNECT
- **Direction:** Client $\rightarrow$ Server
- **Purpose:** Initiates a session request to enter the game lobby with a chosen alias.
- **Schema Specification:**

| Field | Type | Required | Constraints / Description |
|---|---|---|---|
| `message_type` | string | Yes | Must be exactly `"CONNECT"`. |
| `user_alias` | string | Yes | Non-empty string between 1 and 16 characters. |

**Example Wire Payload:**
```json
{
  "message_type": "CONNECT",
  "user_alias": "GRRM#1_FAN"
}
```

---

### 1.2 LOBBY_WAIT
- **Direction:** Server $\rightarrow$ Client (Player 1)
- **Purpose:** Acknowledges Player 1's connection and informs them that the server is waiting for an opponent.
- **Schema Specification:**

| Field | Type | Required | Constraints / Description |
|---|---|---|---|
| `message_type` | string | Yes | Must be exactly `"LOBBY_WAIT"`. |

**Example Wire Payload:**
```json
{
  "message_type": "LOBBY_WAIT"
}
```

---

### 1.3 GAME_START
- **Direction:** Server $\rightarrow$ Clients (Broadcast to Player 1 and Player 2)
- **Purpose:** Notifies both clients that matchmaking is complete, assigns roles, and identifies opponents.
- **Schema Specification:**

| Field | Type | Required | Constraints / Description |
|---|---|---|---|
| `message_type` | string | Yes | Must be exactly `"GAME_START"`. |
| `opponent_alias` | string | Yes | Non-empty string containing the opponent's chosen alias. |
| `role` | bool | Yes | `true` if Client is assigned Player 1; `false` if Client is Player 2. |

**Example Wire Payload (Sent to Player 1):**
```json
{
  "message_type": "GAME_START",
  "opponent_alias": "Sweet Robin",
  "role": true
}
```

---

### 1.4 SEND_QUESTION
- **Direction:** Server $\rightarrow$ Clients (Broadcast)
- **Purpose:** Delivers a synchronized multiple-choice trivia question for the current round.
- **Schema Specification:**

| Field | Type | Required | Constraints / Description |
|---|---|---|---|
| `message_type` | string | Yes | Must be exactly `"SEND_QUESTION"`. |
| `question_number` | int | Yes | 1-indexed sequential integer identifying the active question. |
| `question` | string | Yes | Non-empty question prompt. |
| `option1` | string | Yes | Choice 1 text. |
| `option2` | string | Yes | Choice 2 text. |
| `option3` | string | Yes | Choice 3 text. |
| `option4` | string | Yes | Choice 4 text. |

**Example Wire Payload:**
```json
{
  "message_type": "SEND_QUESTION",
  "question_number": 4,
  "question": "What major reveal about Tyrion's past was changed from the books in season 5?",
  "option1": "He actually isn't a dwarf.",
  "option2": "His mother did not die during childbirth.",
  "option3": "He is the prince who was promised.",
  "option4": "His first love was not actually a prostitute."
}
```

---

### 1.5 SEND_ANSWER
- **Direction:** Client $\rightarrow$ Server
- **Purpose:** Submits a player's selected option for the currently active question.
- **Schema Specification:**

| Field | Type | Required | Constraints / Description |
|---|---|---|---|
| `message_type` | string | Yes | Must be exactly `"SEND_ANSWER"`. |
| `question_number` | int | Yes | Must match the active server `question_number`. |
| `answer` | int | Yes | Integer selection bounded to $[1, 4]$. |

**Example Wire Payload:**
```json
{
  "message_type": "SEND_ANSWER",
  "question_number": 4,
  "answer": 4
}
```

---

### 1.6 STATE_UPDATE
- **Direction:** Server $\rightarrow$ Clients (Broadcast)
- **Purpose:** Broadcasts round evaluation, running scores, and sudden-death status.
- **Schema Specification:**

| Field | Type | Required | Constraints / Description |
|---|---|---|---|
| `message_type` | string | Yes | Must be exactly `"STATE_UPDATE"`. |
| `question_number` | int | Yes | The question number just evaluated. |
| `correct_answer` | string | Yes | Text string corresponding to the correct answer. |
| `client_one_score` | int | Yes | Non-negative cumulative score for Player 1. |
| `client_two_score` | int | Yes | Non-negative cumulative score for Player 2. |
| `is_sudden_death` | bool | Yes | `true` if entering or remaining in sudden death; else `false`. |

**Example Wire Payload:**
```json
{
  "message_type": "STATE_UPDATE",
  "question_number": 4,
  "correct_answer": "His first love was not actually a prostitute.",
  "client_one_score": 3,
  "client_two_score": 3,
  "is_sudden_death": true
}
```

---

### 1.7 ERROR
- **Direction:** Server $\rightarrow$ Client (Unicast)
- **Purpose:** Informs a client of a malformed packet, protocol violation, or invalid action without terminating the game loop.
- **Schema Specification:**

| Field | Type | Required | Constraints / Description |
|---|---|---|---|
| `message_type` | string | Yes | Must be exactly `"ERROR"`. |
| `error_code` | string | Yes | Standardized error identifier from the Error Code Table. |
| `error_message` | string | Yes | Human-readable explanation of the error condition. |

#### Standardized Error Codes:
- `MALFORMED_MESSAGE`: Non-JSON data or missing mandatory schema fields.
- `INVALID_MESSAGE_TYPE`: `message_type` string unrecognized by the parser.
- `OUT_OF_TURN`: Message sent during an incompatible state (e.g., answering before `GAME_START`).
- `INVALID_ANSWER`: Answer integer outside the allowed range of 1 to 4.
- `DUPLICATE_ANSWER`: Player already submitted an answer for this question round.
- `STALE_QUESTION`: `question_number` does not match the active server round.
- `ALIAS_TAKEN`: Player 2 submitted an alias identical to Player 1.

**Example Wire Payload:**
```json
{
  "message_type": "ERROR",
  "error_code": "DUPLICATE_ANSWER",
  "error_message": "An answer has already been submitted for question 4."
}
```

---

### 1.8 DISCONNECT
- **Direction:** Client $\rightarrow$ Server
- **Purpose:** Signals an intentional, graceful departure from the lobby or active match.
- **Schema Specification:**

| Field | Type | Required | Constraints / Description |
|---|---|---|---|
| `message_type` | string | Yes | Must be exactly `"DISCONNECT"`. |

**Example Wire Payload:**
```json
{
  "message_type": "DISCONNECT"
}
```

---

### 1.9 GAME_OVER
- **Direction:** Server $\rightarrow$ Clients (Broadcast)
- **Purpose:** Declares match termination, final victor, and closing scores.
- **Schema Specification:**

| Field | Type | Required | Constraints / Description |
|---|---|---|---|
| `message_type` | string | Yes | Must be exactly `"GAME_OVER"`. |
| `winner_alias` | string | Yes | Alias of the player who won the game. |
| `client_one_score` | int | Yes | Final cumulative score for Player 1. |
| `client_two_score` | int | Yes | Final cumulative score for Player 2. |
| `end_reason` | string | Yes | Exactly `"NORMAL"`, `"SUDDEN_DEATH"`, or `"FORFEIT"`. |

**Example Wire Payload:**
```json
{
  "message_type": "GAME_OVER",
  "winner_alias": "GRRM#1_FAN",
  "client_one_score": 7,
  "client_two_score": 5,
  "end_reason": "NORMAL"
}
```

---

## 2. TCP Stream Packet Framing & Boundary Handling

### 2.1 The TCP Byte-Stream Problem
TCP is an unsegmented, continuous byte stream. It guarantees in-order, reliable delivery, but does not preserve application message boundaries. 
- **Message Coalescing:** Multiple messages sent in rapid succession can be combined by the operating system or Nagle's algorithm into a single TCP segment and returned in a single `recv()` call.
- **Message Fragmentation:** A single message can be segmented across multiple IP packets, meaning a single `recv()` call may return only a partial header or partial payload.

### 2.2 Framing Rule Specification
TriviaNet solves this using **Length-Prefixed Framing with a Fixed-Width Binary Header**:
1. Every application message consists of a **4-byte fixed-width header** followed immediately by the variable-length UTF-8 payload.
2. The 4-byte header encodes the exact length $N$ (in bytes) of the payload as an unsigned 32-bit integer in **Network Byte Order (Big-Endian)**.
3. The receiver operates deterministically in two discrete phases:
   - **Phase 1 (Header Read):** Accumulate exactly 4 bytes from the wire. Unpack using `struct.unpack('!I', header_bytes)` to obtain length $N$.
   - **Phase 2 (Payload Read):** Accumulate exactly $N$ bytes from the wire into a local buffer. Only after all $N$ bytes are collected is the buffer decoded as UTF-8 and deserialized as JSON.

```
+-----------------------------------+--------------------------------------------+
| 4-Byte Length Header (Big-Endian) | Variable-Length JSON Payload (UTF-8 Bytes) |
| (0x00 0x00 0x00 0x37 = 55 bytes)  | {"message_type":"CONNECT", ...}            |
+-----------------------------------+--------------------------------------------+
|<---------- 4 Bytes -------------->|<---------------- N Bytes ----------------->|
```

### 2.3 Wire Stream Representation
Two consecutive `CONNECT` messages sent back-to-back illustrating message coalescing:

- **Message 1 Payload (55 Bytes):**  
  `{"message_type": "CONNECT", "user_alias": "GRRM#1_FAN"}`  
  Length Prefix: `55` $\rightarrow$ Hex `0x00000037` $\rightarrow$ Bytes: `\x00\x00\x00\x37`

- **Message 2 Payload (56 Bytes):**  
  `{"message_type": "CONNECT", "user_alias": "Sweet Robin"}`  
  Length Prefix: `56` $\rightarrow$ Hex `0x00000038` $\rightarrow$ Bytes: `\x00\x00\x00\x38`

#### Continuous Byte Stream on the Wire:
```
[Header 1: 4B] [Payload 1: 55B                                           ] [Header 2: 4B] [Payload 2: 56B                                            ]
\x00\x00\x00\x37{"message_type": "CONNECT", "user_alias": "GRRM#1_FAN"}\x00\x00\x00\x38{"message_type": "CONNECT", "user_alias": "Sweet Robin"}
```

### 2.4 Reference Python Framing Implementation

```python
import json
import struct
import socket

HEADER_FORMAT = "!I"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 4 bytes

def send_framed_message(sock: socket.socket, message_dict: dict) -> None:
    """Serializes, frames, and sends an application message over TCP."""
    payload_bytes = json.dumps(message_dict).encode("utf-8")
    header = struct.pack(HEADER_FORMAT, len(payload_bytes))
    sock.sendall(header + payload_bytes)

def recv_exact(sock: socket.socket, n_bytes: int) -> bytes | None:
    """
    Accumulates exactly n_bytes from the TCP socket buffer.
    Handles fragmentation across multiple recv() chunks.
    Returns None immediately if EOF (b"") is encountered.
    """
    buf = bytearray()
    while len(buf) < n_bytes:
        chunk = sock.recv(n_bytes - len(buf))
        if not chunk:
            return None  # TCP EOF: Peer closed connection
        buf.extend(chunk)
    return bytes(buf)

def recv_framed_message(sock: socket.socket) -> dict | None:
    """Reads a complete framed message from the socket."""
    header_bytes = recv_exact(sock, HEADER_SIZE)
    if header_bytes is None:
        return None
    
    payload_len = struct.unpack(HEADER_FORMAT, header_bytes)[0]
    payload_bytes = recv_exact(sock, payload_len)
    if payload_bytes is None:
        return None
    
    return json.loads(payload_bytes.decode("utf-8"))
```

---

## 3. Connection Termination & Socket Lifecycle Management

### 3.1 Graceful Application Disconnect
A graceful departure occurs when a client intentionally leaves via the application layer:
1. Client transmits a framed `DISCONNECT` message.
2. Server consumes `DISCONNECT`, identifies the originating player, and updates the state machine:
   - If in `WAITING_FOR_PLAYER_2`: Server resets back to `WAITING_FOR_PLAYER_1`.
   - If during an active match (`WAITING_FOR_ANSWERS`, etc.): Server declares the remaining player victor by forfeit, sending a `GAME_OVER` message with `end_reason: "FORFEIT"`.
3. Client and server invoke `sock.close()`, which sends a TCP FIN packet and initiates the standard 4-way TCP FIN handshake.

### 3.2 TCP 0-Byte EOF Detection
When a client terminates cleanly without sending an application-level `DISCONNECT` (e.g., normal process exit), the OS sends a FIN. Calling `sock.recv()` returns `b""` (0 bytes).
- **Infinite Loop Guard:** Socket loops must check `if not chunk: return None`. Without this check, non-blocking or select-driven loops enter a 100% CPU infinite spin.
- **Handling Incomplete Reads:** If `recv_exact` receives EOF while in the middle of reading a header or payload, the incomplete segment is discarded, the socket is closed, and forfeit cleanup is triggered.

### 3.3 Abrupt Failures & Socket Exception Traps
Abrupt events (network cable unplugged, `kill -9`, power loss) do not send FIN packets. Subsequent socket I/O raises OS-level exceptions:
- `ConnectionResetError` (WSAECONNRESET / ECONNRESET): Peer host forcibly killed connection; RST received.
- `BrokenPipeError` (EPIPE): Attempted `sendall()` to a socket where the remote end is already closed.
- `ConnectionAbortedError`: Local OS aborted the connection.
- `TimeoutError`: Socket read/write deadline exceeded.

#### Server Lifecycle Exception Trap Pattern:
```python
try:
    message = recv_framed_message(player_sock)
    if message is None:
        # Detected clean EOF via recv() == b""
        handle_disconnect(player_id, reason="EOF")
    else:
        dispatch_message(player_id, message)
except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, TimeoutError) as e:
    # Abrupt network drop / crash
    logger.warning(f"Abrupt disconnect from {player_id}: {e}")
    handle_disconnect(player_id, reason="ABRUPT_RESET")
```