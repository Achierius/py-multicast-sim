import functools
import argparse
from pprint import pprint
from time import sleep
from termcolor import colored

from network import *
from multicast_core import *
from multicast_coordinator import *
from multicast_router import *
from multicast_worker import *
from enclave import *

# NOTE BENE: All the harness/superstructure bits are at the top of this file,
#            the actual benchmark scenarios are down below,

bench_flags = None
bench_opts = None

def setBenchOpts(flags, opts):
    """ I hate this but I want them to be in different files """
    global bench_flags
    global bench_opts
    bench_flags = flags
    bench_opts = opts


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

    if bench_flags.show_tree:
        print("======== Mcast Tree ========")
        print(coord.root.prettyString())
        

    if bench_flags.show_tasks:
        print("======= Task Results =======")
        for task in tasks:
            print(task)

    if bench_opts:
        for b in bench_opts:
            benchmark_stats[b](serv_coord.ip, serv_root.ip, ip_map, packets, failures)


def benchmark(func):
    """Performs setup / teardown & prints outputs."""
    @functools.wraps(func)
    def benchmark_decorator(*args, **kwargs):
        netReset()

        serv_coord = NetworkHost("73.0.0.1")
        serv_root = serv_coord

        tasks = []
        task_ids = []

        args[0].serv_coord = serv_coord
        args[0].serv_root = serv_root
        args[0].tasks = tasks
        args[0].task_ids = task_ids

        rv = func(*args, **kwargs)

        ip_map, packets, failures = getNetworkDebugInfo()
        #print("======== Debug Info ========")
        #pprint(ip_map)
        #pprint(packets)
        #pprint(failures)

        if bench_flags.show_tree:
            print("======== Mcast Tree ========")
            print(args[0].coord.root.prettyString())

        if bench_flags.show_tasks:
            print("======= Task Results =======")
            for task in tasks:
                print(task)

        if bench_opts:
            for b in bench_opts:
                benchmark_stats[b](serv_coord.ip, serv_root.ip, ip_map, packets, failures)

        return rv
    return benchmark_decorator


@benchmark
def veryScalable(harness, tasks): # TODO disable sharding
    """
    The pre-existing implementation; disables sharding and has no routers
    besides the root router.
    Pretend you're running this inside of a docker instance with 30 separate
    shells for extra immersion.
    """
    coord = Coordinator(harness.serv_coord, harness.serv_root.ip, "coord")
    harness.coord = coord
    root = Router(harness.serv_root, harness.serv_coord.ip, True, 100, "root")

    for i in range(30):
        server = NetworkHost("90.0")
        worker = Worker(server, harness.serv_coord.ip, "w_" + str(i))

    for task in tasks:
        print(task)
        harness.tasks.append(task)
        coord.enqueueUserTask(task)
        #sleep(0.1)

    coord.joinUserTasks()


@benchmark
def runBintree5(harness, tasks):
    """
    Create a simple binary tree of nodes with depth 5:
        1 coordinator, 14 routers, 16 workers.
    IP space:
        Driver, Coordinator, and Root Router are on 73.0.0.1
        Routers are on 80.0.*.*
        Workers are on 90.0.*.*
    """
    coord = Coordinator(harness.serv_coord, harness.serv_root.ip, "coord")
    harness.coord = coord
    root = Router(harness.serv_root, harness.serv_coord.ip, True, 2, "root")

    for i in range(14):
        server = NetworkHost("80.0")
        router = Router(server, harness.serv_coord.ip, False, 2, "r_" + str(i))
    for i in range(16):
        server = NetworkHost("90.0")
        worker = Worker(server, harness.serv_coord.ip, "w_" + str(i))

    for task in tasks:
        harness.tasks.append(task)
        coord.enqueueUserTask(task)
#        #sleep(0.1)

    coord.joinUserTasks()


@benchmark
def runTrintree4(harness, tasks):
    """
    Create a simple trinary tree of nodes with depth 4:
        1 coordinator, 9 routers, 27 workers.
    IP space:
        Driver, Coordinator, and Root Router are on 73.0.0.1
        Routers are on 80.0.*.*
        Workers are on 90.0.*.*
    """
    b_factor = 3

    coord = Coordinator(harness.serv_coord, harness.serv_root.ip, "coord")
    harness.coord = coord
    root = Router(harness.serv_root, harness.serv_coord.ip, True, b_factor, "root")

    for i in range(9):
        server = NetworkHost("80.0")
        router = Router(server, harness.serv_coord.ip, False, b_factor, "r_" + str(i))
    for i in range(27):
        server = NetworkHost("90.0")
        worker = Worker(server, harness.serv_coord.ip, "w_" + str(i))

    for task in tasks:
        harness.tasks.append(task)
        coord.enqueueUserTask(task)
#        #sleep(0.1)

    coord.joinUserTasks()


##### Stats #####

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

# POST SCRIPTUM: I deeply regret moving this to another file, I'll fix it tmrw
