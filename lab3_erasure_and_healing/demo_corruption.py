"""
3B demo (task 4) -- silent corruption. cloud_check only confirms a copy
*exists*; it says nothing about whether its bytes are still correct. A
checksum is the only thing that notices.

Run after implementing checksum_store/checksum_verify:

    python3 demo_corruption.py
"""
import os
import sys
import tempfile

from cloud_ec import _replica_servers, checksum_store, checksum_verify, cloud_check

LAB1_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lab1_object_store")
sys.path.insert(0, LAB1_DIR)
from cloud import cloud_upload  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from cloud_lowlevel import download, pathmap, sealname  # noqa: E402

TEST_NAME = "corruption-demo.bin"


def main():
    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "source.bin")
        with open(source, "wb") as f:
            f.write(os.urandom(20_000))

        cloud_upload(source, TEST_NAME)
        checksum_store(TEST_NAME, source)
        print(f"Uploaded '{TEST_NAME}' and stored its checksum.")
        print("cloud_check BEFORE corruption:", cloud_check(TEST_NAME))

        server = _replica_servers(TEST_NAME)[0]
        physical_path = os.path.join(pathmap(server), sealname(TEST_NAME))
        with open(physical_path, "r+b") as f:
            byte = f.read(1)
            f.seek(0)
            f.write(bytes([byte[0] ^ 0xFF]))
        print(f"\nFlipped one byte directly on disk on server {server} "
              f"(bypassing cloud_upload entirely -- simulates silent bit rot).")

        print("cloud_check AFTER corruption: ", cloud_check(TEST_NAME),
              " <-- still OK. The file exists and is the right size.")

        corrupted_copy = os.path.join(tmp, "corrupted_copy.bin")
        download(server, TEST_NAME, corrupted_copy)
        matches = checksum_verify(TEST_NAME, corrupted_copy)
        print(f"checksum_verify on that same copy:  {matches}  <-- only the checksum knows.")


if __name__ == "__main__":
    main()
