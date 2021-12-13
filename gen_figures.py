import matplotlib.pyplot as plt
from benchmark import *
import statistics

#plt.plot([1, 2, 3, 4])
#plt.ylabel('some numbers')
#plt.show()

bench_metrics.append("n_packets_root")
n_trials = 10
b = 3 # Branching factor of routers in the tree
max_tree_height = 6 # May need multiprocessing at some point
# Dictionaries mapping tree heights to lists containing the sum of packets touched
# by the root router for each trial
tree_trial_scores = {}
flat_trial_scores = {}

# Means and standard deviation of the score lists for each trial
tree_trial_means  = []
tree_trial_stdevs = []
flat_trial_means  = []
flat_trial_stdevs = []


for h in range(1, max_tree_height):
    # Set up summations for trials
    tree_trial_scores[h] = []
    flat_trial_scores[h] = []

    # Create a balanced tree of *internal* height h:
    # i.e. not including the root node or workers
    n_workers = b ** (h + 1)
    # Could use the binary trick of next power up - 1, but this is clearer
    n_routers = sum([b ** (i + 1) for i in range(0, h)])

    # Create a 2-high (internal height 0), non-multicasted, non-sharded tree
    # to simulate the current status quo implementation
    n_flat_workers = n_workers + n_routers
    for trial in range(n_trials):
        tree_scores = bench(False,
                            fruitsOfMyLabor(n_workers * 2)(),
                            n_routers,
                            n_workers,
                            b,
                            b,
                            True)
        tree_n_packets_root = tree_scores[0]

        flat_scores = bench(False,
                           posterboard(n_workers)(),
                           0,
                           n_flat_workers,
                           n_flat_workers,
                           n_flat_workers,
                           False)
        flat_n_packets_root = flat_scores[0]

        # Add scores to respective sums
        tree_trial_scores[h].append(tree_n_packets_root)
        flat_trial_scores[h].append(flat_n_packets_root)
    # Average out the recorded scores across all N_TRIALS trials

    tree_trial_means.append(statistics.mean(tree_trial_scores[h]))
    tree_trial_stdevs.append(statistics.stdev(tree_trial_scores[h]))
    flat_trial_means.append(statistics.mean(flat_trial_scores[h]))
    flat_trial_stdevs.append(statistics.stdev(flat_trial_scores[h]))


print("Tree means: ", tree_trial_means)
print("Tree stdvs: ", tree_trial_stdevs)
print("Flat means: ", flat_trial_means)
print("Flat stdvs: ", flat_trial_stdevs)

x = range(1, max_tree_height)

#plt.figure()
#plt.title("Bottleneck packet throughput, DSM Tree vs. Flat")
fig, (ax_tree, ax_flat) = plt.subplots(nrows=1, ncols=2)
fig.suptitle("Bottleneck packet throughput vs. tree height")

ax_tree.set_title("Balanced, sharded, multicast tree")
ax_tree.errorbar(x, tree_trial_means, yerr=tree_trial_stdevs, fmt='--o',
                 c='green')

ax_flat.set_title("Flat broadcast domain")
ax_flat.errorbar(x, flat_trial_means, yerr=flat_trial_stdevs, fmt='--o',
                 c='red')

plt.show()
