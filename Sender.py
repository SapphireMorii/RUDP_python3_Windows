import sys
import socket
import getopt
import base64

import Checksum
import BasicSender

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
class Sender(BasicSender.BasicSender):
    def __init__(self, dest, port, filename, debug=False, sackMode=False,timeout=0.5):
        super(Sender, self).__init__(dest, port, filename, debug)
        self.base = 0
        self.win = 5
        self.ack = 0
        self.next_seqno = 0
        self.packets = []
        self.debug = debug
        self.timeout = timeout
        self.sackMode = sackMode
        self.acks = []
        #if sackMode:
        #   raise NotImplementedError #remove this line when you implement SACK

    def handle_response(self,response_packet):
        if not Checksum.validate_checksum(response_packet):
            print("recv: %s <--- CHECKSUM FAILED" % response_packet)
            return 
        pieces = response_packet.split('|')
        ack_type, ackno = pieces[0:2]
        if(ack_type == 'ack'):
            self.ack = int(ackno)
            if(self.debug):
                print("Sender.py: received ack|%d|"%(self.ack))
        elif(ack_type == 'sack' and self.sackMode):
            sack_pieces = ackno.split(';')
            self.ack = int(sack_pieces[0])
            sacks = sack_pieces[1].split(',')
            if(sacks[0]!=''):
                for i in sacks:
                    self.acks[int(i)] = 1
        
        if(self.ack > self.base):
            self.handle_new_ack(self.ack)

    # Main sending loop.
    def start(self):
        #raise NotImplementedError
        seqno = 0
        msg = self.infile.read(500)
        msg_type = None
        while not msg_type == 'end':
            next_msg = self.infile.read(500)
            msg_type = 'data'
            if seqno == 0:
                msg_type = 'start'
            elif next_msg == b"":
                msg_type = 'end'

            msg = str(base64.b64encode(msg),'utf-8')
            packet = self.make_packet(msg_type,seqno,msg)
            self.packets.append(packet)

            msg = next_msg
            seqno += 1

        self.infile.close()

        packets_length = len(self.packets)
        self.acks = [0] * packets_length

        while(self.ack < packets_length):
            if(self.sackMode):
                while(self.next_seqno < min(self.base+self.win,packets_length)):
                    if(self.acks[self.next_seqno]==0):
                        self.send(self.packets[self.next_seqno])
                        if(self.debug):
                            print("Sender.py: send ack|%d|"%(self.next_seqno))
                    self.next_seqno += 1
            else:
                while(self.next_seqno < min(self.base+self.win,packets_length)):
                    self.send(self.packets[self.next_seqno])
                    if(self.debug):
                            print("Sender.py: send ack|%d|"%(self.next_seqno))
                    self.next_seqno += 1

            response = self.receive(self.timeout)

            while(response!=None):
                response = response.decode()
                self.handle_response(response)
                response = self.receive(self.timeout)
            
            self.handle_timeout()

    def handle_timeout(self):
        self.next_seqno = self.ack

    def handle_new_ack(self, ack):
        self.base = ack
        self.next_seqno = ack
        if(self.base+self.win<=len(self.acks)):
            self.send(self.packets[self.base+self.win-1])
            if(self.debug):
                print("Sender.py: send ack|%d| from new_ack"%(self.base+self.win-1))
        if(self.sackMode):
            for i in range(self.base,min(self.base+self.win,len(self.acks))):
                if(self.acks[i]==0):
                    self.next_seqno = i
                    break

    def handle_dup_ack(self, ack):
        pass

    def log(self, msg):
        if self.debug:
            print(msg)


'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print("RUDP Sender")
        print("-f FILE | --file=FILE The file to transfer; if empty reads from STDIN")
        print("-p PORT | --port=PORT The destination port, defaults to 33122")
        print("-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost")
        print("-d | --debug Print debug messages")
        print("-h | --help Print this usage message")
        print("-k | --sack Enable selective acknowledgement mode")

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False
    sackMode = False
    timeout = 0.5

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True
        elif o in ("-k", "--sack="):
            sackMode = True

    s = Sender(dest, port, filename, debug, sackMode, timeout)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
