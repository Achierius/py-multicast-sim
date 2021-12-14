import matplotlib.pyplot as plt
import multiprocessing as mp
from benchmark import *
import statistics


bench_metrics.append("n_packets_root")
n_trials = 8
b = 3 # Branching factor of routers in the tree
max_tree_height = 6 # Does not include worker nodes

# Dictionaries mapping tree heights to lists containing the sum of packets touched
# by the root router for each trial
tree_trial_scores = {}
flat_trial_scores = {}

# Means and standard deviation of the score lists for each trial
tree_trial_means  = []
tree_trial_stdevs = []
flat_trial_means  = []
flat_trial_stdevs = []

# I guess these have to be global to be accessible to the processes?
tree_trials_L = []
flat_trials_L = []
tree_scores_D = {}
flat_scores_D = {}

def trial_fn(tree_scores, flat_scores):
    for h in range(1, max_tree_height):
        # Create a balanced tree of *internal* height h:
        # i.e. not including the root node or workers
        n_workers = b ** (h + 1)
        # Could use the binary trick of next power up - 1, but this is clearer
        n_routers = sum([b ** (i + 1) for i in range(0, h)])

        # Create a 2-high (internal height 0), non-multicasted, non-sharded tree
        # to simulate the current status quo implementation
        n_flat_workers = n_workers

        tree = bench(False,
                     #fruitsOfMyLabor(n_workers * 2)(),
                     working_sets(512, 1, 4, 5)(),
                     n_routers,
                     n_workers,
                     b,
                     b,
                     True)
        tree_n_packets_root = tree[0]

        flat = bench(False,
                    #posterboard(n_workers * 2)(),
                     working_sets(512, 1, 4, 5)(),
                    0,
                    n_workers,
                    n_workers,
                    n_workers,
                    False)
        flat_n_packets_root = flat[0]

        tree_scores[h].append(tree_n_packets_root)
        flat_scores[h].append(flat_n_packets_root)


if __name__ == '__main__':
    mp.set_start_method('spawn')

    with mp.Manager() as manager:
        tree_scores_D = manager.dict()
        flat_scores_D = manager.dict()
        for h in range(1, max_tree_height):
            tree_scores_D[h] = manager.list()
            flat_scores_D[h] = manager.list()

        processes = []
        for t in range(n_trials):
            p = mp.Process(target=trial_fn, args=(tree_scores_D, flat_scores_D,))
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

        # Convert IPC structures into useable lists/dicts
        #tree_trials_L = list(tree_trials_L)
        #flat_trials_L = list(flat_trials_L)
        tree_scores_D = dict(tree_scores_D)
        flat_scores_D = dict(flat_scores_D)
        for h in range(1, max_tree_height):
            tree_scores_D[h] = list(tree_scores_D[h])
            flat_scores_D[h] = list(flat_scores_D[h])
        for h in range(1, max_tree_height):
            tree_trial_scores[h] = []
            flat_trial_scores[h] = []
            for t in range(n_trials):
                tree_trial_scores[h].append(tree_scores_D[h][t])
                flat_trial_scores[h].append(flat_scores_D[h][t])
            # Average out the recorded scores across all N_TRIALS trials
            tree_trial_means.append(statistics.mean(tree_trial_scores[h]))
            tree_trial_stdevs.append(statistics.stdev(tree_trial_scores[h]))
            flat_trial_means.append(statistics.mean(flat_trial_scores[h]))
            flat_trial_stdevs.append(statistics.stdev(flat_trial_scores[h]))

    x = range(1, max_tree_height)

    #plt.figure()
    #plt.title("Bottleneck packet throughput, DSM Tree vs. Flat")
    fig, (ax_tree, ax_flat) = plt.subplots(nrows=1, ncols=2, sharey=True)
    fig.suptitle("Bottleneck packet throughput vs. tree height")

    ax_tree.set_title("Balanced, sharded, multicast tree")
    ax_tree.errorbar(x, tree_trial_means, yerr=tree_trial_stdevs, fmt='--o',
                     c='green', capthick=1)
    ax_tree.set_yscale('log')

    ax_flat.set_title("Flat broadcast domain")
    ax_flat.errorbar(x, flat_trial_means, yerr=flat_trial_stdevs, fmt='--o',
                     c='red', capthick=1)
    ax_flat.set_yscale('log')

    plt.show()
