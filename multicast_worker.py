from network import Packet, NetworkHost, simpleSockListener, IpAddr, loopback_ip
from enclave import EnclaveProgram, enclaveExecute
from queue import Queue, SimpleQueue
from time import sleep
from threading import Thread
from multicast_core import *


class Worker(Node):
    def __init__(self, host: NetworkHost, coordinator_ip: IpAddr,
                 debug_name: str = ""):
        super().__init__(host, coordinator_ip, f"Worker \'{debug_name}\'")

        assert host.openPort(simpleSockListener(host, self.handleControlMsg),
                WORKER_CONTROL_PORT)
        assert host.openPort(simpleSockListener(host, self.handleMulticastMsg),
                WORKER_MCAST_PORT)
        assert host.openPort(simpleSockListener(host, self.handleUserTask),
                WORKER_RECV_USERTASK_PORT)

        self.parent = None
        self._enclave_queue = SimpleQueue()
        self._enclave_thread = None
        self._enclave_memcache = {}

        join_msg = {
                'type': "Join",
                'is_router': False
                }
        self.host.sendMsg(join_msg, ROUTER_SEND_JOIN_PORT,
                coordinator_ip, COORD_CONTROL_PORT)



    def handleControlMsg(self, p: Packet):
        assert p.src == self.coordinator_ip, \
            f"Recv. Control Msg with bad origin: {p}"
        msg = p.payload
        if (msg['type'] == 'AssignParent'):
            self.parent = msg['ip']
            return
        else:
            assert false, f"bad msg contents: {msg}"


    def handleMulticastMsg(self, p: Packet):
        # TODO update local memcache if it's relevant, maybe reply or something
        pass


    def handleUserTask(self, p: Packet):
        msg = p.payload
        assert msg['type'] == "ExecFakeProgram", f"Bad packet: {p}"
        program = msg['program']

        assert self.parent, "Detached worker cannot run!"
        if self._enclave_thread is None:
            self._enclaveStart(program, msg['program_uid'])
        else:
            self._enclave_queue.put( (program, msg['program_uid']) )


    def _enclaveStart(self, program: EnclaveProgram, program_uid: int):
        assert self._enclave_thread is None, "Enclave already running"
        def callback(result):
            return self._enclaveComplete(program, program_uid, result)
        self._enclave_thread = Thread(
                target = enclaveExecute,
                args = (program, self._enclaveUpdate, callback))
        self._enclave_thread.start()


    def _enclaveUpdate(self, key, value, program: EnclaveProgram):
        self._enclave_memcache[key] = value
        mcast_msg = {
                  'type': "KeyUpdate"
                , 'key': key
                , 'value': value
                }
        self.host.sendMsg(mcast_msg, WORKER_MCAST_PORT, self.parent, ROUTER_MCAST_PORT)


    def _enclaveComplete(self, program: EnclaveProgram, program_uid: int, result):
        # Currently runs synchronously so no need to join
        #self._enclave_thread.join()

        result_msg = {
                  'type': "Result"
                , 'result': result
                , 'program': program
                , 'program_uid': program_uid
                }
        self.host.sendMsg(result_msg, WORKER_SEND_RESULT_PORT,
                          self.parent, ROUTER_RESULT_PORT)

        if not self._enclave_queue.empty():
            self._enclave_thread = None
            task, t_id = self._enclave_queue.get()
            self._enclaveStart(task, t_id)
        else:
            self._enclave_thread = None
