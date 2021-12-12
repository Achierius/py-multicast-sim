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

parser.add_argument('-t', '--topology', metavar='TOPOLOGY', default='bintree_5',
        dest='run_target', action='store')

parser.add_argument('-b', '--bench', metavar='METRIC',
        dest='benchmarks', action='append')

parser.add_argument('-w', '--workload',
        default='fruits_of_my_labor', metavar='WORKLOAD',
        dest='workload', action='store')

parser.add_argument('--show_tree', action='store_true')
parser.add_argument('--show_tasks', action='store_true')

args = parser.parse_args()

setBenchOpts(args, args.benchmarks)
run_targets[args.run_target](lambda: None, workloads[args.workload]())
