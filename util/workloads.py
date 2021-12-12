from multicast.core import UserTask
from simulators.enclave import *

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
