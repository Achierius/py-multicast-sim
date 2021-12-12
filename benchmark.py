import argparse
from pprint import pprint
from time import sleep
from termcolor import colored
from numpy import repeat

from network import *
from multicast_core import *
from multicast_coordinator import *
from multicast_router import *
from multicast_worker import *
from enclave import *

from benchmark_scenarios import *


##### Workloads #####

def posterboard(n):
    """ Yields tasks containing the same program back n times. """
    program = EnclaveProgram(['x', 'y', 'z'], 0.3, 1)

    iteration = 0
    def generator():
        nonlocal iteration
        while iteration < n:
            yield UserTask(program, iteration)
            iteration += 1
    return generator


def fruitsOfMyLabor(n):
    """ Generates a new program (i.e. new key distribution) for each task. """
    fruits = ["apple", "orange", "pear", "peach", "mango", "rhubarb", "kiwi"]
    fruits = [(fruit,) for fruit in fruits]

    iteration = 0
    def generator():
        nonlocal iteration
        while iteration < n:
            yield UserTask(EnclaveProgram(fruits, 0.6, 10), iteration)
            iteration += 1
    return generator


##### Stats #####


workloads = {
          'fruits_of_my_labor': fruitsOfMyLabor(128)
        , 'posterboard': posterboard(8)
        }

run_targets = {
          'bintree_5': runBintree5
        , 'trintree_4': runTrintree4
        , 'very_scalable': veryScalable
        }


parser = argparse.ArgumentParser(description=
        'Benchmark multicast implementations')

parser.add_argument('-r', '--routers', metavar='N_ROUTERS', default=0,
        dest='n_routers', type=int, action='store')

parser.add_argument('-e', '--enclaves', metavar='N_WORKERS', default=1,
        dest='n_workers', type=int, action='store')

parser.add_argument('-b', '--branch', metavar='BRANCH_FACTOR', default=1024,
        dest='max_children', type=int, action='store')

parser.add_argument('--root_branch', metavar='ROOT_BRANCH_FACTOR',
        dest='max_children_root', type=int, action='store')

parser.add_argument('-m', '--metric', metavar='METRIC',
        dest='metrics', action='append')

parser.add_argument('-w', '--workload',
        default='fruits_of_my_labor', metavar='WORKLOAD',
        dest='workload', action='store')

parser.add_argument('--disable_sharding',
        dest='sharding', action='store_false')

parser.add_argument('--show_tree', action='store_true')
parser.add_argument('--show_tasks', action='store_true')

args = parser.parse_args()

setBenchOpts(args, args.metrics)

bench(workloads[args.workload](), args.n_routers, args.n_workers, args.max_children,
        args.max_children_root if args.max_children_root else args.max_children,
        args.sharding)

#run_targets[args.run_target](lambda: None, workloads[args.workload]())
