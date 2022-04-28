# UDP-Server
UDP server base on Socketserver(Python)
## Simulation
Each process (a running instance) of RUSHB server will simulate file storage server. When your server receives a client's file request, it should locate the requested file in its local working directory and return the file contents over one or more packets. When complete, the server should close the connection with the guest that have sent the file. Your server also needs to be capable of simultaneously dealing with multiple clients. The server should try its best on improving the flow-control and guaranteeing the clients to get all the content reliably and uncorrupted by using the company's selected protocol, RUSHB (Reliable UDP Substitute for HTTP Beta).
## RUSHB Structure
The RUSHB protocol is a HTTP-like stop-and-wait protocol that uses UDP in conjunction with some idea of the RDT (Reliable Data Transfer) protocols. It is expected that the RUSHB protocol is able to handle packet corruption and loss.

A RUSHB packet can be expressed as the following structure (|| is concatenation):
<center> IP HEADER || UDP HEADER || RUSHB HEADER || ASCII PAYLOAD </center>

The data segment of the packet is a string of ASCII plaintext. A single RUSHB packet must be no longer than 1500 bytes, including the IP and UDP headers (i.e. the maximum length of the data section, or the concatenation of RUSHB HEADER and ASCII PAYLOAD, is 1472 bytes). Any packets smaller than 1500 bytes need to be padded with 0 bits up to that size. In detail, Figure 2 describes the header structure of a RUSHB packet.

![image](https://user-images.githubusercontent.com/91719529/165701228-f2f75ec2-8779-4fdd-b8cc-78eae620b866.png)

A client and server independently maintain sequence numbers. The first packet sent by either endpoint (a client and server) should have a sequence number of 1, and subsequent packets should have a sequence number of 1 higher than the previous packet (note that unlike TCP, RUSHB sequence numbers are based on the number of packets as opposed to the number of bytes).

When the ACK flag (see Figure 3: Flags structure) is set, the acknowledgement number should contain the sequence number of the packet that is being acknowledged. When a packet is retransmitted, it should use the original sequence number of the packet being retransmitted. Packet that is not retransmission (including NAKs) should increment the sequence number. The Flags Header is broken down in Figure 3.
![image](https://user-images.githubusercontent.com/91719529/165701206-79a60cd1-412a-4a6b-825e-9186257fb956.png)

The following scenario describes a simple RUSHB communication session. The square brackets denote the flags set in each step (e.g., [FIN/ACK] denotes the FIN and ACK flags having the value 1 and the rest having the value 0). Note that RUSHB, unlike TCP, is not connection-oriented. There is no handshake to initialise the connection, but there is one to close the connection.
