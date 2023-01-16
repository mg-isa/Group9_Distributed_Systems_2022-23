# imports
import socket
from threading import Thread
import uuid
import sys
import ipaddress
import json
import time

debug = False

# list of servers available in a Tupel (ip, uuid)
servers = []
# list of connected clients
clients = []

BUFFER_SIZE = 1024
SUBNETMASK = '255.255.255.0'

UUID = uuid.uuid4()

global response
response = False

# information about leader
global I_am_leader 
I_am_leader = False
global leader 
leader = (None, None)

# ---------- Util Functions ----------
def get_broadcast_IP():
    ip = get_host_IP()
    network_adress = ipaddress.IPv4Network(ip + '/' + SUBNETMASK, False)
    broadcast_IP = network_adress.broadcast_address.exploded
    return broadcast_IP

def encode_message(message):
    return str.encode(json.dumps(message))

def decode_message(message):
    return json.loads(message)

def get_host_IP():
    host_list = socket.gethostbyname_ex(socket.gethostname())
    if len(host_list[2]) > 1:
        host_ip = host_list[2][1]
    else:
        host_ip = host_list[2][0]
    return host_ip

# find neighbours for heartbeat
def find_neighbour_right(ip_address):
    # sort list
    sorted_list = sorted(servers, key = lambda servers: servers[0])
    my_index = sorted_list.index((ip_address, str(UUID)))
    neighbour_right = sorted_list[(my_index + 1) % len(sorted_list)]
    #if debug: print('My right neighbour is: ', neighbour_right)
    return neighbour_right

def find_neighbour_left(ip_address):
    # sort list
    sorted_list = sorted(servers, key = lambda servers: servers[0])
    my_index = sorted_list.index((ip_address, str(UUID)))
    neighbour_left = sorted_list[(my_index - 1) % len(sorted_list)]
    #if debug: print('My left neighbour is: ', neighbour_left)
    return neighbour_left
#---------- End Util Functions ----------


