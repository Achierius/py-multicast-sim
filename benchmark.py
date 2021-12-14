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
          max_children, max_routers_root, max_children_root,
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
    root = Router(serv_root, serv_coord.ip, True, max_routers_root,
                  "root", sharding)

    workers = []
    routers = []

    workload_tasks = []
    task_ids = []

    for i in range(n_routers):
        server = NetworkHost("80.0")
        router = Router(server, serv_coord.ip, False, max_children,
                        "r_" + str(i), sharding)
        routers.append(router)

    # Max # of workers that can fit in the tree
    worker_capacity = max_children + (n_routers * (max_children - 1))

    # Add as many workers as the router tree can allegedly handle
    for i in range(min(n_workers, worker_capacity)):
        server = NetworkHost("90.0")
        worker = Worker(server, serv_coord.ip, "w_" + str(i))
        workers.append(worker)

    # Allocate the rest to root :)
    coord.max_children = n_workers # Force root to accept them
    for i in range(worker_capacity, n_workers):
        server = NetworkHost("90.0")
        worker = Worker(server, serv_coord.ip, "w_" + str(i))
        workers.append(worker)

    ## Used to pre-init all dicts to have keys to avoid deadlock
    #empty_keydict = {}
    #for task in workload:
    #    for key in workload.keyspace:
    #        task_keys[key] = 0

    #for router in routers:
    #    for child in router.child_task_keys.keys():
    #        router.child_task_keys = dict(empty_keydict)

    for task in workload:
        workload_tasks.append(task)
        coord.enqueueUserTask(task)
        sleep(0.01)

    coord.joinUserTasks() # Wait for enclaves to finish execution

    ip_map, packets, failures = getNetworkDebugInfo()
    metrics = []
    if bench_metrics:
        for m in bench_metrics:
            metrics.append(
                benchmark_stats[m](
                    print_to_console,
                    coord,
                    root,
                    workload_tasks,
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

def bench_topThroughputPackets(
        percentile: float, # [0, 1]
        console,
        coord,
        root,
        tasks,
        ip_map,
        packet_list,
        failure_info):
    #assert percentile <= 1 and percentile >= 0,\
    #       f"Invalid percentile {percentile}"

    def br(s): return colored(str(s), 'green')
    def res(s): return colored(str(s), 'blue')

    root_ip = root.host.ip

    ips = {}

    for packet in packet_list:
        if packet.src in ips:
            ips[packet.src] += 1
        else:
            ips[packet.src] = 1
        if packet.dst in ips:
            ips[packet.dst] += 1
        else:
            ips[packet.dst] = 1

    # just cause i make routers start with 80, save for the root one
    throughput_counts = [v for k, v in ips.items() if k.startswith("80")]
    throughput_counts.append(ips[root_ip])

    throughput_counts.sort()
    if percentile == -1.0:
        val_at_percentile = throughput_counts
    elif percentile == 1.0:
        val_at_percentile = max(throughput_counts)
    else:
        val_at_percentile = throughput_counts[int(len(throughput_counts)*percentile)]

    if console:
        print(
            f"""{br('[')}"""
            f"""Num. packets handled by {percentile*100}-percentile router: """
            f"""{res(val_at_percentile)}"""
            f"""{br(']')}""")

    return val_at_percentile


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
    'top_half_packets':\
        lambda *args, **kw: bench_topThroughputPackets(0.5, *args, *kw),
    'top_quartile_packets':\
        lambda *args, **kw: bench_topThroughputPackets(0.75, *args, *kw),
    'top_decile_packets':\
        lambda *args, **kw: bench_topThroughputPackets(0.90, *args, *kw),
    'top_5pct_packets':\
        lambda *args, **kw: bench_topThroughputPackets(0.95, *args, *kw),
    'top_percentile_packets':\
        lambda *args, **kw: bench_topThroughputPackets(0.99, *args, *kw),
    'maximum_packets':\
        lambda *args, **kw: bench_topThroughputPackets(1.00, *args, *kw),
    'print_tree': bench_showTree,
    'dump_tasks': bench_dumpTasks,
    'dump_packets': bench_dumpPackets}

workloads = {
    'fruits_of_my_labor': fruitsOfMyLabor, 'posterboard': posterboard,
    'monic': monic, '2x10': lambda n, t: working_sets(n, t, 2, 10),
    '4x5': lambda n, t: working_sets(n, t, 4, 5),
    '1x20': lambda n, t: working_sets(n, t, 1, 20)
}

bench_metrics = []

if __name__ == "__main__":
    args = parseUserArgs()
    bench_metrics = args.metrics
    bench(True,  # Print to console
          workloads[args.workload](args.n_workers * 2, 5)(),
          args.n_routers,
          args.n_workers,
          args.max_children,
          args.max_children_root,
          args.max_children_root,
          args.sharding)
