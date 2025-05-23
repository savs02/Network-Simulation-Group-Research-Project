import time
import numpy as np
import matplotlib.pyplot as plt
from passive_monitoring.passive_monitoring_interface.passive_simulator import PassiveSimulator
from active_monitoring_evolution.ground_truth import GroundTruthNetwork
from passive_monitoring.end_host.end_host_latency_measurement import EndHostEstimation
from passive_monitoring.passive_monitoring_interface.switch_and_packet import Packet

def evolution_0_find_optimal_window(min_window_size=100, max_window_size=1000, window_increment=100, apply_filtering=True, discard_method="median_filter"):
    print("=== Evolution 0: Finding Optimal Window Size (Normal Distribution, No Congestion) ===")

    target_kl = 0.05
    trials_per_window = 10
    simulation_duration = 5

    true_mean = 0.8
    true_std = 0.15

    results = []

    for window_size in range(min_window_size, max_window_size + 1, window_increment):
        print(f"\nTesting window size: {window_size}")
        kl_scores = []

        for trial in range(trials_per_window):
            network = GroundTruthNetwork()
            simulator = PassiveSimulator(network)
            simulator.normal_drop_probability = 0.0

            monitor = EndHostEstimation(
                window_size=window_size,
                apply_filtering=apply_filtering,
                discard_method=discard_method,
                true_mean=true_mean,
                true_std=true_std
            )

            monitor.report_interval = float('inf')
            simulator.attach_sketch(network.DESTINATION, monitor)

            # Custom traffic simulation that attaches true_delay to packets
            start_time = time.time()
            while time.time() - start_time < simulation_duration:
                packet = Packet(network.SOURCE, network.DESTINATION)
                packet.true_delay = network.sample_edge_delay(packet.source, packet.destination)
                # simulate the network delay (but don't sleep, let simulator do that)
                time.sleep(0.001)  # Simulate sending spacing
                simulator.network.destination_switch.receive(packet)
                # print(packet.true_delay)

            # Evaluate estimation
            params = monitor.estimate_parameters()
            est_mean = params['estimated_mean']
            est_std = params['estimated_std']
            if est_mean is None or est_std is None:
                continue

            kl_score = simulator.compare_distribution_parameters(est_mean, est_std)
            kl_scores.append(kl_score)

            if (trial + 1) % 10 == 0:
                print(f"  Completed {trial + 1}/{trials_per_window} trials")

        if kl_scores:
            avg_kl = np.mean(kl_scores)
            results.append((window_size, avg_kl))

            print(f"  Window size: {window_size}")
            print(f"  Average KL score: {avg_kl:.6f}")
            # print(f"  Success rate: {success_rate:.2%}")

            # if avg_kl <= target_kl and success_rate >= 0.8:
            if avg_kl <= target_kl:
                print(f"\n*** Optimal window size found: {window_size} ***")
                break

    print(f"\n=== Evolution 0 Results (filtering: {discard_method})===")
    print("Window Size | Avg KL Score")
    print("--------------------------")
    for window_size, avg_kl in results:
        print(f"{window_size:11d} | {avg_kl:12.6f}")

    optimal_windows = [w for w, kl in results if kl <= target_kl]
    if optimal_windows:
        print(f"\nSmallest window size for achieving KL score ≤ {target_kl}: {min(optimal_windows)}")
    else:
        print(f"\nNo window size achieved the target KL score of {target_kl} consistently.")

    return results

# if __name__ == "__main__":

    # min_window_size = 100
    # max_window_size = 1000
    # window_increment = 100

    # apply_filtering = False
    # discard_method = None


results_dict = {}

results_dict["no_filtering"] = evolution_0_find_optimal_window(50, 500, 50, False, None)
# results_dict["trimmed"] = evolution_0_find_optimal_window(100, 1000, 100, True, "trimmed")
# results_dict["median_filtering"] = evolution_0_find_optimal_window(100, 1000, 100, True, "median_filter")
# results_dict["threshold"] = evolution_0_find_optimal_window(100, 1000, 100, True, "threshold")

# Plotting KL divergence vs. window size for different filtering strategies
plt.figure(figsize=(10, 6))

for method, results in results_dict.items():
    window_sizes = [w for w, kl in results]
    kl_scores = [kl for w, kl in results]
    plt.plot(window_sizes, kl_scores, marker='o', label=method.replace("_", " ").title())

plt.axhline(y=0.05, color='gray', linestyle='--', label='Target KL Threshold (0.05)')
plt.title("Evolution 0: KL Divergence vs. Window Size (Normal)")
plt.xlabel("Window Size")
plt.ylabel("Average KL Divergence")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()