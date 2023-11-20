#!/usr/bin/env python3
"""Fetch server stats from ark server"""

import socket
import struct

A2S_INFO_REQUEST_FMT = '<ic20s'
A2S_INFO_RESPONSE_FMT = '<H7B'
A2S_PLAYER_REQUEST_FMT = '<ic'
RESPONSE_HEADER_FMT = '<ic'


class ProtocolError(Exception):
    """Protocol Error"""


class ServerInfo:
    """Data class for Server Info"""
    protocol_version = 0
    server_name = ''
    map = ''
    folder = ''
    game = ''
    app_id = 0
    num_players = 0
    max_players = 0
    bot_count = 0
    server_type = 0
    platform = 0
    private = 0
    vac = 0
    version = ''
    port = None
    steam_id = None
    sourcetv_port = None
    sourcetv_name = None
    keywords = None
    game_id = None

    def __init__(self, data):
        if data[0:1] != b'I':
            raise ProtocolError('Wrong response')
        (self.protocol_version, ) = struct.unpack('B', data[1:2])
        parts = data[2:].split(b'\0', 4)
        (self.server_name, self.map, self.folder, self.game)\
            = [part.decode() for part in parts[:4]]
        data = parts[4]
        ilen = struct.calcsize(A2S_INFO_RESPONSE_FMT)
        (self.app_id, self.num_players, self.max_players,
         self.bot_count, self.server_type, self.platform,
         self.private, self.vac) = struct.unpack(A2S_INFO_RESPONSE_FMT,
                                                 data[:ilen])
        version_bytes, data = data[ilen:].split(b'\0', 1)
        self.version = version_bytes.decode()
        (edf, ) = struct.unpack('B', data[0:1])
        data = data[1:]
        if edf & 0x80:
            (self.port, ) = struct.unpack('<H', data[:2])
            data = data[2:]
        if edf & 0x10:
            (self.steam_id, ) = struct.unpack('<Q', data[:8])
            data = data[8:]
        if edf & 0x40:
            (self.sourcetv_port, ) = struct.unpack('<H', data[:2])
            sourcetv_name, data = data[2:].split(b'\0', 1)
            self.sourcetv_name = sourcetv_name.decode()
        if edf & 0x20:
            keyword_bytes, data = data.split(b'\0', 1)
            self.keywords = keyword_bytes.decode()
        if edf & 0x01:
            (self.game_id, ) = struct.unpack('<Q', data[:8])

    def __repr__(self):
        s = f'<ServerInfo protocol_version={self.protocol_version}'\
            f' server_name="{self.server_name}"'\
            f' map="{self.map}"'\
            f' folder="{self.folder}"'\
            f' game="{self.game}"'\
            f' app_id={self.app_id}'\
            f' num_players={self.num_players}'\
            f' max_players={self.max_players}'\
            f' bot_count={self.bot_count}'\
            f' server_type={self.server_type}'\
            f' platform={self.platform}'\
            f' private={self.private}'\
            f' vac={self.vac}'
        if self.port is not None:
            s += f' port={self.port}'
        if self.steam_id is not None:
            s += f' steam_id={self.steam_id}'
        if self.sourcetv_port is not None:
            s += f' sourcetv_name="{self.sourcetv_name}"'
            s += f' sourcetv_port={self.sourcetv_port}'
        if self.keywords is not None:
            s += f' keywords="{self.keywords}"'
        if self.game_id is not None:
            s += f' game_id={self.game_id}'
        s += '>'
        return s


class PlayerInfo:
    """Info about players"""
    def __init__(self, data):
        self.players = []
        (header, num_players, ) = struct.unpack('cB', data[0:2])
        if header != b'D':
            raise ProtocolError('Wrong response')
        data = data[2:]
        for _ in range(num_players):
            name, data = data[1:].split(b'\0', 1)  # skip index
            self.players.append(name)
            data = data[8:]  # skip score and duration

    def __repr__(self):
        return '<PlayerInfo' + ' '.join(f' "{player}"'
                                        for player in self.players) + '>'


class Query:
    """UDP query logic"""

    def __init__(self, servername, port):
        self.peer = (servername, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1.0)
        self.received = b''

    def send_recv(self, request):
        """handle udp traffic"""
        self.socket.sendto(request, self.peer)
        return self.recv()

    def recv(self):
        """receive udp packet"""
        (response, _) = self.socket.recvfrom(1500)
        return response

    def handle_challenge(self, request):
        """send request and handle challenge logic"""
        response = self.send_recv(request + struct.pack('<i', -1))
        hlen = struct.calcsize(RESPONSE_HEADER_FMT)
        while True:
            (split, header) = struct.unpack(RESPONSE_HEADER_FMT,
                                            response[:hlen])
            if header == b'A':
                return self.handle_challenge(request + response[hlen:hlen + 4])
            if split == -1:
                ret = self.received + response[4:]
                self.received = b''
                return ret
            if split == -2:
                self.received = response[4:]
                response = self.recv()
            else:
                raise ProtocolError(f'{split=}')

    def get_info(self):
        """get server info"""
        request = struct.pack(A2S_INFO_REQUEST_FMT,
                              -1, b'T', b'Source Engine Query\0')
        return ServerInfo(self.handle_challenge(request))

    def get_players(self):
        """get player details"""
        request = struct.pack(A2S_PLAYER_REQUEST_FMT, -1, b'U')
        return PlayerInfo(self.handle_challenge(request))


if __name__ == '__main__':
    q = Query('tranquillity', 27015)
    print(q.get_info())
    print(q.get_players())
