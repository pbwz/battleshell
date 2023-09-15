'''
BattleShell Opponent V1.0

This program allows a user to connect to a Battleship host through socket.
The opponent can interact with the host as long as they are on the same
Wifi network and configure the same PORT.

Author: Paul Belland
'''

import socket
import pickle

PORT = 5001

class Client:
    def __init__(self,name):
        self.name = name   # players username
    
    def run(self):
        '''Attempts to connect to host if it exists'''
        try:
            self.host = socket.gethostname()  # as both code is running on same pc
            self.client_sock = socket.socket()  # instantiate
            self.client_sock.connect((self.host, PORT))  # connect to the server
            self.client_sock.setblocking(0)
            return 'Connected to host!'
        except:
            return 'No host could be found'

    def refresh(self):
        '''When called, receives any packets passed from host
        Returns:
        - Identifier tag (helps identify what to do with info)
        - Data associated with identifier tag (ie List or String)
        '''
        try:
            raw_data = self.client_sock.recv(1024)
            
            if raw_data:
                payload = pickle.loads(raw_data)
                identifier, data = payload[0], payload[1]
                return identifier, data
            else:
                return 'Status', 'Disconnected'
        except BlockingIOError:
            return None, None
            
    def send(self,identifier,data=None):
        '''Sends any given data to host'''
        payload = pickle.dumps([identifier,data])
        self.client_sock.send(payload)
        
    def close(self):
        '''Kills the client connection to host'''
        self.client_sock.close()