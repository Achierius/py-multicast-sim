import matplotlib.pyplot as plt
import multiprocessing as mp
import statistics
import pickle
from itertools import chain
from benchmark import *
from simulators.network import *


# I guess these have to be global to be accessible to the processes?
tree_trials_L = []
tree_scores_D = {}

max_tree_height = 3
n_trials = 8
b_f = 4
total_nodes = sum([b_f ** (i + 1) for i in range(0, max_tree_height + 1)])
#iv_range = range(1, total_nodes // 2, step) # Independent variable range
iv_range = list(range(b_f, b_f**2, 1))\
         + list(range(b_f**2, b_f**3, b_f))\
         + list(range(b_f**3, total_nodes // b_f, b_f**2))
#workload = working_sets(total_nodes * 2, 0.1, 4, 5)

bench_metrics.extend([
    "top_half_packets",
    "top_quartile_packets",
    "top_decile_packets",
    "top_5pct_packets"])

def trial_fn(b, scores):
    for n in iv_range:
        # First fix the number of nodes we're allocating to work as routers
        n_routers = n
        # Then make the rest workers
        n_workers = total_nodes - n_routers
        # Then figure out how many more nodes the root needs to handle
        leftover_workers = ( b               # Curr root-router capacity
                           + (b * n_routers) # Total router capacity (sans root)
                           - n_workers       # Total utilization by workers
                           - n_routers)      # Total util. by non-root routers
        leftover_workers = max(0, -leftover_workers) # Sign correct & clip

        workload = working_sets(total_nodes, 0.01, 4, 8)#posterboard(total_nodes, 0.1)
        score = bench(False,
                      workload(),
                      n_routers,
                      n_workers,
                      b,
                      b,
                      b + leftover_workers, # Give root room to handle extras
                      True)

        scores[n][0].append(score[0])
        scores[n][1].append(score[1])
        scores[n][2].append(score[2])
        scores[n][3].append(score[3])
        #print(f"===============");
        #print(f"===== {n} =====");
        #print(f"===============");
        #ip_map, packets, failures = getNetworkDebugInfo()
        #pprint(packets)
        #pprint(failures)
        #print(f"=== failure ===");
        #print(score[4])

def calc_and_show_fig():
    mp.set_start_method('spawn')

    # Dictionaries mapping node counts to lists containing the sum of packets touched
    # by the root router for each trial
    # {int} -> [int]
    percentile_50_scores = {}
    percentile_75_scores = {}
    percentile_90_scores = {}
    percentile_95_scores = {}

    # Means and standard deviation of the score lists for each trial
    percentile_50_means  = []
    percentile_50_stdevs = []
    percentile_75_means  = []
    percentile_75_stdevs = []
    percentile_90_means  = []
    percentile_90_stdevs = []
    percentile_95_means  = []
    percentile_95_stdevs = []

    with mp.Manager() as manager:
        tree_scores_D = manager.dict()
        for n in iv_range:
            tree_scores_D[n] = manager.list([manager.list(),
                                             manager.list(),
                                             manager.list(),
                                             manager.list()])

        # Run N_TRIALS simulations to smooth out randomness
        processes = []
        for t in range(n_trials):
            p = mp.Process(target=trial_fn, args=(3,tree_scores_D,))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()

        # Convert IPC structures into useable lists/dicts
        tree_scores_D = dict(tree_scores_D)
        for n in iv_range:
            tree_scores_D[n] = list(tree_scores_D[n])
            tree_scores_D[n][0] = list(tree_scores_D[n][0])
            tree_scores_D[n][1] = list(tree_scores_D[n][1])
            tree_scores_D[n][2] = list(tree_scores_D[n][2])
            tree_scores_D[n][3] = list(tree_scores_D[n][3])

        # Transpose data and calculate statistics from it
        for n in iv_range:
            percentile_50_scores[n] = []
            percentile_75_scores[n] = []
            percentile_90_scores[n] = []
            percentile_95_scores[n] = []
            for t in range(n_trials):
                for i in range(4):
                    percentile_50_scores[n].append(tree_scores_D[n][0][t])
                    percentile_75_scores[n].append(tree_scores_D[n][1][t])
                    percentile_90_scores[n].append(tree_scores_D[n][2][t])
                    percentile_95_scores[n].append(tree_scores_D[n][3][t])
            percentile_50_means.append(statistics.mean(percentile_50_scores[n]))
            percentile_50_stdevs.append(statistics.stdev(percentile_50_scores[n]))
            percentile_75_means.append(statistics.mean(percentile_75_scores[n]))
            percentile_75_stdevs.append(statistics.stdev(percentile_75_scores[n]))
            percentile_90_means.append(statistics.mean(percentile_90_scores[n]))
            percentile_90_stdevs.append(statistics.stdev(percentile_90_scores[n]))
            percentile_95_means.append(statistics.mean(percentile_95_scores[n]))
            percentile_95_stdevs.append(statistics.stdev(percentile_95_scores[n]))

    stats = {
            "50_m": percentile_50_means
          , "50_sd": percentile_50_stdevs
          , "75_m": percentile_75_means
          , "75_sd": percentile_75_stdevs
          , "90_m": percentile_90_means
          , "90_sd": percentile_90_stdevs
          , "95_m": percentile_95_means
          , "95_sd": percentile_95_stdevs
            }

    save_stats(stats)
    plot_stats(stats)

def save_stats(stats):
    with open("last_stats", 'wb') as file:
        pickle.dump(stats, file)

def load_stats():
    with open("last_stats", 'rb') as file:
        return pickle.load(file)

def plot_stats(stats):
    #plt.figure()
    #plt.title("Bottleneck packet throughput, DSM Tree vs. Flat")
    #fig, (ax_tree, ax_flat) = plt.subplots(nrows=1, ncols=1)
    plt.figure()
    ax = plt.axes()

    #fig.suptitle("Bottleneck packet throughput vs. # routing nodes")
    plt.title("Packet-routing burden vs. # of routing nodes")

    plt.plot(iv_range, stats["50_m"], 'D--r', label="50th percentile")
    plt.plot(iv_range, stats["75_m"], 'D--y', label="75th percentile")
    plt.plot(iv_range, stats["90_m"], 'D--g', label="90th percentile")
    plt.plot(iv_range, stats["95_m"], 'D--b', label="95th percentile")

    #ax_tree.set_title("Balanced, sharded, multicast tree")
    #plt.errorbar(iv_range, tree_trial_means, yerr=tree_trial_stdevs,
    #                 fmt='--o', c='green', capthick=1)
    ax.set_yscale('log')
    ax.legend()

    plt.savefig("last_fig.png", format="png")

    plt.show()
