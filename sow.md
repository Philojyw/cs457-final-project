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

## 3. Game Behavior & Server Concurrency Architecture (Sprint 2 Deliverable) *To be completed during Sprint 2.* 

--- 

## 4. Coding & AI Implementation Plan (Sprint 3) *To be completed during Sprint 3.* 

--- 

## 5. CML Multi-Subnet Topology & Wireshark Deployment Plan (Sprint 4 & 5 Deliverable) *To be completed during Sprints 4 and 5.*