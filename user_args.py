import argparse

def parseUserArgs():
    return parser.parse_args()

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
