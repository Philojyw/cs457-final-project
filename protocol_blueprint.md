#### 1. Message Types & Structured Schema Definitions

### CONNECT

**Direction:** Client -> Server

**Purpose:** Client requests to join game room with player alias.

| Field | Type | Required | Description |
|---|---|---|---|
| message_type | string | Yes | Allows server to identify the category of message it is receiving, message_type must be exactly "CONNECT". |
| user_alias | string | Yes | Supplies the identifier the client wants to use for game. Field cannot be empty, and cannot exceed 16 characters. |

**Example Payload**

```json
{
  "message_type": "CONNECT",
  "user_alias": "GRRM#1_FAN"
}
```
### LOBBY_WAIT

**Direction:** Server -> Client

**Purpose:** Server notifies Client 1 that it is waiting for Player 2 to connect.

| Field | Type | Required | Description |
|---|---|---|---|
| message_type | string | Yes | Allows client to identify the category of message it is receiving, message_type must be exactly "LOBBY_WAIT". |

**Example Payload**

```json
{
  "message_type": "LOBBY_WAIT"
}
```
### GAME_START

**Direction:** Server -> Client

**Purpose:** Server notifies both clients that game has started and assigns roles (Player 1 / Player 2).

| Field | Type | Required | Description |
|---|---|---|---|
| message_type | string | Yes | Allows client to identify the category of message it is receiving, message_type must be exactly "GAME_START". |
| opponent_alias | string | Yes | Supplies the identifier the opponent has chosen for the game.|
| role | bool | Yes | Assigns client as player 1 (True) or player 2 (False). Role of opponent is inferred from role of client, since only 2 players is possible. |

**Example Payload**

```json
{
  "message_type": "GAME_START",
  "opponent_alias": "Sweet Robin",
  "role": true
}
```
### SEND_QUESTION

**Direction:** Server -> Client

**Purpose:** Server sends the trivia question to both clients.

| Field | Type | Required | Description |
|---|---|---|---|
| message_type | string | Yes | Allows client to identify the category of message it is receiving, message_type must be exactly "SEND_QUESTION". |
| question | string | Yes | Supplies the client the question to be answered.|
| option1 | string | Yes | Supplies the client a choice for answer.|
| option2 | string | Yes | Supplies the client a choice for answer.|
| option3 | string | Yes | Supplies the client a choice for answer.|
| option4 | string | Yes | Supplies the client a choice for answer.|
| question_number | int | Yes | Sends the sequence number for question. This is used to pair questions with answers and handle repeat submissions. |

**Example Payload**

```json
{
  "message_type": "SEND_QUESTION",
  "question": "What major reveal about Tyrion's past was changed in from the book in season 5?",
  "option1": "He actually isn't a dwarf.",
  "option2": "His mother did not die during childbirth.",
  "option3": "He is the prince who was promised.",
  "option4": "His first love was not actually a prostitute.",
  "question_number": 4
}
```
### SEND_ANSWER

**Direction:** Client -> Server

**Purpose:** Client submits answer to trivia question.

| Field | Type | Required | Description |
|---|---|---|---|
| message_type | string | Yes | Allows the server to identify the category of message it is receiving, message_type must be exactly "SEND_QUESTION". |
| answer | int | Yes | Supplies the server with the clients answer. Answer must be a value from 1-4. |
| question_number | int | Yes | Supplies the server the identifier to pair an answer to a given question. |

**Example Payload**

```json
{
  "message_type": "SEND_ANSWER",
  "answer": 2,
  "question_number": 4
}
```
### STATE_UPDATE

**Direction:** Server -> Client

**Purpose:** Server broadcasts answer results, updated scores, or the transition into sudden death..

| Field | Type | Required | Description |
|---|---|---|---|
| message_type | string | Yes | Allows client to identify the category of message it is receiving, message_type must be exactly "STATE_UPDATE". |
| client_one_score | int | Yes | Supplies the client with the new total for client one's score.|
| client_two_score | int | Yes | Supplies the client with the new total for client two's score. |
| correct_answer | string | Yes | Supplies the client with the correct answer for the previous question. |
| is_sudden_death | bool | Yes | Supplies the client with a boolean to tell if sudden death is being entered. |
| question_number | int | Yes | Allows the client to pair an answer to a given question. |

**Example Payload**

```json
{
  "message_type": "STATE_UPDATE",
  "client_one_score": 3,
  "client_two_score": 5,
  "correct_answer": "His first love was not actually a prostitute.",
  "is_sudden_death": false,
  "question_number": 4
}
```
### ERROR

**Direction:** Server -> Client

**Purpose:** Server notifies a client that a submitted message or action was invalid and could not be processed.

| Field | Type | Required | Description |
|---|---|---|---|
| message_type | string | Yes | Allows client to identify the category of message it is receiving. message_type must be exactly "ERROR". |
| error_code | string | Yes | Identifies the type of error that occurred. Valid values include "INVALID_ANSWER", "DUPLICATE_ANSWER", and "MALFORMED_MESSAGE". |
| error_message | string | Yes | Provides a description of the error for the client. |

**Example Payload**

