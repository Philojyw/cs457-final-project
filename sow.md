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

## 2. Application-Layer Messaging Protocol Blueprint (Sprint 1 Deliverable) *To be completed during Sprint 1.* 

--- 

## 3. Game Behavior & Server Concurrency Architecture (Sprint 2 Deliverable) *To be completed during Sprint 2.* 

--- 

## 4. Coding & AI Implementation Plan (Sprint 3) *To be completed during Sprint 3.* 

--- 

## 5. CML Multi-Subnet Topology & Wireshark Deployment Plan (Sprint 4 & 5 Deliverable) *To be completed during Sprints 4 and 5.*