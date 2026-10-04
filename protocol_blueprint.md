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
  "role": True
}

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

### SEND_ANSWER

**Direction:** Client -> Server

**Purpose:** Client submits answer to trivia question.

| Field | Type | Required | Description |
|---|---|---|---|
| message_type | string | Yes | Allows client to identify the category of message it is receiving, message_type must be exactly "SEND_QUESTION". |
| answer | int | Yes | Supplies the server with the clients answer.|
| question_number | int | Yes | Supplies the server the identifier to pair an answer to a given question. |

**Example Payload**

```json
{
  "message_type": "SEND_ANSWER",
  "answer": "2",
  "question_number": 4
}

### STATE_UPDATE

**Direction:** Server -> Client

**Purpose:** Server broadcasts answer results, updated scores, or the transition into sudden death..

| Field | Type | Required | Description |
|---|---|---|---|
| message_type | string | Yes | Allows client to identify the category of message it is receiving, message_type must be exactly "STATE_UPDATE". |
| answer | int | Yes | Supplies the server with the clients answer.|
| question_number | int | Yes | Supplies the server the identifier to pair an answer to a given question. |

**Example Payload**

```json
{
  "message_type": "SEND_ANSWER",
  "answer": "2",
  "question_number": 4
}