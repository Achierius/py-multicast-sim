import unittest
from pprint import pprint
from time import sleep

from network import *
from multicast_core import *
from multicast_coordinator import *
from multicast_router import *
from multicast_worker import *
from enclave import *


class TestNetworkSimulator(unittest.TestCase):

    class PortListener:

        def __init__(self, test_rig, debug_name, host, port, callback=None):
            self.test_rig = test_rig
            self.name = debug_name
            self.host = host
            self.expects_packet = False
            self.callback = callback
            test_rig.assertTrue(host.openPort(self.notify, port),
                                f"({self.name}) Failed to open port!")

        def setExpectation(self, p: Packet):
            self.expects_packet = True
            self.expected_port = p.dst_port
            self.expected_message = p.payload
            self.expected_sender = p.src
            # TODO refactor & cover the other fields in p

        def notify(self, port: int):
            self.test_rig.assertTrue(self.expects_packet,
                                     f"({self.name}) Unexpected packet!")
            self.expects_packet = False
            packet = self.host.port_buffers[port]

            self.test_rig.assertEqual(self.expected_port, packet.dst_port,
                                      f"({self.name}) Unexpected packet port!")
            self.test_rig.assertEqual(
                self.expected_message,
                packet.payload,
                f"({self.name}) Unexpected packet contents!")
            self.test_rig.assertEqual(
                self.expected_sender,
                packet.src,
                f"({self.name}) Unexpected packet source!")

            if self.callback:
                self.callback(packet, self.host)

    def test_send_bounce(self):
        server_A = NetworkHost()
        server_B = NetworkHost()

        def packetBouncer(p: Packet, host):
            new_packet = Packet(p.payload,
                                p.dst, p.dst_port,
                                p.src, p.src_port)
            host.sendPacket(new_packet)

        listener_A = self.PortListener(self, "A", server_A, 256)
        listener_B = self.PortListener(
            self, "B", server_B, 49713, packetBouncer)

        listener_B.setExpectation(Packet("test packet to B",
                                         server_A.ip, 256,
                                         server_B.ip, 49713))
        listener_A.setExpectation(Packet("test packet to B",
                                         server_B.ip, 49713,
                                         server_A.ip, 256))

        server_A.sendMsg("test packet to B", 256, server_B.ip, 49713)

        self.assertFalse(listener_B.expects_packet, "Packet not received")
        self.assertFalse(
            listener_A.expects_packet,
            "Packet bounce not received")

    def test_loopback(self):
        server = NetworkHost()
        listener = self.PortListener(self, "0", server, 1001)
        listener.setExpectation(
            Packet("test loopback", server.ip, 1001, server.ip, 1001))
        self.assertTrue(
            server.sendMsg("test loopback", 1001, "127.0.0.1", 1001),
            "Packet failed to send")
        self.assertFalse(listener.expects_packet, "Packet not received")


class TestMulticastTreeStructure(unittest.TestCase):

    def test_setup(self):
        """
        Just making sure that nothing faults during setup.
        """
        netReset()

        serv_coord = NetworkHost()
        serv_root = serv_coord

        coord = Coordinator(serv_coord, serv_root.ip, "coord")
        root = Router(serv_root, serv_coord.ip, 5, True, "root")

        for i in range(10):
            server = NetworkHost()
            router = Router(server, serv_coord.ip, False, 3, "r_" + str(i))
            worker = Worker(server, serv_coord.ip, "w_" + str(i))

    def test_program_determinism(self):
        """
        Multiple user-tasks based on the same program should have the same
        result, since they don't depend on the actual values in the memcache.
        """
        netReset()

        serv_coord = NetworkHost("73.222.255.1")
        serv_root = serv_coord

        coord = Coordinator(serv_coord, serv_root.ip, "coord")
        root = Router(serv_root, serv_coord.ip, True, 3, "root")
        tasks = []
        task_ids = []

        for i in range(4):
            server = NetworkHost()
            router = Router(server, serv_coord.ip, False, 2, "r_" + str(i))
        for i in range(7):
            server = NetworkHost()
            worker = Worker(server, serv_coord.ip, "w_" + str(i))

        program = EnclaveProgram(['x', 'y', 'z'], 0.3, 1)
        for i in range(7):
            task = UserTask(program, i)

            tasks.append(task)
            coord.enqueueUserTask(task)

        coord.joinUserTasks()

        prev_value = tasks[0].result
        for task in tasks:
            self.assertEqual(task.result, prev_value)
            prev_value = task.result

    def test_simple_driver(self):
        """ Debugging rig. """
        netReset()

        # IP space:
        #  Driver, Coordinator, and Root Router are on 73.0.0.1
        #  Routers are on 80.0.*.*
        #  Workers are on 90.0.*.*

        serv_coord = NetworkHost("73.0.0.1")
        serv_root = serv_coord

        coord = Coordinator(serv_coord, serv_root.ip, "coord")
        root = Router(serv_root, serv_coord.ip, True, 3, "root")
        tasks = []
        task_ids = []

        for i in range(4):
            server = NetworkHost("80.0")
            router = Router(server, serv_coord.ip, False, 2, "r_" + str(i))
        for i in range(7):
            server = NetworkHost("90.0")
            worker = Worker(server, serv_coord.ip, "w_" + str(i))

        program = EnclaveProgram(['x', 'y', 'z'], 0.3, 1)
        for i in range(7):
            task = UserTask(program, i)

            tasks.append(task)
            coord.enqueueUserTask(task)

        coord.joinUserTasks()

        print("======== Debug Info ========")
        ip_map, packets, failures = getNetworkDebugInfo()
        pprint(ip_map)
        pprint(packets)
        pprint(failures)

        print("======= Task Results =======")
        for task in tasks:
            print(task)

        print("======== Mcast Tree ========")
        print(coord.root.prettyString())


if __name__ == '__main__':
    unittest.main()
