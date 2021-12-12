import numpy as np
import numpy.random as rand
import threading
from time import sleep

class EnclaveProgram:

    def __init__(self, keyspace, length_factor: float, work_factor: float):
        """
        Higher LENGTH_FACTOR => longer program sequences (range: 0-1)
        WORK_FACTOR => expected number of milliseconds spent executing each key
        """
        self.keyspace = keyspace
        self.work_factor = work_factor
        self.keys = []

        rng = rand.default_rng()
        n_keys = 1 + rng.geometric(p = (1 - length_factor))
        for _ in range(n_keys):
            next_key = self.keyspace[rng.integers(0, len(keyspace))]
            self.keys.append(next_key)


    def __repr__(self):
        return self.__str__()


    def __str__(self):
        return f"<Program: {self.keys}>"


def enclaveExecute(program: EnclaveProgram, key_update_fn, callback_fn):
    """
    Spawns a new thread to simulate the execution of the mock program PROGRAM.
    Each EnclaveProgram contains an ordered list of keys along with a 'work
    factor' which scales the execution time of executions of that program.
    'Executing' this program consists of iterating through the list of keys,
    sleeping for an exponentially-distributed amount of time on each, and after
    waking each time 'updating' the value of the key: i.e. setting its value in
    MEMCACHE to a random value, then calling CALLBACK with the key as a
    parameter to let the parent Worker node know to propogate the key update
    throughout the multicast tree.
    """

    base_sleep = 0.01 # 1ms
    sleep_rng = rand.default_rng()
    value_rng = rand.default_rng()
    result = 0

    prev_value = 0
    for key in program.keys:
        sleep(base_sleep*sleep_rng.exponential(1/program.work_factor))
        new_value = value_rng.integers(-65536, 65536) # not inclusive
        new_value = hash(key)
        result //= 2
        result += new_value
        key_update_fn(key, prev_value, program)
        prev_value = new_value
    callback_fn(result)
