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


def bench(print_to_console, workload, n_routers, n_workers,
          max_children, max_children_root,
          sharding):
    assert isinstance(n_routers, int),\
        f"n_routers must be an integer, but is {n_routers}"
    assert isinstance(n_workers, int),\
        f"n_workers must be an integer, but is {n_workers}"
    assert isinstance(max_children, int),\
        f"max_children must be an integer, but is {max_children}"
    assert isinstance(max_children_root, int),\
        f"max_children_root must be an integer, but is {max_children_root}"

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
        sleep(0.001)

    coord.joinUserTasks() # Wait for enclaves to finish execution

    ip_map, packets, failures = getNetworkDebugInfo()
    metrics = []
    if bench_metrics:
        for b in bench_metrics:
            metrics.append(
                benchmark_stats[b](
                    print_to_console,
                    coord,
                    root,
                    tasks,
                    ip_map,
                    packets,
                    failures))

    return metrics


def bench_nPackets(
        console,
        coord,
        root,
        tasks,
        ip_map,
        packet_list,
        failure_info):
    def br(s): return colored(str(s), 'green')
    def res(s): return colored(str(s), 'blue')

    if console:
        print(f"{br('[')}Total packets sent: {res(len(packet_list))}{br(']')}")
    return len(packet_list)


def bench_nRootPackets(
        console,
        coord,
        root,
        tasks,
        ip_map,
        packet_list,
        failure_info):
    def br(s): return colored(str(s), 'green')
    def res(s): return colored(str(s), 'blue')

    root_ip = root.host.ip
    ls = [x for x in packet_list if x.src is root_ip or x.dst is root_ip]
    if console:
        print(
            f"{br('[')}Total packets handled by root router: {res(len(ls))}{br(']')}")
    return len(ls)


def bench_showTree(
        console,
        coord,
        root,
        tasks,
        ip_map,
        packet_list,
        failure_info):
    tree = coord.root.prettyString()
    if console:
        print("======== Mcast Tree ========")
        print(tree)
    return tree


def bench_dumpTasks(
        console,
        coord,
        root,
        tasks,
        ip_map,
        packet_list,
        failure_info):
    if console:
        print("======= Task Results =======")
        pprint(tasks)
    return tasks
    # for task in tasks:
    #    print(task)


def bench_dumpPackets(
        console,
        coord,
        root,
        tasks,
        ip_map,
        packet_list,
        failure_info):
    if console:
        print("======= Sent Packets =======")
        pprint(packet_list)
    return packet_list


benchmark_stats = {
    'n_packets': bench_nPackets,
    'n_packets_root': bench_nRootPackets,
    'print_tree': bench_showTree,
    'dump_tasks': bench_dumpTasks,
    'dump_packets': bench_dumpPackets}

workloads = {
    'fruits_of_my_labor': fruitsOfMyLabor(128), 'posterboard': posterboard(8)
}

bench_metrics = []

if __name__ == "__main__":
    args = parseUserArgs()
    bench_metrics = args.metrics
    bench(True,  # Print to console
          workloads[args.workload](),
          args.n_routers,
          args.n_workers,
          args.max_children,
          args.max_children_root,
          args.sharding)
