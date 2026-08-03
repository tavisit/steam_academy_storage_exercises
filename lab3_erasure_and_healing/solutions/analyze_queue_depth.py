"""
analyze_queue_depth.py (Lab 3C): solution.

    python3 analyze_queue_depth.py
"""
import csv
import os
import statistics
from collections import defaultdict

# walk up from this file until a `common/` sibling turns up: works
# whether this file stays at its committed depth (.../solutions/) or
# gets copied up to replace the stub (.../), same as every other
# solutions/*.py file
_dir = os.path.dirname(os.path.abspath(__file__))
while not os.path.isdir(os.path.join(_dir, "common")):
    _dir = os.path.dirname(_dir)
CSV_PATH = os.path.join(_dir, "lab2_measure_your_machine", "queue_depth_timings.csv")


def load_timings():
    timings = defaultdict(list)
    with open(CSV_PATH) as f:
        for row in csv.DictReader(f):
            timings[int(row["queue_depth"])].append(float(row["latency_s"]))
    return timings


def _percentile(sorted_values_ms, pct):
    idx = min(len(sorted_values_ms) - 1, int(len(sorted_values_ms) * pct / 100))
    return sorted_values_ms[idx]


def summarize(timings_by_depth):
    print(
        f"{'depth':>6} {'ops':>6} {'mean(ms)':>10} {'p50(ms)':>9} "
        f"{'p95(ms)':>9} {'p99(ms)':>9} {'throughput(ops/s)':>18}"
    )

    prev_throughput = None
    knee = None
    for depth in sorted(timings_by_depth):
        lats = timings_by_depth[depth]
        lats_ms = sorted(lat * 1000 for lat in lats)
        mean_ms = statistics.mean(lats_ms)
        p50 = _percentile(lats_ms, 50)
        p95 = _percentile(lats_ms, 95)
        p99 = _percentile(lats_ms, 99)
        throughput = depth / statistics.mean(lats)

        print(
            f"{depth:>6} {len(lats):>6} {mean_ms:>10.3f} {p50:>9.3f} "
            f"{p95:>9.3f} {p99:>9.3f} {throughput:>18.1f}"
        )

        if prev_throughput is not None and knee is None and throughput < prev_throughput * 1.05:
            knee = depth
        prev_throughput = throughput

    if knee is not None:
        print(
            f"\nThroughput stops meaningfully improving around queue depth "
            f"{knee}, but p99 keeps climbing well past that point. That gap "
            f"is the difference between 'busy' and 'saturated'."
        )

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib not installed, skipping the plot; the table above has everything you need.)")
        return

    depths = sorted(timings_by_depth)
    throughputs = [d / statistics.mean(timings_by_depth[d]) for d in depths]
    p99s = [_percentile(sorted(lat * 1000 for lat in timings_by_depth[d]), 99) for d in depths]

    fig, ax1 = plt.subplots()
    ax1.plot(depths, throughputs, marker="o", label="throughput (ops/s)")
    ax1.set_xlabel("queue depth")
    ax1.set_ylabel("throughput (ops/s)")
    ax1.set_xscale("log", base=2)

    ax2 = ax1.twinx()
    ax2.plot(depths, p99s, marker="x", color="red", label="p99 latency (ms)")
    ax2.set_ylabel("p99 latency (ms)")

    fig.legend(loc="upper left", bbox_to_anchor=(0.12, 0.88))
    fig.tight_layout()
    out_path = "queue_depth_knee.png"
    fig.savefig(out_path)
    print(f"\nPlot saved to {out_path}")


def main():
    if not os.path.exists(CSV_PATH):
        print(f"{CSV_PATH} not found, run Lab 2 Task 2.3 first.")
        return
    timings = load_timings()
    summarize(timings)


if __name__ == "__main__":
    main()
