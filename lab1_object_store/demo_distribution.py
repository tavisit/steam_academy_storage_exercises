"""
Task 1.1 demo -- upload every sample file and see how evenly the DHT spreads
them across the 8 servers.

Run after implementing the primary-placement part of cloud_upload:

    python3 make_sample_files.py
    python3 demo_distribution.py
"""
import glob
import os
import sys

from cloud import cloud_upload

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from cloud_lowlevel import N_SERVERS, list_names  # noqa: E402

PICTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pictures")


def main():
    files = sorted(glob.glob(os.path.join(PICTURES_DIR, "*")))
    if not files:
        print("No sample files found -- run make_sample_files.py first.")
        return

    for path in files:
        cloud_upload(path, os.path.basename(path))

    print(f"Uploaded {len(files)} files. Distribution across servers:\n")
    for server in range(1, N_SERVERS + 1):
        count = len(list_names(server))
        print(f"  server {server}: {count:3d} files  {'#' * count}")


if __name__ == "__main__":
    main()
