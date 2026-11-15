# CS 457 Project Statement of Work (SOW) & Protocol Specification 
**Student Name:** Matthew Leman 
**Date:** 2026-09-20 
**Course:** CS 457 - Computer Networks 
**Target Server Domain:** `server.leman.edu` 
--- 

## 1. Game Selection & Scope (Sprint 0) 

### 1.1 Game Overview 
- **Chosen Game:** A Song of Ice and Fire Terminal Trivia 
- **Player Capacity:** 2 Players (Simulated via 2 CML Client nodes) 
- **Game Summary:** The game is a two-player, round-based trivia game based on George R. R. Martin's *A Song of Ice and Fire* book series. Both players connect to a central game server and answer trivia questions about characters, locations, events, houses, history, and other information from the books. The server presents the questions, receives each player's answers, determines whether the answers are correct, and keeps track of the players' scores. After a predetermined number of questions have been answered, the player with the highest score wins. 
### 1.2 Core Game Rules & Win/Draw Conditions 
- **Turn Mechanics:** The game will be played in rounds. During each round, the server will provide a trivia question to both players. Each player will submit an answer from their client. The server will evaluate the answers and award points for correct responses. After both players have answered, the server will display the correct answer and update the scores before beginning the next round. 
- **Victory Condition:** The game will contain a predetermined number of trivia rounds. Each correct answer will award one point. After the final round, the player with the highest total score will be declared the winner. 
- **Draw/Tie Condition:** If both players have the same score after the final scheduled round, the game will enter a sudden-death tiebreaker. Additional trivia questions will be asked until one player answers a question correctly while the other player answers incorrectly. The player who answers correctly will win the game. 

--- 

## 2. Application-Layer Messaging Protocol Blueprint (Sprint 1 Deliverable)

### 2.1 Transport, Serialization, & Framing

- **Transport Protocol:** TCP
- **Serialization Format:** UTF-8 encoded JSON
- **Framing Mechanism:** 4-byte unsigned big-endian length-prefixed framing

Each application message is serialized into JSON and encoded as UTF-8 bytes. Before the payload is transmitted, the sender calculates the exact number of bytes in the encoded payload and places that value into a 4-byte unsigned integer using Network Byte Order (big-endian).

The receiver first accumulates exactly 4 bytes to obtain the payload length. It then continues reading from the TCP stream until exactly the specified number of payload bytes have been received. Only after the complete payload has been accumulated is it decoded from UTF-8 and parsed as JSON.

This framing mechanism prevents the application from incorrectly assuming that a single TCP `recv()` call corresponds to one complete application message and handles both TCP fragmentation and message coalescing.

### 2.2 Application Message Types

The TriviaNet protocol defines the following application-layer message types:

| Message Type | Direction | Purpose |
|---|---|---|
| `CONNECT` | Client -> Server | Requests entry into the game lobby using a player alias. |
| `LOBBY_WAIT` | Server -> Client | Notifies Player 1 that the server is waiting for Player 2. |
| `GAME_START` | Server -> Clients | Announces the start of the game, identifies the opponent, and assigns Player 1 / Player 2 roles. |
| `SEND_QUESTION` | Server -> Clients | Sends the synchronized trivia question and four answer choices for the current round. |
| `SEND_ANSWER` | Client -> Server | Submits a player's selected answer and corresponding question number. |
| `STATE_UPDATE` | Server -> Clients | Reports the correct answer, updated scores, and sudden-death status. |
| `ERROR` | Server -> Client | Reports malformed, duplicate, stale, or otherwise invalid client actions without terminating the game. |
| `DISCONNECT` | Client -> Server | Notifies the server that a client is intentionally leaving the lobby or active game. |
| `GAME_OVER` | Server -> Clients | Reports the winner, final scores, and whether the game ended normally, in sudden death, or by forfeit. |

Each message has an explicitly defined JSON schema containing required fields, data types, and validation rules. The complete schemas and example payloads are defined in `protocol_blueprint.md`.

### 2.3 Question & Answer Synchronization

Every `SEND_QUESTION` contains a sequential `question_number`. The client includes the same value in its corresponding `SEND_ANSWER`.

The server uses the question number to ensure that answers belong to the currently active round. Duplicate answers, stale question numbers, malformed messages, and answer selections outside the valid range are rejected with an `ERROR` message without advancing the game state.

The server waits until both players have submitted valid answers before evaluating the round and broadcasting a `STATE_UPDATE`.

### 2.4 Connection Termination & Failure Handling

The protocol supports both graceful and unexpected connection termination.

A client intentionally leaving the game sends a `DISCONNECT` message before closing its TCP socket. During an active game, the remaining connected player is declared the winner by forfeit.

A clean TCP closure is detected when `recv()` returns zero bytes (`b""`), indicating EOF. If EOF occurs while receiving either the 4-byte framing header or the JSON payload, the incomplete message is discarded and disconnect handling begins.

