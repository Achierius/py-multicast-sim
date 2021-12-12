from pprint import pprint
from time import sleep
from termcolor import colored
from numpy import repeat

from network import *
from multicast_core import *
from multicast_coordinator import *
from multicast_router import *
from multicast_worker import *

from benchmark_scenarios import *
from workloads import *
from user_args import *


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
    #pprint(ip_map)
    #pprint(packets)
    #pprint(failures)

    if args.show_tree:
        print("======== Mcast Tree ========")
        print(coord.root.prettyString())


    if args.show_tasks:
        print("======= Task Results =======")
        for task in tasks:
            print(task)

    if args.metrics:
        for b in args.metrics:
            benchmark_stats[b](serv_coord.ip, serv_root.ip, ip_map, packets, failures)


def bench_nPackets(coord_ip, root_ip, ip_map, packet_list, failure_info):
    br = lambda s: colored(str(s), 'green')
    res = lambda s: colored(str(s), 'blue')

    print(f"{br('[')}Total packets sent: {res(len(packet_list))}{br(']')}")


def bench_nRootPackets(coord_ip, root_ip, ip_map, packet_list, failure_info):
    br = lambda s: colored(str(s), 'green')
    res = lambda s: colored(str(s), 'blue')

    ls = [x for x in packet_list if x.src is root_ip or x.dst is root_ip]
    print(f"{br('[')}Total packets handled by root router: {res(len(ls))}{br(']')}")


benchmark_stats = {
          'n_packets': bench_nPackets
        , 'n_packets_root': bench_nRootPackets
        }

workloads = {
          'fruits_of_my_labor': fruitsOfMyLabor(128)
        , 'posterboard': posterboard(8)
        }

args = parser.parse_args()
bench(workloads[args.workload](), args.n_routers, args.n_workers, args.max_children,
        args.max_children_root if args.max_children_root else args.max_children,
        args.sharding)
