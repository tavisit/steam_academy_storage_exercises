"""
Task 2.3 demo: upload a file, kill its primary server, and confirm
cloud_download still succeeds from a replica.

Run after implementing replication in cloud_upload/cloud_download:

    python3 demo_redundancy.py
"""
import os
import sys
import tempfile

from cloud import cloud_download, cloud_upload

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from cloud_lowlevel import h8d, reset, sha1string  # noqa: E402

TEST_NAME = "redundancy-demo.bin"


def primary_server(cloud_name):
    return h8d(sha1string(cloud_name)[0])


def main():
    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "source.bin")
        with open(source, "wb") as f:
            f.write(b"steam academy 2026" * 100)

        cloud_upload(source, TEST_NAME)
        primary = primary_server(TEST_NAME)
        print(f"Uploaded '{TEST_NAME}', primary server is {primary}.")

        print(f"Wiping server {primary} (simulating total node loss)...")
        reset(primary)

        result = os.path.join(tmp, "recovered.bin")
        served_by = cloud_download(TEST_NAME, result)

        if served_by is None:
            print("FAILED: file could not be recovered from any replica.")
            return

        with open(source, "rb") as a, open(result, "rb") as b:
            assert a.read() == b.read(), "recovered file does not match the original!"

        print(f"Recovered '{TEST_NAME}' from server {served_by} (primary {primary} was down).")
        print("Redundancy works: one dead server did not lose the file.")


if __name__ == "__main__":
    main()
