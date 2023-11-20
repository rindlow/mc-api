#!/usr/bin/env python3
"""Communicate with a server on RCON"""

import socket
import struct


RCON_HEADER_FMT = '<iii'
SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0


class ProtocolError(Exception):
    """Protocol Error"""


class LoginFailed(Exception):
    """Login Failed"""


class Rcon:
    """Rcon connection"""

    def __init__(self, server, port, password):
        self.server = server
        self.port = port
        self.password = password
        self.request_id = 0

        self.connect()
        self.login()

    def connect(self):
        """Connect to a rcon server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((self.server, self.port))
        except ConnectionRefusedError as exc:
            raise LoginFailed("Connection refused") from exc

    def login(self):
        """Send password to login"""
        self.request_id += 1
        request = struct.pack(RCON_HEADER_FMT,
                              len(self.password) + 10,
                              self.request_id,
                              SERVERDATA_AUTH)
        request += (self.password.encode() + b'\0\0')
        self.socket.send(request)
        response_bytes = self.socket.recv(4096)
        print(response_bytes)
        hlen = struct.calcsize(RCON_HEADER_FMT)
        (_, response_id, response_type)\
            = struct.unpack(RCON_HEADER_FMT, response_bytes[:hlen])
        if response_type != SERVERDATA_AUTH_RESPONSE:
            raise ProtocolError('Wrong response type')
        if response_id != self.request_id:
            raise LoginFailed

    def exec(self, command):
        """send command to be executed, return output"""
        self.request_id += 1
        request = struct.pack(RCON_HEADER_FMT,
                              len(command) + 10,
                              self.request_id,
                              SERVERDATA_EXECCOMMAND)
        request += (command.encode() + b'\0\0')
        self.socket.send(request)
        response_bytes = self.socket.recv(4096)
        print(response_bytes)
        hlen = struct.calcsize(RCON_HEADER_FMT)
        (_, response_id, response_type)\
            = struct.unpack(RCON_HEADER_FMT, response_bytes[:hlen])
        if response_type != SERVERDATA_RESPONSE_VALUE:
            raise ProtocolError('Wrong response type')
        if response_id != self.request_id:
            raise ProtocolError('Wrong Request ID received')
        return response_bytes[hlen:-2].decode()


if __name__ == '__main__':
    import getpass
    rcon = Rcon('tranquillity', 32330, getpass.getpass())
    print(rcon.exec('ListPlayers'))
    print(rcon.exec('DoExit'))
    # mc = Rcon('tranquillity', 25575, getpass.getpass())
    # print(mc.exec('list'))
