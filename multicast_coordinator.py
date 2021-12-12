from network import Packet, NetworkHost, simpleSockListener, IpAddr, loopback_ip
from queue import Queue, SimpleQueue
from time import sleep
from termcolor import colored
from threading import Thread
from enclave import EnclaveProgram, enclaveExecute
from multicast_core import *


class UserTask:
    def __init__(self, program: EnclaveProgram, task_id: int):
        self.id = task_id

        self.program = program
        self.result = None
        self.has_result = False # Non-pythonic I know


    def finish(self, result: int):
        self.has_result = True
        self.result = result


    def __repr__(self):
        return self.__str__()


    def __str__(self):
        if self.has_result:
            return f"<UserTask ▣ #{self.id}: {self.result}>"
        else:
            return f"<UserTask □ #{self.id}: {self.program}>"


class Tree:
    def __init__(self, ip: IpAddr, is_router: bool, max_children: int = 0):
        self.children = []
        self.ip = ip
        self.max_children = max_children
        self.is_router = is_router

    def prettyString(self, indent = 0) -> str:
        tab = '  '
        car = colored(' 𝕽 ', 'red') if self.is_router else colored(' 労', 'yellow')
        cdr = ""
        for child in self.children:
            cdr += f"\n{child.prettyString(indent + 1)}"
        return f"{indent*tab}({car}{cdr})"


    def __str__(self):
        car = 'ℝ' if self.is_router else '𝕎'
        cdr = ""
        for child in self.children:
            cdr += " " + child.__str__()
        return f"({car}{cdr})"

    def hasRoom(self) -> bool:
        return self.numChildren() < self.max_children

    def numChildren(self) -> int:
        return len(self.children)

    def addChild(self, ip: IpAddr):
        assert(self.hasRoom())
        self.children.append(ip)


class Coordinator(Node):

    def __init__(self, host: NetworkHost, root_ip: IpAddr,
                 debug_name: str = ""):
        super().__init__(host, host.ip, f"Coordinator \'{debug_name}\'")

        assert host.openPort(simpleSockListener(host, self.handleControlMsg),
                COORD_CONTROL_PORT)
        assert host.openPort(simpleSockListener(host, self.handleResultMsg),
                COORD_RECV_RESULT_PORT)

        self.task_queue = Queue() # Queue for tasks to send to mcast tree
        self.tasks = {} # Used to store results of previously completed tasks

        self.routers = []
        self.workers = []

        self.host = host
        self.root_ip = root_ip
        self.root = None # Wait until they ping us to set things up


    def handleControlMsg(self, p: Packet):
        msg = p.payload
        if (msg['type'] == 'Join'):

            new_node = Tree(p.src, msg['is_router'],
                    msg['max_children'] if msg['is_router'] else 0)

            def findRoom(tree):
                if not tree:
                    return None
                if tree.hasRoom():
                    return tree
                for child in tree.children:
                    candidate = findRoom(child)
                    if candidate:
                        return candidate
                return None

            new_home = findRoom(self.root)
            if new_home:
                new_home.addChild(new_node)

                msg_to_child = {
                          'type': "AssignParent"
                        , 'ip': new_home.ip
                        }
                self.host.sendMsg(msg_to_child, COORD_CONTROL_PORT, p.src,
                        ROUTER_CONTROL_PORT if msg['is_router'] else
                        WORKER_CONTROL_PORT)

                msg_to_parent = {
                          'type': "AssignChild"
                        , 'ip': p.src
                        , 'node_type': "Router" if msg['is_router'] else "Worker"
                        }
                self.host.sendMsg(msg_to_parent, COORD_CONTROL_PORT, new_home.ip,
                        ROUTER_CONTROL_PORT)
            else:
                # TODO reply with NACK
                return
        elif (msg['type'] == 'RootJoin'):
            # TODO reply with ACK?
            assert p.src == self.root_ip, "RootJoin received from wrong router!"
            self.root = Tree(p.src, True, msg['max_children'])
            return
        elif (msg['type'] == 'Leave'):
            return
        else:
            assert not msg, f"bad msg contents: {msg}"


    # TODO add UIDs to avoid people reporting for the wrong task
    def handleResultMsg(self, p: Packet):
        msg = p.payload
        assert msg['type'] == 'Result', f"bad Result msg type: {msg}"
        self.tasks[msg['program_uid']].finish(msg['result'])
        self.task_queue.task_done()
        # TODO pass message along to user


    def enqueueUserTask(self, task: UserTask):
        self.tasks[task.id] = task
        self.task_queue.put(task)

        # TODO defer this to later
        user_task = self.task_queue.get()
        msg = {
              'type': 'ExecFakeProgram'
            , 'program': user_task.program
            , 'program_uid': user_task.id
            }
        packet = Packet(msg, self.host.ip, COORD_SEND_USERTASK_PORT,
                self.root_ip, ROUTER_RECV_USERTASK_PORT)
        assert self.host.sendPacket(packet), f"Packet failed to send: {packet}"


    def joinUserTasks(self):
        self.task_queue.join()
