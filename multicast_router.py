from network import Packet, NetworkHost, simpleSockListener, IpAddr, loopback_ip
from enclave import EnclaveProgram, enclaveExecute
from queue import Queue, SimpleQueue
from time import sleep
from threading import Thread
from multicast_core import *

class Router(Node):

    def __init__(self, host: NetworkHost, coordinator_ip: IpAddr, is_root: bool,
            max_children: int, debug_name: str = ""):
        super().__init__(host, coordinator_ip, f"Router \'{debug_name}\'")

        self.parent = None
        self.child_workers = []
        self.child_task_counts = {}
        self.child_routers = []
        self.is_root = is_root
        self.max_children = max_children # Soft max

        assert host.openPort(simpleSockListener(host, self.handleControlMsg),
                ROUTER_CONTROL_PORT)
        assert host.openPort(simpleSockListener(host, self.handleMulticastMsg),
                ROUTER_MCAST_PORT)
        assert host.openPort(simpleSockListener(host, self.handleUserTask),
                ROUTER_RECV_USERTASK_PORT)
        assert host.openPort(simpleSockListener(host, self.handleResultMsg),
                ROUTER_RESULT_PORT)

        join_msg = {
                  'type': "RootJoin" if is_root else "Join"
                , 'max_children': max_children
                , 'is_router': True
                }
        self.host.sendMsg(join_msg, ROUTER_SEND_JOIN_PORT,
                coordinator_ip, COORD_CONTROL_PORT)

        return


    def handleControlMsg(self, p: Packet):
        assert p.src == self.coordinator_ip, \
            f"Recv. Control Msg with bad origin: {p}"
        msg = p.payload
        if (msg['type'] == 'AssignParent'):
            self.parent = msg['ip']
            return
        elif (msg['type'] == 'AssignChild'):
            ip = msg['ip']
            if msg['node_type'] == 'Worker':
                self.child_workers.append(ip)
                self.child_task_counts[ip] = 0
            elif msg['node_type'] == 'Router':
                self.child_routers.append(ip)
                self.child_task_counts[ip] = 0
            else:
                assert not msg, f"Bad node_type in msg: {msg}"
        else:
            assert not msg, f"bad msg contents: {msg}"


    def handleMulticastMsg(self, p: Packet):
        msg = p.payload
        if (msg['type'] == 'KeyUpdate'):
            # TODO multicast propogation
            return
        else:
            assert not msg, f"bad msg contents: {msg}"


    def handleUserTask(self, p: Packet):
        msg = p.payload
        assert msg['type'] == 'ExecFakeProgram', f"Bad packet: {p}"
        # TODO bounce back if no children available
        if (not self.child_workers) and (not self.child_routers):
            print(self, self.child_workers, self.child_routers)
            assert self.child_workers or self.child_routers, "I have no child"
        lucky_child = min(self.child_task_counts, key = self.child_task_counts.get)
        new_packet = Packet(p.payload,
                p.dst, p.dst_port,
                lucky_child,
                ROUTER_RECV_USERTASK_PORT if lucky_child in self.child_routers else
                WORKER_RECV_USERTASK_PORT)
        self.host.sendPacket(new_packet)


    def handleResultMsg(self, p: Packet):
        msg = p.payload
        assert msg['type'] == 'Result', f"bad Result msg type: {msg}"
        self.child_task_counts[p.src] -= 1
        if self.is_root:
            packet = Packet(p.payload,
                            self.host.ip, ROUTER_RESULT_PORT,
                            self.coordinator_ip, COORD_RECV_RESULT_PORT)
            self.host.sendPacket(packet)
            pass
        else:
            packet = Packet(p.payload,
                            self.host.ip, ROUTER_RESULT_PORT,
                            self.parent, ROUTER_RESULT_PORT)
            self.host.sendPacket(packet)
