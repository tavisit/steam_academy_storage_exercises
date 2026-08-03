"""
3A demo: upload a file with erasure coding, delete one chunk and
reconstruct it, then delete two chunks and show that fails.

Run after implementing cloud_ec_upload/cloud_ec_download:

    python3 demo_ec.py
"""
import filecmp
import os
import sys
import tempfile

from cloud_ec import _ec_servers, cloud_ec_download, cloud_ec_upload

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from cloud_lowlevel import delete  # noqa: E402

TEST_NAME = "ec-demo.bin"


def main():
    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "source.bin")
        with open(source, "wb") as f:
            f.write(os.urandom(50_000))

        print("--- upload ---")
        cloud_ec_upload(source, TEST_NAME)

        print("\n--- download, nothing missing ---")
        recovered = os.path.join(tmp, "recovered_full.bin")
        cloud_ec_download(TEST_NAME, recovered)
        print("matches original:", filecmp.cmp(source, recovered, shallow=False))

        print("\n--- delete ONE chunk, then download ---")
        servers = _ec_servers(TEST_NAME)
        delete(servers[0], f"{TEST_NAME}.chunk0")
        recovered_1 = os.path.join(tmp, "recovered_one_missing.bin")
        ok = cloud_ec_download(TEST_NAME, recovered_1)
        if ok:
            print("matches original:", filecmp.cmp(source, recovered_1, shallow=False))

        print("\n--- delete a SECOND chunk, then download ---")
        delete(servers[1], f"{TEST_NAME}.chunk1")
        recovered_2 = os.path.join(tmp, "recovered_two_missing.bin")
        ok = cloud_ec_download(TEST_NAME, recovered_2)
        print("download succeeded:", ok, "(should be False)")


if __name__ == "__main__":
    main()
