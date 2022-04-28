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

### Scenario A (simple communication):
1. The client sends a request [GET] to the server. The sequence number of this packet is 1.
2. The data section (ASCII payload) of this packet contains the name of a resource (e.g. file.txt).
3. The server receives [GET] message, then transmits the requested resource to the client over(possibly) multiple [DAT] packets. Remember, RUSHB protocol is a HTTP-like stop-and-wait protocol. The first packet from the server has a sequence number of 1.
4. The client acknowledges by sending an [DAT/ACK] packet to each received data packet. TheAcknowledgement Number of each packet is the Sequence Number of the packet beingacknowledged.
5. After receiving the last acknowledgement [DAT/ACK] from the client, the server sends [FIN]message to end the connection.
6. The client receives [FIN] message from the server, then sends back [FIN/ACK] to the server.
7. After receiving the last acknowledgement [FIN/ACK] from the client, the server send[FIN/ACK] again to the client and close the connection.

For all the packets with [DAT] flag is set to 0, the payload must be filled with all 0s bit only. Please note that it is just a simple example of RUSHB protocol; the server also needs to deal with optimised data flow control and multiple clients (that will be described later).

RUSHB server is capable of checksum. During the initial [GET], clients can negotiate requests for checksum. This is done using [CHK] for checksum in the very first [GET] packet. The first [DAT] from the server will indicate if negotiation was successful by setting the corresponding [CHK] flag. Once negotiated, these options are valid for all packets until close the connection with that client. [ENC] is encryption flag. In this assignment, you do not have to implement [ENC], thus this flag can be left as 0.

RUSHB checksum uses the standard Internet checksum on the payload only. As per the RFC, the checksum field is the 16-bit one's complement of the one's complement addition of all 16-bit words of the payload (see example below). Once [CHK] is negotiated, all packets that have invalid checksums are considered corrupt.