Abrupt connection failures are handled through socket exceptions such as `ConnectionResetError`, `BrokenPipeError`, `ConnectionAbortedError`, and `TimeoutError`. These failures do not crash the game server and instead trigger the appropriate disconnect, forfeit, and cleanup behavior.

### 2.5 Server Finite State Machine

The server operates as an authoritative finite state machine. Major server states include:

- `INIT`
- `WAITING_FOR_PLAYER_1`
- `WAITING_FOR_PLAYER_2`
- `GAME_START`
- `WAITING_FOR_ANSWERS`
- `EVALUATE_ANSWERS`
- `UPDATE_STATE`
- `CHECK_GAME_STATUS`
- `SUDDEN_DEATH`
- `GAME_OVER`
- `CLEANUP`

The server remains in `WAITING_FOR_ANSWERS` until both players submit valid answers. Invalid, duplicate, stale, or early submissions generate an `ERROR` without advancing the FSM.

After the scheduled rounds have been completed, unequal scores result in `GAME_OVER`. Equal scores transition the server into `SUDDEN_DEATH`. Sudden-death rounds continue until one player answers correctly while the other answers incorrectly.

A disconnect during active gameplay immediately results in a forfeit victory for the remaining player. After `GAME_OVER`, the server enters `CLEANUP`, closes game sockets, resets game data, and returns to `WAITING_FOR_PLAYER_1`.

The complete Mermaid `stateDiagram-v2` diagram and formal transition definitions are contained in `fsm_specification.md`.

### 2.6 AI Prompting & Protocol Constraints

AI coding assistants used during implementation will be constrained to the protocol and FSM designed during Sprint 1.

The AI is explicitly instructed not to:

- Add, remove, or rename application message fields.
- Invent additional message types.
- Replace the 4-byte big-endian length-prefix framing mechanism.
- Assume one TCP `recv()` call contains one complete message.
- Ignore TCP EOF or socket failure conditions.
- Advance the game state after invalid messages.
- Invent game states or transitions outside the documented FSM.

The prompts and implementation constraints are documented in `ai_prompts.md`.

---

## 3. Game Behavior & Server Concurrency Architecture (Sprint 2 Deliverable)

### 3.1 Server Concurrency Strategy

- **Architecture Choice:** Non-blocking I/O multiplexing using Python's `selectors` module and `selectors.DefaultSelector`.

- **Connection Handling:** The TriviaNet server will operate using a single event loop rather than creating a separate thread for each connected player. The listening socket and each accepted client socket will be placed into non-blocking mode with `setblocking(False)` and registered with the selector. The selector will monitor sockets for read and write readiness so that the server can service either player without blocking while waiting for the other player.

- **Connection Lifecycle:** When the listening socket becomes ready, the server will accept the new TCP connection, place the client socket into non-blocking mode, create a session record for the client, and register the socket with the selector. After receiving a valid `CONNECT` message, the first player will receive `LOBBY_WAIT`. Once the second player registers, both players will receive `GAME_START` and the match will begin. During the match, client sockets will remain registered with the selector until the client disconnects, the connection fails, or the game completes. Closed sockets will be unregistered from the selector before being closed.

- **TCP Message Handling:** Each client will maintain its own incoming and outgoing byte buffers. TriviaNet uses UTF-8 JSON messages framed with a 4-byte big-endian length prefix. Because TCP does not preserve application message boundaries, received bytes will remain buffered until both the complete length header and the complete JSON payload are available. Outgoing messages will also be buffered so that partial `send()` operations do not block the event loop.

- **Synchronization and Thread Safety:** Shared game state will include the connected players, current question number, current question, submitted answers, player scores, sudden-death status, and the current state of the game. Because all socket events and game-state changes are processed by one event-loop thread, only one handler modifies the shared state at a time. TriviaNet therefore uses event-loop state isolation rather than `threading.Lock` or other mutexes to prevent race conditions.

- **Server Authority:** The server will be authoritative over all game state. Clients may submit actions and display state received from the server, but they will not independently modify official scores, advance rounds, select the next question, or determine the winner.

### 3.2 State & Score Synchronization Across Clients

- **Round Mechanics:** TriviaNet does not use alternating player turns. Instead, each round operates in lockstep. The server broadcasts the same `SEND_QUESTION` message to both players, and each player independently responds with one `SEND_ANSWER`.

- **Answer Validation:** Before accepting an answer, the server will verify that the client is a registered player, the game is currently accepting answers, the supplied `question_number` matches the active question, the answer is between 1 and 4, and the player has not already submitted an answer for that round. Invalid requests will not modify game state and will generate an appropriate `ERROR`, such as `OUT_OF_TURN`, `INVALID_ANSWER`, `DUPLICATE_ANSWER`, or `STALE_QUESTION`.

- **Waiting for Both Players:** When the first valid answer is received, the server will store that answer and return to the selector event loop rather than blocking while waiting for the second player. The round will not be evaluated until both players have submitted valid answers.

