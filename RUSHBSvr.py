import multiprocessing
import os.path
import socketserver
import time
from multiprocessing import Process, Manager

LOCALHOST = "127.0.0.1"
PORT = 0
PACKET_SIZE = 1472
PAYLOAD_SIZE = 1464

cli_seq = 1
ser_seq = 0
cke_flag = 0

file = 0
file_words = 0
con_num = 0
buffer = 0

pro = None

processes = Manager().dict()
SERVER = 0


def bit_to_list(t, n):
    s = [0 for i in range(n)]
    i = -1
    while t != 0:
        s[i] = t % 2
        t = t >> 1
        i -= 1
    return s


def carry_around_add(a, b):
    c = a + b
    return (c & 0xffff) + (c >> 16)


def compute_checksum(message):
    b_str = message
    if len(b_str) % 2 == 1:
        b_str += b'\0'
    checksum = 0
    for i in range(0, len(b_str), 2):
        w = b_str[i] + (b_str[i + 1] << 8)
        checksum = carry_around_add(checksum, w)
    return ~checksum & 0xffff


def packet(seq_num, ack_num, che_num, flags, payload):
    seq_num = seq_num.to_bytes(2, byteorder="big")
    ack_num = ack_num.to_bytes(2, byteorder="big")
    che_num = che_num.to_bytes(2, byteorder="big")
    flags = int(flags + "0", 2).to_bytes(1, byteorder="big")
    res_ver = (2).to_bytes(1, byteorder="big")
    return seq_num + ack_num + che_num + flags + res_ver + payload


class MyUDPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        global cli_seq, ser_seq, file_words, file, con_num, buffer, pro, cke_flag

        def timeout():
            while 1:
                time.sleep(4)
                socket.sendto(buffer, self.client_address)

        data = self.request[0].strip()
        socket = self.request[1]
        seq_num = int.from_bytes(data[0:2], byteorder='big')
        ack_num = int.from_bytes(data[2:4], byteorder='big')
        che_num = int.from_bytes(data[4:6], byteorder='big')
        flags = bit_to_list(data[6], 8)[:7]
        flags_str = "".join(map(str, flags))
        payload = bytes.decode(data[8:].rstrip(chr(0).encode()))

        if (flags_str == "0010010" or flags_str == "0010000"):
            if flags[5] == 1:
                cke_flag = 1
            else:
                cke_flag = 0
        if cke_flag == 1:
            if che_num == compute_checksum(data[8:]):
                if flags_str == "0010010" and seq_num == 1 and ack_num == 0:
                    cli_seq += 1
                    if pro is not None:
                        pro.terminate()
                    path = payload
                    content = ""
                    # If the file does exist.
                    if os.path.exists(path):
                        with open(path, "r") as file:
                            for line in file:
                                content += line
                        file = content.encode()
                        file_words = len(content)
                        ser_seq = ser_seq + 1
                        pad = 0
                        if file_words >= PAYLOAD_SIZE:
                            pad = file[:PAYLOAD_SIZE]
                            con_num = con_num + PAYLOAD_SIZE
                            file_words = file_words - PAYLOAD_SIZE
                        elif file_words < PAYLOAD_SIZE:
                            con_num = con_num + PAYLOAD_SIZE
                            pad = file[:file_words] + (0).to_bytes(
                                PAYLOAD_SIZE - file_words, byteorder="big")
                            file_words = 0
                        dat = packet(ser_seq, 0, compute_checksum(pad),
                                     "0001010", pad)
                        socket.sendto(dat, self.client_address)
                        buffer = dat
                        pro = Process(target=timeout)
                        pro.start()

                    # If the file does not exist, closes the connection.
                    else:
                        ser_seq = ser_seq + 1
                        pad = (0).to_bytes(PAYLOAD_SIZE, byteorder="big")
                        fin = packet(ser_seq, 0, compute_checksum(pad),
                                     "0000110", pad)
                        socket.sendto(fin, self.client_address)
                        buffer = fin
                        pro = Process(target=timeout)
                        pro.start()

                elif flags_str == "1001010" and ack_num == ser_seq \
                        and seq_num == cli_seq and file_words > 0:
                    cli_seq += 1
                    if pro is not None:
                        pro.terminate()
                    ser_seq = ser_seq + 1
                    pad = 0
                    if file_words >= PAYLOAD_SIZE:
                        pad = file[con_num:con_num + PAYLOAD_SIZE]
                        con_num = con_num + PAYLOAD_SIZE
                        file_words = file_words - PAYLOAD_SIZE
                    elif file_words < PAYLOAD_SIZE:
                        pad = file[con_num: con_num + file_words] + \
                              (0).to_bytes(PAYLOAD_SIZE - file_words,
                                           byteorder="big")
                        con_num = con_num + file_words
                        file_words = 0
                    dat = packet(ser_seq, 0, compute_checksum(pad), "0001010",
                                 pad)
                    socket.sendto(dat, self.client_address)
                    buffer = dat
                    pro = Process(target=timeout)
                    pro.start()
                # NAK
                elif (flags_str == "0101010" or flags_str == "0100110") \
                        and seq_num == cli_seq and ack_num == ser_seq:
                    cli_seq += 1
                    if pro is not None:
                        pro.terminate()
                    socket.sendto(buffer, self.client_address)
                    pro = Process(target=timeout)
                    pro.start()

                # FIN Determine whether the received ACK and the sent SEQ
                # are expected
                elif flags_str == "1001010" and ack_num == ser_seq \
                        and file_words == 0 and seq_num == cli_seq:
                    cli_seq += 1
                    if pro is not None:
                        pro.terminate()
                    ser_seq = ser_seq + 1
                    pad = (0).to_bytes(PAYLOAD_SIZE, byteorder="big")
                    fin = packet(ser_seq, 0, compute_checksum(pad), "0000110",
                                 pad)
                    socket.sendto(fin, self.client_address)
                    buffer = fin
                    pro = Process(target=timeout)
                    pro.start()
                # FIN/ACK
                elif flags_str == "1000110" and ack_num == ser_seq \
                        and seq_num == cli_seq:
                    cli_seq += 1
                    if pro is not None:
                        pro.terminate()
                    ser_seq = ser_seq + 1
                    pad = (0).to_bytes(PAYLOAD_SIZE, byteorder="big")
                    fin_ack = packet(ser_seq, seq_num, compute_checksum(pad),
                                     "1000110", pad)
                    socket.sendto(fin_ack, self.client_address)
                    buffer = fin_ack
                    # clear all
                    cli_seq = 1
                    ser_seq = 0
                    cke_flag = 0
                    file = 0
                    file_words = 0
                    con_num = 0
                    buffer = 0

        # Without check
        else:
            if cke_flag == 0:
                if flags_str == "0010000" and seq_num == 1 and ack_num == 0:
                    cli_seq += 1
                    if pro is not None:
                        pro.terminate()
                    path = payload
                    content = ""
                    # If the file does exist.
                    if os.path.exists(path):
                        with open(path, "r") as file:
                            for line in file:
                                content += line
                        file = content.encode()
                        file_words = len(content)
                        ser_seq = ser_seq + 1
                        pad = 0
                        if file_words >= PAYLOAD_SIZE:
                            pad = file[:PAYLOAD_SIZE]
                            con_num = con_num + PAYLOAD_SIZE
                            file_words = file_words - PAYLOAD_SIZE
                        elif file_words < PAYLOAD_SIZE:
                            con_num = con_num + PAYLOAD_SIZE
                            pad = file[:file_words] + (0).to_bytes(
                                PAYLOAD_SIZE - file_words, byteorder="big")
                            file_words = 0
                        dat = packet(ser_seq, 0, 0, "0001000", pad)
                        socket.sendto(dat, self.client_address)
                        buffer = dat
                        pro = Process(target=timeout)
                        pro.start()
                    # If the file does not exist, closes the connection.
                    else:
                        ser_seq = ser_seq + 1
                        pad = (0).to_bytes(PAYLOAD_SIZE, byteorder="big")
                        fin = packet(ser_seq, 0, 0, "0000100", pad)
                        socket.sendto(fin, self.client_address)
                        buffer = fin
                        pro = Process(target=timeout)
                        pro.start()

                elif flags_str == "1001000" and ack_num == ser_seq \
                        and file_words > 0 and seq_num == cli_seq:
                    cli_seq += 1
                    if pro is not None:
                        pro.terminate()
                    ser_seq = ser_seq + 1
                    pad = 0
                    if file_words >= PAYLOAD_SIZE:
                        pad = file[con_num:con_num + PAYLOAD_SIZE]
                        con_num = con_num + PAYLOAD_SIZE
                        file_words = file_words - PAYLOAD_SIZE
                    elif file_words < PAYLOAD_SIZE:
                        pad = file[con_num: con_num + file_words] + \
                              (0).to_bytes(PAYLOAD_SIZE - file_words,
                                           byteorder="big")
                        con_num = con_num + file_words
                        file_words = 0
                    dat = packet(ser_seq, 0, 0, "0001000", pad)
                    socket.sendto(dat, self.client_address)
                    buffer = dat
                    pro = Process(target=timeout)
                    pro.start()
                # NAK
                elif (flags_str == "0101000" or flags_str == "0100100") \
                        and seq_num == cli_seq and ack_num == ser_seq:
                    cli_seq += 1
                    if pro is not None:
                        pro.terminate()
                    socket.sendto(buffer, self.client_address)
                    pro = Process(target=timeout)
                    pro.start()

                # FIN Determine whether the received ACK and the sent SEQ
                # are expected
                elif flags_str == "1001000" and ack_num == ser_seq \
                        and file_words == 0 and seq_num == cli_seq:
                    cli_seq += 1
                    if pro is not None:
                        pro.terminate()
                    ser_seq = ser_seq + 1
                    pad = (0).to_bytes(PAYLOAD_SIZE, byteorder="big")
                    fin = packet(ser_seq, 0, 0, "0000100", pad)
                    socket.sendto(fin, self.client_address)
                    buffer = fin
                    pro = Process(target=timeout)
                    pro.start()
                # FIN/ACK
                elif flags_str == "1000100" and ack_num == ser_seq \
                        and seq_num == cli_seq:
                    cli_seq += 1
                    if pro is not None:
                        pro.terminate()
                    ser_seq = ser_seq + 1
                    pad = (0).to_bytes(PAYLOAD_SIZE, byteorder="big")
                    fin_ack = packet(ser_seq, seq_num, 0, "1000100", pad)
                    socket.sendto(fin_ack, self.client_address)
                    buffer = fin_ack

                    # clear all
                    cli_seq = 1
                    ser_seq = 0
                    cke_flag = 0
                    file = 0
                    file_words = 0
                    con_num = 0
                    buffer = 0


class MyUDPServer(socketserver.UDPServer):
    def finish_request(self, request, client_address):
        if client_address in processes:
            processes[client_address] = [request, client_address, 1]

        else:
            processes[client_address] = [request, client_address, 1]
            MyProcess(args=(client_address, )).start()


class MyProcess(multiprocessing.Process):
    def run(self):
        while 1:
            client_address = list(self._args)[0]
            args = processes[client_address]
            if args[2] == 1:
                processes[client_address] = [args[0], args[1], 0]
                SERVER.RequestHandlerClass(args[0], args[1], SERVER)


if __name__ == '__main__':
    with MyUDPServer((LOCALHOST, PORT), MyUDPHandler) as server:
        SERVER = server
        IP, port = server.server_address
        print(port, flush=True)
        server.serve_forever()
