#!/usr/bin/env python3
"""Fetch server stats from minecraft server"""

import socket
import struct

HANDSHAKE_REQUEST_FMT = '>HBI'
BASIC_REQUEST_FMT = '>HBII'
FULL_REQUEST_FMT = '>HBIII'
RESPONSE_HEADER_FMT = '>BI'
MAGIC = 0xFEFD


class HandshakeError(Exception):
    """Handshake failed"""


class BasicStats:
    """Data class for basic stats"""
    motd = ''
    map = ''
    num_players = 0
    max_players = 0
    port = 25565
    ip = ''

    def propstr(self):
        """format basic properties"""
        return f'motd="{self.motd}" map="{self.map}"'\
               f' num_players={self.num_players}'\
               f' max_players={self.max_players}'\
               f' port={self.port} ip="{self.ip}"'

    def __repr__(self):
        return f'<BasicStats {self.propstr()}>'


class FullStats(BasicStats):
    """Data class for full stats"""
    version = ''
    plugins = []
    players = []

    def __repr__(self):
        players = ', '.join(f'"{p}"' for p in self.players)
        return f'<FullStats {self.propstr()}'\
               f' version="{self.version}" plugins="{self.plugins}"'\
               f' players=[{players}]>'


class Query:
    """UDP query logic"""

    session_id = 0
    challenge_token = 0

    def __init__(self, servername, port):
        self.peer = (servername, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1.0)

    def flattened_session_id(self):
        """Pack 16 bit session id into low nibbles of 32 bit int"""
        return ((self.session_id & 0x0000F000) << 12
                | (self.session_id & 0x00000F00) << 8
                | (self.session_id & 0x000000F0) << 4
                | (self.session_id & 0x0000000F))

    def send_recv(self, request, query):
        """handle udp traffic"""
        self.socket.sendto(request, self.peer)
        (response, _) = self.socket.recvfrom(1024)
        hlen = struct.calcsize(RESPONSE_HEADER_FMT)
        (querytype, session_id) = struct.unpack(RESPONSE_HEADER_FMT,
                                                response[:hlen])
        if querytype != query or session_id != self.session_id:
            raise HandshakeError()
        return response[hlen:]

    def do_handshake(self):
        """request a new challenge token"""
        self.session_id += 1
        request = struct.pack(HANDSHAKE_REQUEST_FMT, MAGIC, 9,
                              self.flattened_session_id())
        challenge_token_string = self.send_recv(request, 9)\
            .decode().strip('\0')
        self.challenge_token = int(challenge_token_string)

    def get_basic(self):
        """get basic stats"""
        self.do_handshake()
        request = struct.pack(BASIC_REQUEST_FMT,
                              MAGIC, 0, self.session_id, self.challenge_token)
        basic_stats_bytes = self.send_recv(request, 0)
        basic_stats_list = basic_stats_bytes.split(b'\0')
        stats = BasicStats()
        stats.motd = basic_stats_list[0].decode()
        stats.map = basic_stats_list[2].decode()
        stats.num_players = int(basic_stats_list[3].decode())
        stats.max_players = int(basic_stats_list[4].decode())
        (stats.port,) = struct.unpack('<H', basic_stats_list[5][:2])
        stats.ip = basic_stats_list[5][2:].decode()
        return stats

    def get_full(self):
        """get full stats"""
        self.do_handshake()
        request = struct.pack(FULL_REQUEST_FMT,
                              MAGIC, 0, self.session_id,
                              self.challenge_token, 0)
        full_stats_bytes = self.send_recv(request, 0)
        full_stats_list = full_stats_bytes.split(b'\0')
        stats = FullStats()
        i = 0
        while i < len(full_stats_list):
            if full_stats_list[i] == b'':
                break
            if full_stats_list[i+1] != b'\x80':
                value = full_stats_list[i+1].decode()
            match full_stats_list[i].decode():
                case 'hostname':
                    stats.motd = value
                case 'version':
                    stats.version = value
                case 'plugins':
                    stats.plugins = value
                case 'map':
                    stats.map = value
                case 'numplayers':
                    stats.num_players = int(value)
                case 'maxplayers':
                    stats.max_players = int(value)
                case 'hostport':
                    stats.port = int(value)
                case 'hostip':
                    stats.ip = value
            i += 2
        while full_stats_list[i] != b'\x01player_':
            i += 1
        i += 2
        stats.players = [p.decode()
                         for p in full_stats_list[i:i+stats.num_players]]
        return stats


if __name__ == '__main__':
    q = Query('tranquillity', 25565)
    print(q.get_basic())
    print(q.get_full())