```json
{
  "message_type": "ERROR",
  "error_code": "DUPLICATE_ANSWER",
  "error_message": "An answer has already been submitted for this question."
}
```
### DISCONNECT

**Direction:** Client -> Server

**Purpose:** Client notifies the server that the player is intentionally leaving the game.

| Field | Type | Required | Description |
|---|---|---|---|
| message_type | string | Yes | Allows server to identify the category of message it is receiving. message_type must be exactly "DISCONNECT". |

**Example Payload**

```json
{
  "message_type": "DISCONNECT"
}
```
### GAME_OVER

**Direction:** Server -> Clients

**Purpose:** Server notifies connected clients that the game has ended and provides the winner, final scores, and reason the game ended.

| Field | Type | Required | Description |
|---|---|---|---|
| message_type | string | Yes | Allows client to identify the category of message it is receiving. message_type must be exactly "GAME_OVER". |
| winner_alias | string | Yes | Supplies the alias of the player who won the game. |
| client_one_score | int | Yes | Supplies the final score for Client 1. |
| client_two_score | int | Yes | Supplies the final score for Client 2. |
| end_reason | string | Yes | Identifies how the game ended. Valid values are "NORMAL", "SUDDEN_DEATH", or "FORFEIT". |

**Example Payload**

```json
{
  "message_type": "GAME_OVER",
  "winner_alias": "GRRM#1_FAN",
  "client_one_score": 7,
  "client_two_score": 5,
  "end_reason": "NORMAL"
}
```

#### 2. TCP Stream Packet Framing & Boundary Handling

**Packet framing choice and receiver logic explanation**: 

I am using length-prefixed framing. Basically, when using length-prefixing every message sent has a 4 byte header that tells the receiver “this payload will be exactly the size specified in the header, don’t try to parse the data from this message until you received the full message”. This is needed because a single recv() may not get a full payload, or may receive past a payload into the next payloads header. The 4 byte header must be in Network byte order, which is big endian order, regardless of whether the client or server machines use little or big endian. It is important that if recv() returns b"", even if it hasn't finished parsing the full packet, it ends the connection rather than continuing to wait for more data.

To achieve this, the sender must take the message dictionary and turn that into a JSON payload. It then encodes that payload at UTF-8 bytes, measure how many bytes that is, and convert that to length into a 4 byte big endian header. It then sends the header and the converted payload.

The receiver starts by reading until it has exactly 4 bytes, so that it is sure it receives the full header. It decodes the header to get the length of the payload, and then keeps reading in bytes until it has received exactly the amount of info specified by the header. It then decodes the payload as UTF-8 bytes and then parses the JSON.

**Raw wire-stream example**:

[00 00 00 37]{"message_type": "CONNECT", "user_alias": "GRRM#1_FAN"}[00 00 00 38]{"message_type": "CONNECT", "user_alias": "Sweet Robin"}

#### 3. Connection Termination & Socket Lifecycle Management

**Graceful Disconnect**:

A graceful disconnect occurs when a clients chooses to intentionally leave the game, the client will send a DISCONNECT message to the server. This is how the server will distinguish an intentional disconnect from from a disconnect caused by some unexpected issue. 

When the server receives a DISCONNECT message, it will identify the leaving player and update the state accordingly. If the leaving player were the only player in a waiting lobby, the state will be updated to EMPTY_LOBBY. If the disconnect happened during the game, a GAME_OVER message will be sent to the remaining player declaring them the winner, with the end reason being "forfeit".

The server and client will then close the socket normally, leading to TCP initiating its 4-way FIN handshake.

**TCP EOF / Clean Closure**:

A clean TCP closure can occur when the remote client closes its socket normally. When this happens, a recv() call returns 0 bytes (b"" in Python), which indicates EOF. The server must check for this condition while reading both the 4-byte length header and the JSON payload. If EOF is detected before the expected data has been fully received, the incomplete message is discarded and the server stops waiting for additional bytes.

The server then treats the client as disconnected, updates the game state, closes the associated socket, and begins the appropriate cleanup or forfeit handling. Checking for EOF is necessary to prevent the server from repeatedly calling recv() on a connection that has already been closed.

**Abrupt Connection Failure**:

An abrupt connection failure occurs when the TCP connection is lost unexpectedly, such as when a client crashes, a process is forcefully terminated, or a network connection fails. Unlike a graceful disconnect, the client may not have the opportunity to send a DISCONNECT message before the connection is lost.

The server must catch socket-related exceptions instead of allowing them to crash the game server. A ConnectionResetError can occur when the connection is forcibly reset by the remote system, while a BrokenPipeError can occur when the server attempts to send data through a socket whose remote endpoint is no longer available. When one of these errors occurs, the server treats the affected player as disconnected and begins the same game-state cleanup used for other unexpected disconnects.

**Game-Level Disconnect Handling**:

If either player disconnects while a game is active, the server identifies which player lost the connection and declares the remaining connected player the winner by forfeit. If the remaining player's connection is still available, the server sends that client a GAME_OVER message with an end_reason of "FORFEIT".

The server does not attempt to continue sending messages to the disconnected player's socket. After notifying the remaining player, the server closes any remaining sockets associated with the game and clears the current game state so that resources can be released and the server can prepare for a future game.