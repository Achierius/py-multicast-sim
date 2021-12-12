from queue import Queue, SimpleQueue
from time import sleep
from threading import Thread
from simulators.network import Packet, NetworkHost, simpleSockListener, IpAddr, loopback_ip
from simulators.enclave import EnclaveProgram, enclaveExecute
from multicast.core import *


class Router(Node):

    def __init__(
            self,
            host: NetworkHost,
            coordinator_ip: IpAddr,
            is_root: bool,
            max_children: int,
            debug_name: str,
            enable_sharding: bool = True):
        super().__init__(host, coordinator_ip, f"Router \'{debug_name}\'")

        self.is_root = is_root
        self.max_children = max_children  # Soft max
        self.parent = None
        self.child_workers = []
        self.child_routers = []
        self.enable_sharding = enable_sharding

        self.child_task_counts = {}  # Lets us load-balance new tasks
        self.child_task_keys = {}  # Idealized (downwards) key-based sharding

        assert host.openPort(simpleSockListener(host, self.handleControlMsg),
                             ROUTER_CONTROL_PORT)
        assert host.openPort(simpleSockListener(host, self.handleMulticastMsg),
                             ROUTER_MCAST_PORT)
        assert host.openPort(simpleSockListener(host, self.handleUserTask),
                             ROUTER_RECV_USERTASK_PORT)
        assert host.openPort(simpleSockListener(host, self.handleResultMsg),
                             ROUTER_RESULT_PORT)

        join_msg = {
            'type': "RootJoin" if is_root else "Join",
            'max_children': max_children,
            'is_router': True}
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
            def propogateMulticast(ip, is_router):
                assert ip, f"Null ip cannot be propogated: orig. packet {p}"
                if ip is p.src:
                    return  # Don't bounce to the sender!
                dst_port = ROUTER_MCAST_PORT if is_router else WORKER_MCAST_PORT
                assert self.host.forwardPacket(
                    p, ROUTER_MCAST_PORT, ip, dst_port), "mcast propogate failed"

            # First send up the tree to our parent, unless they sent it to us
            # TODO shard upwards as well
            if not self.is_root:
                propogateMulticast(self.parent, True)
            # Then send down to children, EXCEPT the one which (if any) sent it!
            # We traverse our record of their working-set of keys to avoid
            # sending redundant packets, this is basically the biggest thing
            # we're working on in this whole project so it's pretty important
            # In C++ ofc we're doing this with Bloom Filters but this still
            # gives us a pretty chill lower bound on congestion
            k = msg['key']
            if self.enable_sharding:
                for child, child_dict in self.child_task_keys.items():
                    if k and k in child_dict and child_dict[k] > 0:
                        if child in self.child_routers:
                            propogateMulticast(child, True)
                        else:
                            assert child in self.child_workers, "neither router nor child?"
                            propogateMulticast(child, False)
            else:
                for child in self.child_workers:
                    propogateMulticast(child, False)
                for child in self.child_routers:
                    propogateMulticast(child, True)
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

        # Track metadata for our children to optimize mcasting + task assignment
        # 1.  Select child with fewest queued tasks (as far as we know)
        lucky_child = min(
            self.child_task_counts,
            key=self.child_task_counts.get)
        self.child_task_counts[lucky_child] += 1  # Track tasks per child
        if lucky_child not in self.child_task_keys:  # Track keys in use by child
            self.child_task_keys[lucky_child] = {}
        for k in msg['program'].keys:
            if k in self.child_task_keys[lucky_child]:
                self.child_task_keys[lucky_child][k] += 1
            else:
                self.child_task_keys[lucky_child][k] = 1

        self.host.forwardPacket(
            p,
            p.dst_port,
            lucky_child,
            ROUTER_RECV_USERTASK_PORT if lucky_child in self.child_routers else WORKER_RECV_USERTASK_PORT)

    def handleResultMsg(self, p: Packet):
        msg = p.payload
        assert msg['type'] == 'Result', f"bad Result msg type: {msg}"

        self.child_task_counts[p.src] -= 1  # Track tasks per child
        assert p.src in self.child_task_keys, \
            "child_task_key missing: Should have populated this earlier!"
        for k in msg['program'].keys:      # Track keys in use per child
            assert k in self.child_task_keys[p.src], \
                "child_task_key sub-key missing: Should have populated this earlier!"
            self.child_task_keys[p.src][k] -= 1

        if self.is_root:
            self.host.forwardPacket(
                p,
                ROUTER_RESULT_PORT,
                self.coordinator_ip,
                COORD_RECV_RESULT_PORT)
        else:
            self.host.forwardPacket(p, ROUTER_RESULT_PORT,
                                    self.parent, ROUTER_RESULT_PORT)
