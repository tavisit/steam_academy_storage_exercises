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

    TODO: open CSV_PATH and iterate over it with csv.DictReader (each
    row is a dict with string values, so convert row["queue_depth"] to
    int and row["latency_s"] to float). Group the latencies by their
    queue depth (a collections.defaultdict(list) makes the "append to
    a list that may not exist yet" part easy, but a plain dict with
    .setdefault(depth, []) works too).
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

    TODO, using the header already printed and `prev_throughput`/`knee`
    below: for each depth in sorted(timings_by_depth):
      1. Get that depth's list of latencies. Convert each to
         milliseconds and sort them (percentiles need sorted data).
      2. Compute mean latency (statistics.mean works on the raw, un-
         sorted seconds list too), and p50/p95/p99: for a percentile p,
         index into the sorted list at position
         int(len(sorted_list) * p / 100), clamped so it never runs past
         the last index.
      3. Compute throughput as depth / mean(latency_in_SECONDS, not ms).
      4. Print this row (matching the header's column widths), then
         check the "knee": if this is not the first depth and this
         throughput is less than 1.05x the PREVIOUS depth's throughput,
         and you haven't already found a knee, remember this depth as
         `knee`. Update `prev_throughput` for the next iteration either
         way.
      After the loop, if `knee` was found, print a sentence naming it.

    Then the matplotlib part: wrap `import matplotlib.pyplot as plt` in
    a try/except ImportError (print a one-line fallback message and
    return if it's missing). Otherwise, build the same depths/
    throughputs/p99s lists again, plot throughput on one y-axis and p99
    latency on a second (ax.twinx()) against depth on the x-axis (a log
    scale reads better here), and save the figure to
    "queue_depth_knee.png".
    """
    print(
        f"{'depth':>6} {'ops':>6} {'mean(ms)':>10} {'p50(ms)':>9} "
        f"{'p95(ms)':>9} {'p99(ms)':>9} {'throughput(ops/s)':>18}"
    )
    prev_throughput = None
    knee = None

    raise NotImplementedError("summarize: implement me")


def main():
    if not os.path.exists(CSV_PATH):
        print(f"{CSV_PATH} not found, run Lab 1 Task 1.3 first.")
        return
    timings = load_timings()
    summarize(timings)


if __name__ == "__main__":
    main()
