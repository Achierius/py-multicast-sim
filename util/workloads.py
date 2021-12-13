from multicast.core import UserTask
from simulators.enclave import *
from random import randrange

##### Workloads #####


def posterboard(n, time_factor):
    """ Yields tasks containing the same program back n times. """
    program = EnclaveProgram(['x', 'y', 'z'], 0.3, time_factor)

    iteration = 0

    def generator():
        nonlocal iteration
        while iteration < n:
            yield UserTask(program, iteration)
            iteration += 1
    return generator


def fruitsOfMyLabor(n, time_factor):
    """ Generates a new program (i.e. new key distribution) for each task. """
    fruits = ["apple", "orange", "pear", "peach", "mango", "rhubarb", "kiwi"]
    fruits = [(fruit,) for fruit in fruits]

    iteration = 0

    def generator():
        nonlocal iteration
        while iteration < n:
            yield UserTask(EnclaveProgram(fruits, 0.6, time_factor), iteration)
            iteration += 1
    return generator


def working_sets(n_tasks, time_factor, n_working_sets, keys_per_set):
    """
    Assigns (independent) programs from one of N_WORKING_SETS different and
    mutually exclusive sets of keys, each of the same size, KEYS_PER_SET.
    The set used is selected randomly each time.
    """
    working_sets = []
    for s in range(n_working_sets):
        working_set = []
        for k in range(keys_per_set):
            key = s*keys_per_set + k
            working_set.append(key)
        working_sets.append(working_set)

    iteration = 0
    next_working_set = randrange(n_working_sets)

    def generator():
        nonlocal iteration
        nonlocal next_working_set
        while iteration < n_tasks:
            working_set = working_sets[next_working_set]
            yield UserTask(
                    EnclaveProgram(working_set, 0.6, time_factor),
                    iteration)
            iteration += 1
            next_working_set = randrange(n_working_sets)
    return generator


def monic(n, time_factor):
    """ Generates (independent) programs with a single key. """

    iteration = 0

    def generator():
        nonlocal iteration
        while iteration < n:
            yield UserTask(EnclaveProgram(['M'], 0.6, time_factor), iteration)
            iteration += 1
    return generator
