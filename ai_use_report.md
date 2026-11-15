# Sprint 1

When starting Sprint 1, I used ChatGPT to help me break down the assignment into more manageable chunks. As I worked through each part, I would often give it my work and have it give me feedback on how to improve it or point out things I may be missing. When I finished the protocol blueprint, I was curious to see how well it could build an FSM for me from my outlined protocols, and it was able to generate one for me pretty effectively, though it made me realize some edge cases I had not considered.

When I finished all three Markdown files for Sprint 1, I had a kind of cheeky idea that I wanted to try. I currently have a paid subscription to ChatGPT, and I have a free subscription to Gemini. I basically gave all my files, the assignment, and the rubric to ChatGPT and Gemini, asking both for feedback on what to add or change. After reading the feedback, I would update my project files, mostly manually, but I want to be transparent that some specific lines are ripped wholecloth from their suggestions.

I did this a couple of times, and then I finally had the idea to basically ask: **"How could I best format this information to be used by an AI model?"** That led to a pretty massive restructuring of the files, and I kind of flipped from having AI review my work to reviewing the AI's work to make sure it all checked out and fit with the original vision for the game.

Finally, I had ChatGPT reformat this to look prettier in Markdown.

# Sprint 3

For Sprint 3, I used ChatGPT to help implement the Python client and server from the protocol, FSM, and selector concurrency documents I had already created in earlier sprints. I supplied the Sprint 3 assignment and my existing project files and asked it to keep the implementation consistent with those specifications rather than inventing a new protocol.

ChatGPT produced an initial implementation of `client.py` and `server.py`. I reviewed the code against the required message schemas, 4-byte big-endian framing, selector architecture, and FSM behavior. I then tested the implementation locally with two clients. The tests included a normal three-round game, a tied game that entered sudden death, a disconnect that produced a forfeit, command-line help and port validation, and a failed DNS lookup to confirm that `socket.gaierror` is handled without a traceback.

I also used ChatGPT to help create the Sprint 3 README and execution-log documentation.

