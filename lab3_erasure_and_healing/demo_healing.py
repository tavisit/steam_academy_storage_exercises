"""
Part 3 demo (tasks 3.2.1-3.2.3): upload files with Lab 2's replicated cloud_upload,
fail one node, check what's DEGRADED/LOST, then heal and re-check.

Run after implementing cloud_check/cloud_heal (and after Lab 2's
cloud_upload already replicates to 3 servers):

    python3 demo_healing.py
"""
import glob
import os
import sys
import tempfile

from cloud_ec import cloud_check, cloud_heal

OBJECT_STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lab2_object_store")
sys.path.insert(0, OBJECT_STORE_DIR)
from cloud import cloud_upload  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from cloud_lowlevel import reset  # noqa: E402

N_TEST_FILES = 20
FAILED_SERVER = 3


def main():
    pictures = sorted(glob.glob(os.path.join(OBJECT_STORE_DIR, "pictures", "*")))[:N_TEST_FILES]
    if len(pictures) < N_TEST_FILES:
        print("Not enough sample files, run make_sample_files.py in lab2_object_store/ first.")
        return

    names = [os.path.basename(p) for p in pictures]
    for path, name in zip(pictures, names):
        cloud_upload(path, name)

    print(f"Uploaded {len(names)} files with replication.\n")
    print(f"--- wiping server {FAILED_SERVER} (simulated node failure) ---")
    reset(FAILED_SERVER)

    statuses = {name: cloud_check(name) for name in names}
    counts = {"OK": 0, "DEGRADED": 0, "LOST": 0}
    for status in statuses.values():
        counts[status] += 1
    print(f"\nAfter failure: {counts}")

    degraded = [name for name, status in statuses.items() if status == "DEGRADED"]
    print(f"\n--- healing {len(degraded)} DEGRADED file(s) ---")
    for name in degraded:
        cloud_heal(name)

    statuses_after = {name: cloud_check(name) for name in names}
    counts_after = {"OK": 0, "DEGRADED": 0, "LOST": 0}
    for status in statuses_after.values():
        counts_after[status] += 1
    print(f"\nAfter healing: {counts_after}")


if __name__ == "__main__":
    main()
