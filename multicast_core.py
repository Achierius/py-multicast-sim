from network import Packet, NetworkHost, simpleSockListener, IpAddr, loopback_ip
from enclave import EnclaveProgram, enclaveExecute
from queue import Queue, SimpleQueue
from time import sleep
from threading import Thread

ROUTER_SEND_CHILD_BASE_PORT = 5555
ROUTER_SEND_JOIN_PORT = 6666
ROUTER_CONTROL_PORT = 6666
ROUTER_MCAST_PORT = 6667
ROUTER_RESULT_PORT = 6669
ROUTER_RECV_USERTASK_PORT = 6670
ROUTER_SEND_USERTASK_PORT = 6671

WORKER_CONTROL_PORT = 7666
WORKER_MCAST_PORT = 7667
WORKER_SEND_RESULT_PORT = 7669
WORKER_RECV_USERTASK_PORT = 7670

COORD_RECV_USERTASK_PORT = 3070
COORD_SEND_USERTASK_PORT = 3071
COORD_RECV_RESULT_PORT = 3011
COORD_CONTROL_PORT = 3010


class Node:
    def __init__(self, host: NetworkHost, coordinator_ip: IpAddr,
                 debug_name: str):
        self.host = host
        self.coordinator_ip = coordinator_ip
        self.name = debug_name

    def __str__(self):
        return f"[{self.name}]"


class UserTask:
    def __init__(self, program: EnclaveProgram, task_id: int):
        self.id = task_id

        self.program = program
        self.result = None
        self.has_result = False  # Non-pythonic I know

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
