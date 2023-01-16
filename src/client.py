#imports
import socket
from threading import Thread
import json
import ipaddress
import sys

debug = False

BUFFER_SIZE = 1024
SUBNETMASK = '255.255.255.0'

global name
server_ip = ''

#-------------------- Util Functions --------------------------
def encode_message(message):
    return str.encode(json.dumps(message))

def decode_message(message):
    return json.loads(message)

def get_broadcast_IP():
    ip = get_host_IP()
    network_adress = ipaddress.IPv4Network(ip + '/' + SUBNETMASK, False)
    broadcast_IP = network_adress.broadcast_address.exploded
    return broadcast_IP

def get_host_IP():
    host_list = socket.gethostbyname_ex(socket.gethostname())
    if len(host_list[2]) > 1:
        host_ip = host_list[2][1]
    else:
        host_ip = host_list[2][0]
    return host_ip
#------------------- End of Util Functions -------------------

class MessageSender():
    def __init__(self):
        self.bcip = get_broadcast_IP()
        self.bcport = 59070

        # create a UDP socket
        self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def broadcast(self, ip, port, message):
        # send message on broadcast address
        self.broadcast_socket.sendto(encode_message(message), (ip, port))

    def terminate(self):
        self.broadcast_socket.close()

def send_initial_broadcast():
    global broadcast_sender
    communication0 = {
        'cmd': 'CHAT',
        'uuid': None,
        'msg': ip,
        'name': name,
        'message': 'initial message'
    }
    broadcast_sender.broadcast(broadcast_sender.bcip, broadcast_sender.bcport, communication0)

class TCPMessageListener(Thread):
    def __init__(self, listening_port):
        Thread.__init__(self)
        self.listening_port = listening_port
        self.hostname = socket.gethostname()
        self.ip_address = get_host_IP()
        self.running = True

    def terminate(self):
        self.running = False

    def run(self):
        # create TCP socket
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
        s.bind(('', self.listening_port))
        if debug: print('TCP Unicast Listener running')
        while self.running:
            s.listen(5)
            conn, addr = s.accept()
            if debug: print('TCP connection addr: ', addr)
            try:
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    break

                msg = {
                    'cmd': 'SUCCESS',
                    'uuid': None,
                    'msg': self.ip_address
                }
                conn.sendall(encode_message(msg))
                received = decode_message(data)
                name = received['name']
                message = received['message']
                global server_ip
                server_ip = received['msg']
                print(name,': ',message)
                if received['message2']:
                    print(name, ': ', received['message2'])

                if debug: print('TCP was successful. Message: ', decode_message(data))
            except:
                pass
                #print('Error while receiving messages')      

        print('Server disconnected')


class TCPMessageSender(Thread):
    def __init__(self, recipient_IP, msg, name):
        Thread.__init__(self)
        self.uport = 59076
        self.recipient_IP = recipient_IP
        self.hostname = socket.gethostname()
        self.ip_address = get_host_IP()
        self.msg = msg
        self.name = name

        self. send_message(self.recipient_IP, self.uport, self.msg)

    def send_message(self, recipient_IP, uport, message):
        failed = False
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect_ex((recipient_IP, uport))
            s.sendall(encode_message(message))
            data = s.recv(BUFFER_SIZE)
            s.settimeout(None)
            
            if debug: print('TCP Unicast successful', message)
        except socket.error or Exception:
            print('Lost connection to server. trying to find new server...')
            failed = True
        finally:
            s.close()

        if failed:
            send_initial_broadcast()
            print('If you dont see a message that you have joined, please restart.')

if __name__ == '__main__':
    try:
        name = input("Nickname: ")
        ip = get_host_IP()
        listener = TCPMessageListener(59076)
        listener.start()
        broadcast_sender = MessageSender()

        send_initial_broadcast()
        
        while True:
            message = input('')
            communication = {
                'cmd': 'CHAT',
                'uuid': None,
                'msg': ip,
                'name': name,
                'message': message
            }
            if server_ip != '':
                TCPMessageSender(server_ip, communication, name)
            else:
                print('Missing server')
            pass

    except KeyboardInterrupt:
        sys.exit(0)