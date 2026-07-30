"""
analyze_queue_depth.py -- Lab 3C: re-read your own Lab 2 numbers.

Reads ../lab2_measure_your_machine/queue_depth_timings.csv (written by Lab
2 Task 2.4) and asks harder questions of the exact same data.

    python3 analyze_queue_depth.py
"""
import csv
import os

CSV_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "lab2_measure_your_machine", "queue_depth_timings.csv",
)


def load_timings():
    """
    Task 3C, setup: read CSV_PATH (columns: queue_depth, latency_s) and
    return {queue_depth: [latency_s, latency_s, ...]}.
    """
    raise NotImplementedError("load_timings: implement me")


def summarize(timings_by_depth):
    """
    Task 3C.1/3C.2: for each queue depth (sorted), compute and print:
      - number of samples
      - mean latency
      - p50, p95, p99 latency (sort the samples, index by percentile)
      - a throughput estimate: depth / mean(latency_seconds)

    Task 3C.1 (the "knee"): find the depth where throughput stops
    meaningfully increasing even though latency keeps climbing.

    Optional: if matplotlib is installed, plot throughput and p99 latency
    together against queue depth so the knee is visible at a glance.
    """
    raise NotImplementedError("summarize: implement me")


def main():
    if not os.path.exists(CSV_PATH):
        print(f"{CSV_PATH} not found -- run Lab 2 Task 2.4 first.")
        return
    timings = load_timings()
    summarize(timings)


if __name__ == "__main__":
    main()
