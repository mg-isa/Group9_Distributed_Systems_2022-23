# Group9_Distributed_Systems_2022-23
This repository hosts the code of a chat application that was programmed for the distributed systems course at the Herrman-Hollerith Zentrum in the winter semester of 2022/2023.

## Structure
The chat application follows a client-server architecture. Several servers can be started to ensure a server is running, if the first one crashes. The servers form a ring and send Heartbeats to their neighbours to ensure that the neighbours are still 'alive'. The server pool needs a leader, because only the leader interacts with the client. The leader is voted with the LCR algorithm. A new Voting round begins as soon as a new server joins or a leader crashes.

You will find two files in the 'src' folder:
- main.py
- client.py

<b>main.py</b> is the script for the server. If executed on several machines in the same network, these machines form the ring/server pool.

<b>client.py</b> is the scriept for the clients. If executed on several machines in the same network, every machine becomes a chat participant.

Keep in mind:
- All components have to be in the same network
- Every component needs to run on a different machine (physical or virtual)