- **Score Synchronization:** Once both answers have been received, the server will compare them with the correct answer and update the scores. Each player will receive one point for a correct response. The server will then construct an authoritative `STATE_UPDATE` containing the completed question number, correct answer, both cumulative scores, and sudden-death status.

- **State Broadcast:** The same completed game-state snapshot will be used to queue a `STATE_UPDATE` for both clients before the server advances to the next game-state transition. The individual TCP writes may occur at slightly different times, but both clients will receive state derived from the same server-side update.

- **Round Progression:** After broadcasting the results, the server will reset the submitted-answer state and send the next `SEND_QUESTION`. This process will repeat for the predetermined number of normal rounds.

- **Win and Sudden-Death Handling:** At the end of the normal rounds, the server will compare the scores. If one player has the higher score, the server will broadcast `GAME_OVER` identifying the winner and final scores. If the scores are tied, the game will enter sudden death. Additional synchronized questions will be sent until exactly one player answers correctly while the other answers incorrectly. The server will then send `GAME_OVER` with the final result.

- **Disconnect Handling:** A client may intentionally leave using `DISCONNECT`, or the server may detect a lost connection through TCP EOF or a socket exception. If a player disconnects while waiting in the lobby, the lobby state will be reset. If a player disconnects during an active match, the remaining player will win by forfeit and will receive a `GAME_OVER` message with the appropriate final state.

### 3.3 Sprint 2 Design Deliverables

Sprint 2 will produce a server concurrency and state-synchronization architecture document describing the selector-based connection lifecycle, non-blocking socket behavior, shared game state, race-condition prevention strategy, answer validation, score synchronization, and connection cleanup.

The design will also include a Mermaid sequenceDiagram showing the interaction between both clients and the authoritative server. The diagram will document question broadcast, valid and invalid SEND_ANSWER requests, server-side validation, score updates, STATE_UPDATE broadcasts, and game completion or sudden-death transitions.

These designs will serve as the implementation blueprint for Sprint 3 so that the client and server code remain consistent with the application-layer protocol and game-state behavior defined in the earlier sprints.

--- 

## 4. Coding & AI Implementation Plan (Sprint 3)

### 4.1 Client Implementation

The Sprint 3 client is implemented in `client.py`. It uses `argparse` for the required `-i` server hostname and `-p` port arguments and validates that the selected port is between 1024 and 65535. The client resolves the configured server name using `socket.gethostbyname()` and catches `socket.gaierror` so DNS failures produce a clear error message rather than a traceback.

After connecting, the client prompts for a player alias and sends a protocol-compliant `CONNECT` message. It then processes `LOBBY_WAIT`, `GAME_START`, `SEND_QUESTION`, `STATE_UPDATE`, `ERROR`, and `GAME_OVER` messages. Questions and score summaries are displayed in a human-readable terminal interface. Client answers are sent using `SEND_ANSWER` with the active `question_number`.

### 4.2 Server Implementation

The Sprint 3 server is implemented in `server.py`. It parses the required `-p` argument, validates the port, binds to `0.0.0.0`, and uses `selectors.DefaultSelector` with non-blocking client sockets as specified in Sprint 2.

Each client connection maintains independent input and output buffers. Incoming TCP data is accumulated until a complete 4-byte big-endian length header and the corresponding UTF-8 JSON payload are available. Outgoing framed messages are queued and drained through selector write events so one slow client does not block the other.

The server implements the Sprint 1 FSM and remains authoritative over aliases, question progression, submitted answers, scores, sudden death, disconnects, and final results. Invalid, stale, duplicate, and out-of-turn messages return protocol-defined `ERROR` responses without corrupting game state.

### 4.3 Testing Plan and Results

Sprint 3 testing is performed locally using `localhost` before CML deployment. Testing includes:

- CLI help and required argument handling for both applications.
- Port validation for the range 1024-65535.
- Successful DNS resolution using `localhost`.
- Graceful `socket.gaierror` handling with an invalid hostname.
- Two simultaneous clients completing at least three trivia rounds.
- Synchronized `STATE_UPDATE` score broadcasts to both clients.
- Sudden-death transition and winner resolution after a tied normal game.
- Mid-game disconnect handling and `GAME_OVER` with `end_reason="FORFEIT"`.

The successful three-round localhost run is recorded in `demo_execution_log.txt`.

### 4.4 AI Use and Verification

ChatGPT was used to help translate the existing Sprint 1 protocol/FSM and Sprint 2 concurrency design into an initial Python implementation. The generated code was constrained to the documented message schemas and framing rules. The implementation was then compiled and exercised through local integration tests, including normal gameplay, sudden death, disconnect/forfeit handling, CLI validation, and DNS failure handling. AI usage details are recorded in `ai_use_report.md`.


--- 

## 5. CML Multi-Subnet Topology & Wireshark Deployment Plan (Sprint 4 & 5 Deliverable) *To be completed during Sprints 4 and 5.*