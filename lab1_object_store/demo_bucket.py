"""
Task 1.2 demo -- compare cloud_ls() (one lookup) against a brute-force scan
of every server (N_SERVERS lookups), and check they agree.

Run after implementing cloud_ls():

    python3 demo_bucket.py
"""
import os
import sys
import time

from cloud import cloud_ls

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from cloud_lowlevel import N_SERVERS, list_names  # noqa: E402


def brute_force_ls():
    names = set()
    for server in range(1, N_SERVERS + 1):
        names.update(list_names(server))
    return sorted(names)


def main():
    t0 = time.perf_counter()
    bucket_result = sorted(cloud_ls())
    t1 = time.perf_counter()
    scan_result = brute_force_ls()
    t2 = time.perf_counter()

    print(f"cloud_ls()      : {len(bucket_result)} names, 1 lookup,           {t1 - t0:.6f}s")
    print(f"brute-force scan: {len(scan_result)} names, {N_SERVERS} lookups,           {t2 - t1:.6f}s")

    if bucket_result == scan_result:
        print("\nMatch -- the bucket index is a faithful, single-lookup namespace.")
    else:
        only_in_bucket = set(bucket_result) - set(scan_result)
        only_in_scan = set(scan_result) - set(bucket_result)
        print("\nMISMATCH.")
        print(f"  only in bucket index: {sorted(only_in_bucket)}")
        print(f"  only in brute-force scan: {sorted(only_in_scan)}")


if __name__ == "__main__":
    main()