#---------- Message Handler ----------
class MessageHandler():
    def __init__(self, data):
        self.msg = decode_message(data)
        self.command = self.msg['cmd']
        self.message = self.msg['msg']
        self.id = self.msg['uuid']
        self.my_ip = get_host_IP()
        self.my_ID = UUID
        global response
        global leader

        global servers
        global clients
        global broadcast_sender
        global client_sender

    # use command in message to initiate specific tasks
        if(self.command == 'INIT'):
            if debug: print('Command received: INIT')
            if self.message == self.my_ip:
                # pause to wait until right neighbour is found
                timeout = time.time() + 2
                while not response and time.time()<timeout:
                    pass
                else:
                    vote = Voting()
                    vote.initiate_voting()
                    print(servers)
                    response = False
                
            else:
                if self.message not in [server[0] for server in servers]:
                    servers.append((self.message, self.id))
                print('New server joined: ', self.message)
                self.msg = {
                    'cmd': 'INIT_RESPONSE',
                    'uuid': str(self.my_ID),
                    'msg': self.my_ip
                }
                TCPUnicastSender(self.my_ID, self.message, self.msg)

        elif(self.command == 'INIT_RESPONSE'):
            if debug: print('Received: INIT_RESPONSE')
            if self.message not in [server[0] for server in servers]:
                servers.append((self.message, self.id))
                response = True
                print('New server joined: ', self.message)

        elif(self.command == 'LOST_SERVER'):
            if debug: print('broadcast received')
            #if debug: print('Lost server: ', self.message)
            try:
                neighbour = find_neighbour_right(get_host_IP())
                servers.remove((self.message, self.id))
                print('Removed server from list: ', self.message)
                if debug: print('Leader: ', leader[0])
                if self.message == leader[0] and neighbour[0] == leader[0] :
                    if debug: print('Initiating voting')
                    vote = Voting()
                    vote.initiate_voting()
            except ValueError:
                if debug: print('Failed to remove lost server from list')

        elif(self.command == 'VOTE'):
            if debug: print(self.msg)
            vote2 = Voting()
            vote2.vote_algorithm(self.msg)

        elif(self.command == 'CHAT'):
            if debug: print('Command: CHAT')
            #print(self.msg)
            if I_am_leader:
                name = self.msg['name']
                ip = self.msg['msg']
                    
                if ip != self.my_ip:
                    if ip not in [client[0] for client in clients]:
                        clients.append((ip, name))
                        string = str('New participant has joined: ' + name)
                        participants = []
                        for client in clients:
                            participants.append(client[1])
                        participants = ', '.join(participants)
                        string2 = str('Currently in this chat: ' + participants)
                        new_message = {
                            'cmd': 'CHAT',
                            'uuid': None,
                            'msg': self.my_ip,
                            'name': 'Server',
                            'message': string,
                            'message2': string2
                        }
                        for client in clients:
                            TCPClientSender(client[0], new_message, client[1])
                        if debug: print(new_message['message'])

                        message_append = {
                            'cmd': 'CLIENT',
                            'uuid': None,
                            'msg': get_host_IP(),
                            'command': 'append',
                            'client_ip': ip,
                            'client_name': name
                        }
                        broadcast_sender.broadcast(broadcast_sender.bcip, broadcast_sender.bcport, message_append)

                    elif (self.msg['message'] == 'initial message'):
                        string = str('New participant has joined: ' + name)
                        participants = []
                        for client in clients:
                            participants.append(client[1])
                        participants = ', '.join(participants)
                        string2 = str('Currently in this chat: ' + participants)
                        new_message = {
                            'cmd': 'CHAT',
                            'uuid': None,
                            'msg': self.my_ip,
                            'name': 'Server',
                            'message': string,
                            'message2': string2
                        }
                        for client in clients:
                            TCPClientSender(client[0], new_message, client[1])

                    else:
                        self.msg['msg'] = get_host_IP()
                        for client in clients:
                            TCPClientSender(client[0], self.msg, client[1])
                        if debug: print(self.msg['message'])
                
                else:
                    for client in clients:
                        TCPClientSender(client[0], self.msg, client[1])
                        if debug: print(self.msg['message'])

        elif (self.command == 'CLIENT'):
            if self.message != self.my_ip:
                if self.msg['command'] == 'append':
                    if self.message not in [client[0] for client in clients]:
                        clients.append((self.msg['client_ip'], self.msg['client_name']))
                        #print(clients)
                elif self.msg['command'] == 'remove':
                    try:
                        clients.remove((self.msg['client_ip'], self.msg['client_name']))
                    except:
                        pass

        else:
            print('Unknown command: ', self.command)  


#---------- Message Handler End ----------

