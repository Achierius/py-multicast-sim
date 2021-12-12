from pprint import pprint
from time import sleep
from termcolor import colored
from numpy import repeat

from multicast.core import *
from multicast.coordinator import *
from multicast.router import *
from multicast.worker import *

from simulators.network import *
from util.workloads import *
from util.user_args import *


def bench(workload, n_routers, n_workers,
          max_children, max_children_root,
          sharding):
    netReset()

    #max_children = 4
    #max_children_root = 2
    #n_routers = 9
    #n_workers = 27

    serv_coord = NetworkHost("73.0.0.1")
    serv_root = serv_coord

    coord = Coordinator(serv_coord, serv_root.ip, "coord")
    root = Router(serv_root, serv_coord.ip, True, max_children_root,
                  "root", sharding)

    tasks = []
    task_ids = []

    for i in range(n_routers):
        server = NetworkHost("80.0")
        router = Router(server, serv_coord.ip, False, max_children,
                        "r_" + str(i), sharding)
    for i in range(n_workers):
        server = NetworkHost("90.0")
        worker = Worker(server, serv_coord.ip, "w_" + str(i))

    for task in workload:
        tasks.append(task)
        coord.enqueueUserTask(task)
#        #sleep(0.1)

    coord.joinUserTasks()

    ip_map, packets, failures = getNetworkDebugInfo()
    #print("======== Debug Info ========")
    # pprint(ip_map)
    # pprint(failures)

    if args.metrics:
        for b in args.metrics:
            benchmark_stats[b](coord, root, tasks, ip_map, packets, failures)


def bench_nPackets(coord, root, tasks, ip_map, packet_list, failure_info):
    def br(s): return colored(str(s), 'green')
    def res(s): return colored(str(s), 'blue')

    print(f"{br('[')}Total packets sent: {res(len(packet_list))}{br(']')}")


def bench_nRootPackets(coord, root, tasks, ip_map, packet_list, failure_info):
    def br(s): return colored(str(s), 'green')
    def res(s): return colored(str(s), 'blue')

    root_ip = root.host.ip

    ls = [x for x in packet_list if x.src is root_ip or x.dst is root_ip]
    print(
        f"{br('[')}Total packets handled by root router: {res(len(ls))}{br(']')}")


def bench_showTree(coord, root, tasks, ip_map, packet_list, failure_info):
    print("======== Mcast Tree ========")
    print(coord.root.prettyString())


def bench_dumpTasks(coord, root, tasks, ip_map, packet_list, failure_info):
    print("======= Task Results =======")
    pprint(tasks)
    # for task in tasks:
    #    print(task)


def bench_dumpPackets(coord, root, tasks, ip_map, packet_list, failure_info):
    print("======= Sent Packets =======")
    pprint(packet_list)


benchmark_stats = {
    'n_packets': bench_nPackets,
    'n_packets_root': bench_nRootPackets,
    'print_tree': bench_showTree,
    'dump_tasks': bench_dumpTasks,
    'dump_packets': bench_dumpPackets}

workloads = {
    'fruits_of_my_labor': fruitsOfMyLabor(128), 'posterboard': posterboard(8)
}

args = parser.parse_args()
bench(workloads[args.workload](),
      args.n_routers,
      args.n_workers,
      args.max_children,
      args.max_children_root if args.max_children_root else args.max_children,
      args.sharding)
