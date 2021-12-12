from itertools import count
from datetime import datetime
import typing
from pprint import pprint

# We abstract away all protocols which are necessary only due to the
# *decentralized* nature of the internet: BGP, ARP, TCP, DNS, etc. IP remains,
# but simplified to function more-or-less like MAC: all hosts are arbitrarily
# mapped to a unique, unchanging address, and this mapping is accessible
# instantaneously from all network hosts on the 'internet'.

IpAddr = str
loopback_ip = "127.0.0.1"

class Packet:
    def __init__(self, payload : str,
                 src : IpAddr, src_port : int,
                 dst : IpAddr, dst_port : int):
        self.src = src
        self.dst = dst
        self.src_port = src_port
        self.dst_port = dst_port
        self.payload = payload
        self.time = datetime.now()


    def __str__(self):
        return (f"Packet: "
                f"({self.src}:{self.src_port} => "
                f"{self.dst}:{self.dst_port} "
                f"{self.payload})")


    def __repr__(self):
        return self.__str__()


class NetworkHost:
    #local_ports  = {} # Maps port # => node to alert upon message receipt
    #port_buffers = {} # Maps port # => (buffer, sender)

    def __init__(self, ip: IpAddr = None):
        self.local_ports = {}
        self.port_buffers = {}
        if ip is None:
            self.ip = _registerHost(self)
        else:
            self.ip = _registerHost(self, ip)
            assert ip, "Failed to register host!"


    def openPort(self, callback, port: int) -> bool:
        """
        If port is open, sets callback to CALLBACK and returns True.
        Otherwise returns False.
        """
        assert callable(callback), "Callback must be callable"
        if port in self.local_ports:
            print(port, "VS", self.local_ports)
            return False
        self.local_ports[port] = callback
        return True


    def closePort(self, port: int):
        """If port is open, frees it."""
        self.local_ports.pop(port, None)
        self.port_buffers.pop(port, None)


    def sendPacket(self, packet: Packet) -> bool:
        """
        Tries to send packet from current host via the network.
        Returns false iff send fails (e.g. if recipient DNE) or
        if the packet's source IP does not match the current host.
        """
        assert packet.src == self.ip, \
                f"Mismatched dest. IP in packet {packet}:"\
                f"{packet.src} vs. actual {self.ip}"
        return _sendPacket(packet)


    def forwardPacket(self, packet: Packet, port: int,
            dst: IpAddr, dst_port: int) -> bool:
        """
        Changes the source/destination of the given packet such that the packet
        originates from this host at port PORT and is sent to DST:DST_PORT.
        The destination of the packet must be equivalent to this host's IP.
        Returns false if the packet is valid but cannot be send for another
        reason.
        """
        assert packet.dst == self.ip, \
                f"Mismatched dest. IP in forwarded packet {packet}:"\
                f"{packet.dst} vs. actual {self.ip}"
        new_packet = Packet(packet.payload, self.ip, port, dst, dst_port)
        return self.sendPacket(new_packet)


    def sendMsg(self, msg, local_port: int,
            dst: IpAddr, remote_port: int) -> bool:
        """
        Creates packet from given message, then attempts to
        send packet from current host via the network.
        Returns false iff send fails (e.g. if recipient DNE).
        """
        packet = Packet(msg, self.ip, local_port, dst, remote_port)
        return self.sendPacket(packet)


    def recvPacket(self, p: Packet) -> bool:
        """
        If port is open, overwrites contents of its buffer with PACKET and
        notifies the port's owner, then returns True.
        Otherwise returns False.
        Should NOT be called by programs 'running' on this host!
        """
        assert p.dst == loopback_ip or p.dst == self.ip, \
                f"Mismatched dest. IP in recieved packet {p}:"\
                f"{p.dst} vs. actual {self.ip}"
        port = p.dst_port
        if port in self.local_ports:
            self.port_buffers[port] = p
            self.local_ports[port](port)
            return True
        return False


    def ping(self, dst: IpAddr) -> (bool, float):
        """
        The first parameter returned is True iff DST is online and reachable.
        If so, the second the round-trip time, in seconds, to DST.
        """
        _calcNetworkDistance(self.ip, dst) + _calcNetworkDistance(dst, self.ip)


def simpleSockListener(host: NetworkHost, callback):
    assert callable(callback), "Callback must be callable"
    def listener(port: int):
        return callback(host.port_buffers[port])
    return listener


_ip_map = {}
_reserved_ips = [loopback_ip]
_logged_packets = []
_logged_failures = []


def getNetworkDebugInfo():
    """ Returns some useful stats and logs for debugging. """
    return (_ip_map, _logged_packets, _logged_failures)


def netReset():
    """ Resets the network state to its base (empty) configuration. """
    global _ip_map
    global _reserved_ips
    global _logged_packets
    global _logged_failures

    _ip_map = {}
    _reserved_ips = [loopback_ip]
    _logged_packets = []
    _logged_failures = []


def _calcNetworkDistance(src: IpAddr, dst: IpAddr):
    if (src == dst) or (dst == loopback and _route(src, dst)):
        return 0
    return 0 # TODO at some point


def _registerHost(host: NetworkHost, ip: IpAddr = None) -> IpAddr:
    """
    Attempts to add host to the internet mapping with the specified address, if
    one is given; if IP is None, instead assigns the first available address in
    the local subnet 192.168.X.X.
    Returns the address if successful, otherwise returns None.
    """
    addr = ip
    if ip is None:
        for c in range(1, 256): # Giga lazy brute force
            for d in range(1, 256):
                addr = "192.168." + str(c) + "." + str(d)
                if addr not in _ip_map:
                    _ip_map[addr] = host
                    return addr
        return None
    elif (ip in _ip_map) or (ip in _reserved_ips):
        return None
    else:
        _ip_map[ip] = host
        return ip


def _route(src: IpAddr, dst: IpAddr) -> NetworkHost:
    """
    Returns the host object at address DST from SRC, or None if DST is offline
    or unreachable from SRC.
    """
    # Route 127.0.0.1 correctly
    if (src in _ip_map) and (loopback_ip == dst):
        return _ip_map[src]
    elif (src in _ip_map) and (dst in _ip_map):
        return _ip_map[dst]
    return None


def _sendPacket(p: Packet) -> bool:
    """
    Tries to send packet via network. May fail (e.g. if recipient DNE).
    Returns false only if recipient address is not bound or if recipient
    at given address does not have a port open.
    """
    # TODO build in network delays?
    target_host = _route(p.src, p.dst)

    if target_host:
        # Since recvPacket is blocking right now, we optimistically log the
        # packet and remove it if the send fails, preventing the stack of packet
        # log messages from landing on the log in reverse order.
        _logged_packets.append(p) # Since recvPacket is blocking, we
        if target_host.recvPacket(p):
            return True
        else:
            _logged_packets.remove(p)
            _logged_failures.append( ("Port closed", p) )
    else:
        _logged_failures.append( ("Routing failed", p) )
    return False