#---------- Broadcast Sender & Receiver ----------
#Broadcast Listener to listen to any incoming broadcast messages
class BroadcastListener(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.broadcast_port = 59070
        self.host_name = socket.gethostname()
        self.my_ip = get_host_IP()
        self.UUID = UUID

        # create a UDP socket
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # set the socket to broadcast and enable reusing addresses
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        #bind socket to address and port
        self.listen_socket.bind(('', self.broadcast_port))
        self.running = True

    def terminate(self):
        self.running = False

    # listener is receving data while it is running
    def run(self):
        while self.running:
            data, address = self.listen_socket.recvfrom(BUFFER_SIZE)
            # what to do with the data once it arrives
            if data:
                received = decode_message(data)
                message = received['msg']
                #print(message)
                MessageHandler(data)
                if debug: print('Broadcast received')

class BroadcastSender():
    def __init__(self):
        self.bcip = get_broadcast_IP()
        self.bcport = 59070

    def broadcast(self, ip, port, message):
        # create a UDP socket
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # send message on broadcast address
        broadcast_socket.sendto(encode_message(message), (ip, port))

def send_initial_broadcast():
    ip = get_host_IP()
    if ip not in [server[0] for server in servers]:
        servers.append((ip, str(UUID)))
    # creating UDP socket
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if debug: print('Sender socket was created')
    # sending message to broadcast address
    text = str(ip)
    message = {
        'cmd': 'INIT',
        'uuid':str(UUID),
        'msg': text
    }
    encoded_message = encode_message(message)
    broadcast_IP = get_broadcast_IP()
    broadcast_socket.sendto(encoded_message, (broadcast_IP, 59070))
    broadcast_socket.close()


#---------- Heartbeat ----------
# heartbeat listener listening for TCP messages from neighbour
class HeartbeatListener(Thread):
    def __init__(self, hearbeat_port, UUID):
        Thread.__init__(self)
        self.heartbeat_port = hearbeat_port #59073
        self.host = socket.gethostname()
        self.ip_address = get_host_IP()
        self.UUID = UUID
        if debug: print('Listening for Hearbeat at: ', self.ip_address, ' on port: ', self.heartbeat_port)
        self.running = True

    def terminate(self):
        self.running = False

    def run(self):
        #create a TCP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', self.heartbeat_port))
        # accepts 5 unaccepted connections
        s.listen(5)

        while self.running:
            conn, addr = s.accept()
            data = conn.recv(BUFFER_SIZE)

            if data:
                #message = decode_message(data)

                # let heartbeat sender know, that you're awake
                msg = {
                    'cmd': 'AWAKE',
                    'uuid': str(self.UUID),
                    'msg': self.ip_address
                }
                conn.sendall(encode_message(msg))
                #MessageHandler(data) #command: 'HEARTBEAT'

            else:
                print('No data received')

        conn.close()
        s.shutdown()

class HeartbeatSender(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.hsport = 59071
        self.UUID = UUID
        self.hostname = socket.gethostname()
        self.ip_address = get_host_IP()
        self.running = True
        self.counts_right = 0
        self.counts_left = 0
        global servers
        

        self.msg = {
            'cmd': 'HEARTBEAT',
            'uuid': str(self.UUID),
            'msg': self.ip_address
        }

    def terminate(self):
        self.running = False

    def run(self):
        # send heartbeats every second - there are only 2 servers or less they each only have 1 right neighbour
        while self.running:
            if len(servers) > 2:
                print('------------', len(servers), '----------------')
                self.send_message(find_neighbour_right(self.ip_address), self.hsport, self.msg, 'right')
                time.sleep(0.5)
                self.send_message(find_neighbour_left(self.ip_address), self.hsport, self.msg, 'left')
                time.sleep(0.5)
            elif len(servers) > 1:
                self.send_message(find_neighbour_right(self.ip_address), self.hsport, self.msg, 'right')
                time.sleep(1)
            
        pass

    def send_message(self, neighbour, hsport, message, direction):
        try:
            # create TCP socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect_ex((neighbour[0], hsport))
            s.settimeout(None)
            s.sendall(encode_message(message))
            data = s.recv(BUFFER_SIZE)
            
            
            if not data:
               
                if direction == 'right':
                    self.counts_right += 1
                    if debug: print('No data for right neigbour counts: ', self.counts_right)
                elif direction == 'left':
                    self.counts_left += 1
                    if debug: print('No data for left neighbour counts: ', self.counts_left)
                else: print('No direction found')
                return
           # else: print('---- still getting data')
        except socket.error or Exception:
            if direction == 'right':
                self.counts_right += 1
                self.failure_right = True
                if debug: print('Right neighbour socket error +1')
            elif direction == 'left':
                self.counts_left += 1
                self.failure_left = True
                if debug: print('Left neighbour socket error +1')
        finally:
            s.close()
        
        # handling lost neighbours
        if self.counts_left > 2:
            if debug: print('Left neighbour lost: ', neighbour)
            self.announce_lost_server(neighbour, 'left')
            self.counts_left = 0
            pass
        if self.counts_right > 2:
            if debug: print('Right neighbour lost: ', neighbour)
            self.announce_lost_server(neighbour, 'right')
            self.counts_right = 0
            pass
    
    # send a broadcast message to everyone, that server has been lost
    def announce_lost_server(self, neighbour, direction):
        global broadcast_sender
        global servers
        global leader

        msg_lost_server = {
            'cmd': 'LOST_SERVER',
            'uuid': neighbour[1],
            'msg': neighbour[0],
            'direction': direction
        }
        broadcast_sender.broadcast(broadcast_sender.bcip, broadcast_sender.bcport, msg_lost_server)
        if debug: print('Broadcast sent')
        try:
            servers.remove((neighbour[0], neighbour[1]))
            print('Removed server from list: ', neighbour[0])
            if debug: print('Leader: ', leader[0])
            if neighbour[0] == leader[0] and direction == 'right':
                if debug: print('Initiating Voting')
                vote = Voting()
                vote.initiate_voting()
        except ValueError:
            if debug: print('Failed to remove lost server from list')

        # if lost leader discovered start new voting - only right neighbour can start the vote
       
#---------- TCP Unicast ----------
class TCPUnicastSender(Thread):
    def __init__(self, UUID, recipient_IP, msg):
        self.uport = 59072
        self.recipient_IP = recipient_IP
        self.hostname = socket.gethostname()
        self.ip_address = get_host_IP()
        self.msg = msg

        self. send_message(self.recipient_IP, self.uport, self.msg)

    def send_message(self, recipient_IP, uport, message):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect_ex((recipient_IP, uport))
            s.sendall(encode_message(message))
            data = s.recv(BUFFER_SIZE)
        except socket.error or Exception:
            if debug: print('An error has occured while trying to send the TCP Unicast')
        s.close()
        #if debug: print('TCP Unicast successful', message)

class TCPUnicastListener(Thread):
    def __init__(self, listening_port, UUID):
        Thread.__init__(self)
        self.UUID = UUID
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
            
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            if debug: print('Unicast message received')

            msg = {
                'cmd': 'SUCCESS',
                'uuid': str(self.UUID),
                'msg': self.ip_address
            }
            conn.sendall(encode_message(msg))
            MessageHandler(data)

            if debug: print('TCP was successful.')
        print('Server disconnected')

#---------- Voting ----------
class Voting():
    def __init__(self):
        self.my_ip = get_host_IP()
        self.UUID = str(UUID)
        self.is_leader_elected = False
        self.is_leader = False
        self.sorted_list = sorted(servers, key = lambda servers: servers[0])
        self.neighbour_right = find_neighbour_right(self.my_ip)
        global leader
        pass
    
    def initiate_voting(self):
        msg = {
            'cmd': 'VOTE',
            'uuid': self.UUID,
            'msg': self.my_ip,
            'leader_elected': False
        }
        if debug: print('Neighbour: ', self.neighbour_right[0])
        TCPUnicastSender(self.UUID, self.neighbour_right[0], msg)
        print('Voting has been initiated')
    
    def vote_algorithm(self, msg):
        global I_am_leader
        global leader
        if debug: print('Incoming vote: ', msg)
        UUID_received = msg['uuid']
        ip_received = msg['msg']
        leader_elected = msg['leader_elected']

        if leader_elected:
            if UUID_received != self.UUID:
                self.is_leader_elected = True
                I_am_leader = False
                leader = (ip_received, UUID_received)
                TCPVoteSender(self.UUID, self.neighbour_right[0], msg)
                print('The leader is: ', leader[0])

        else:
            if self.UUID == UUID_received:
                I_am_leader = True
                response = {
                    'cmd': 'VOTE',
                    'uuid': self.UUID,
                    'msg': self.my_ip,
                    'leader_elected': True
                }
                print('I am the leader')
                TCPVoteSender(self.UUID, self.neighbour_right[0], response)
                if debug: print('sent')
            elif (int(uuid.UUID(self.UUID)) > int(uuid.UUID(UUID_received))):
                response = {
                    'cmd': 'VOTE',
                    'uuid': self.UUID,
                    'msg': self.my_ip,
                    'leader_elected': False
                }
                if debug: print('My UUID is higher so I am replacing the previous one')
                TCPVoteSender(self.UUID, self.neighbour_right[0], response)
            else:
                if debug: print('Forwarding the incoming voting as my uuid is lower')
                TCPVoteSender(self.UUID, self.neighbour_right[0], msg)
        pass

# tcp sender & listener for voting
class TCPVoteSender(Thread):
    def __init__(self, UUID, recipient_IP, msg):
        self.uport = 59075
        self.recipient_IP = recipient_IP
        self.hostname = socket.gethostname()
        self.ip_address = get_host_IP()
        self.msg = msg

        self. send_message(self.recipient_IP, self.uport, self.msg)

    def send_message(self, recipient_IP, uport, message):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect_ex((recipient_IP, uport))
            s.sendall(encode_message(message))
            data = s.recv(BUFFER_SIZE)
        except socket.error or Exception:
            if debug: print('An error occured while sending the TCP message')
        s.close()
        if debug: print('TCP Unicast Vote successful', message)

class TCPVoteListener(Thread):
    def __init__(self, listening_port, UUID):
        Thread.__init__(self)
        self.UUID = UUID
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
            
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break

            msg = {
                'cmd': 'SUCCESS',
                'uuid': str(self.UUID),
                'msg': self.ip_address
            }
            conn.sendall(encode_message(msg))
            MessageHandler(data)

            #print('TCP was successful. Message: ', decode_message(data))
        print('Server disconnected')
#-----------------------------------------

#---------- Client messages ----------
class TCPClientSender(Thread):
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
            s.connect_ex((recipient_IP, uport))
            s.sendall(encode_message(message))
            s.settimeout(2)
            data = s.recv(BUFFER_SIZE)
            s.settimeout(None)
            
            if debug: print('TCP Unicast successful', message)
        except socket.error or Exception:
            print('Lost client: ', self.name)
            try:
                clients.remove((self.recipient_IP, self.name))
                message_remove = {
                    'cmd': 'CLIENT',
                    'uuid': None,
                    'msg': get_host_IP(),
                    'command': 'remove',
                    'client_ip': self.recipient_IP,
                    'client_name': self.name
                }
                broadcast_sender.broadcast(broadcast_sender.bcip, broadcast_sender.bcport, message_remove)
            except:
                print('Failed to remove client: ', self.name)
            failed = True
        finally:
            s.close()

        if failed:
            message = str(self.name + ' has left the chatroom.')
            lost_client_message = {
                'cmd': 'CHAT',
                'uuid': None,
                'msg': self.ip_address,
                'name': 'Server',
                'message': message
            }
            MessageHandler(encode_message(lost_client_message))


class TCPClientListener(Thread):
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
            
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            #print('Unicast message received 2')

            msg = {
                'cmd': 'SUCCESS',
                'uuid': None,
                'msg': self.ip_address
            }
            conn.sendall(encode_message(msg))
            MessageHandler(data)

            print('TCP was successful. Message: ', decode_message(data))
        print('Server disconnected')        
        
        
#---------- main function -----------
if __name__ == '__main__':
    try:
        listener_b = BroadcastListener()
        listener_b.start()
        listener_u = TCPUnicastListener(59072, UUID)
        listener_u.start()
        listener_v = TCPVoteListener(59075, UUID)
        listener_v.start()
        listener_c = TCPClientListener(59076)
        listener_c.start()

        if debug: print('Listeners started')

        # send initial broadcast for dynamic discovery
        send_initial_broadcast()

        time.sleep(2)

        #print('servers: ', servers)

        broadcast_sender = BroadcastSender()

        heartbeat_listener = HeartbeatListener(59071, UUID)
        heartbeat_listener.start()

        heartbeat_sender = HeartbeatSender()
        heartbeat_sender.start()

    except KeyboardInterrupt:
        sys.exit(0)
    