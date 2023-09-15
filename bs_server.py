'''
BattleShell Server V1.0

This program allows a user to host a Battleship server using socket.
The host can interact with an opponent as long as they are on the same
Wifi network and configure the same PORT.

Author: Paul Belland
'''

import socket
import pickle

PORT = 5001

class Server:
    '''Basic Server Class for BattleShell'''
    def __init__(self,name):
        self.name = name
    
    def run(self):
        '''Starts and awaits connection'''
        try:
            self.host = socket.gethostname()
            self.server = socket.socket()
            
            self.server.bind((self.host, PORT))
            self.server.listen(2)   # 2 connections
            self.server.setblocking(0)
            return 'Waiting for opponent...'
        except:
            return 'Server already running!'
        
    def search(self):
        '''When called, tries to accept any incoming connections from other clients'''
        try:
            self.conn, self.address = self.server.accept()  # accept new connection
            self.conn.setblocking(0)
            self.send('Name',self.name)
            return 'Connected to opponent!'
        except:
            return False
    
    def refresh(self):
        '''When called, receives any packets passed from opponent'''
        try:
            conn = self.conn
            raw_data = conn.recv(1024)
            
            if raw_data:
                payload = pickle.loads(raw_data)
                identifier, data = payload[0], payload[1]
                return identifier, data
            else:
                return 'Status', 'Disconnected'
        except BlockingIOError:
            return None, None
            
    def send(self,identifier,data=None):
        '''Sends any given data to opponent's client'''
        payload = pickle.dumps([identifier,data])
        self.conn.send(payload)
        
    def close(self):
        '''Kills the server'''
        self.server.close()