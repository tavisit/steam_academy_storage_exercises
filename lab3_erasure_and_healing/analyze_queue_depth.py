"""
analyze_queue_depth.py (Lab 3 Part 4): re-read your own Lab 1 numbers.

Reads ../lab1_measure_your_machine/queue_depth_timings.csv (written by Lab
1 Task 1.3) and asks harder questions of the exact same data.

    python3 analyze_queue_depth.py
"""
import csv
import os

CSV_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "lab1_measure_your_machine", "queue_depth_timings.csv",
)


def load_timings():
    """
    Task 3.3.1, setup: read CSV_PATH (columns: queue_depth, latency_s) and
    return {queue_depth: [latency_s, latency_s, ...]}.
    """
    raise NotImplementedError("load_timings: implement me")


def summarize(timings_by_depth):
    """
    Task 3.3.1, questions 3.3.1a/3.3.1b: for each queue depth (sorted),
    compute and print:
      - number of samples
      - mean latency
      - p50, p95, p99 latency (sort the samples, index by percentile)
      - a throughput estimate: depth / mean(latency_seconds)

    Question 3.3.1a (the "knee"): find the depth where throughput stops
    meaningfully increasing even though latency keeps climbing.

    Optional: if matplotlib is installed, plot throughput and p99 latency
    together against queue depth so the knee is visible at a glance.
    """
    raise NotImplementedError("summarize: implement me")


def main():
    if not os.path.exists(CSV_PATH):
        print(f"{CSV_PATH} not found, run Lab 1 Task 1.3 first.")
        return
    timings = load_timings()
    summarize(timings)


if __name__ == "__main__":
    main()
