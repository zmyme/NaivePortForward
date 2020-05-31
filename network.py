import socket
import socks
import zlib
import json
import struct
import queue
import time
import sys
import secrets
import hashlib
import traceback

import os

import parallel

default_recv_buffer = 8192

def set_socks5_proxy(server, port):
    default_socket = socket.socket
    socks.set_default_proxy(socks.SOCKS5, server, port)
    socket.socket = socks.socksocket
def SendMessage(host, port, msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.send(msg)
    print('Message Sent!')
    s.close()

class SocketServer():
    def __init__(self, daemon=parallel.daemon, ip='0.0.0.0', port=12345, message_handler=None):
        self.daemon = daemon
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ip, self.port))
        self.socket.listen(5)
        self.socket.settimeout(0.5)
        self.terminate = False
        self.handler = message_handler

    def __del__(self):
        self.terminate = True
        self.socket.close()

    def handle_message(self, clientsocket, addr):
        # print('Connection Established from clinet', addr)
        if self.handler is not None:
            self.handler(clientsocket, addr)

    def loop(self):
        while not self.terminate:
            try:
                clientsocket,addr = self.socket.accept()
                self.daemon.add_job(
                    self.handle_message,
                    args=[clientsocket, addr],
                    name='Client[{0}]'.format(addr)
                )
            except socket.timeout:
                pass
        self.socket.close()

    def start(self, back=True):
        if back:
            self.daemon.add_job(self.loop, name='SocketMainLoop')
        else:
            self.loop()

    def stop(self):
        self.terminate = True

class BridgeConnection():
    def __init__(self, sock1, sock2, daemon=parallel.daemon):
        self.sock1 = sock1
        self.sock2 = sock2
        self.daemon = daemon
        self.exit = False

        self.sock1.settimeout(1)
        self.sock2.settimeout(1)

    def forward(self, src, dst, name='None'):
        while not self.exit:
            msg = None
            try:
                msg = src.recv(default_recv_buffer)
            except (ConnectionAbortedError, ConnectionResetError):
                self.exit = True
                break
            except socket.timeout:
                pass

            if msg is not None:
                if len(msg) == 0:
                    self.exit = True
                    break
                dst.send(msg)
        print('forward {0} terminated.'.format(name))

    def start(self):
        self.daemon.add_job(self.forward, args=[self.sock1, self.sock2, '1->2'])
        self.daemon.add_job(self.forward, args=[self.sock2, self.sock1, '2->1'])

    def wait_for_stop(self):
        while not self.exit:
            time.sleep(1)
        self.sock1.close()
        self.sock2.close()
class PortForwardServer():
    def __init__(self, daemon=parallel.daemon):
        self.daemon = daemon
        self.servers = []

    def add(self, dst_ip, dst_port, listen_ip, listen_port):
        def handler(src, addr):
            host, port = addr
            print('Connection Established from {0}:{1}'.format(host, port))
            dst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dst.connect((dst_ip, dst_port))
            print('Connect to Target Server {0}:{1}'.format(dst_ip, dst_port))
            connection = BridgeConnection(src, dst, daemon=self.daemon)
            connection.start()
            connection.wait_for_stop()
            print('handler stopped. [{0}:{1}]'.format(host, port))
        # print('Handler:', id(handler))
        server = SocketServer(daemon=self.daemon, message_handler=handler, ip=listen_ip, port=listen_port)
        server.start()
        describ_string = '{0}:{1} <=> {2}:{3}'.format(listen_ip,listen_port, dst_ip, dst_port)
        self.servers.append([describ_string, server])

    def get_rules(self):
        return [x[0] for x in self.servers]

    def delete(self, pid):
        self.servers[pid][1].stop()
        del self.servers[pid]
