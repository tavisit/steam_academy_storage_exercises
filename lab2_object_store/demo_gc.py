"""
Task 2.4 demo: simulate a hash-table resize (8 servers -> 4) and show both
halves of the problem: cloud_ls() still lists every name, but a lookup
under the new 4-server table can no longer find most of them, and
cloud_gc() cleans up the copies left stranded on the old, now-unreachable
servers.

Run after implementing h4d/cloud_gc:

    python3 demo_gc.py
"""
import glob
import os
import sys

from cloud import cloud_gc, cloud_ls, cloud_upload, h4d

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from cloud_lowlevel import N_SERVERS, list_names, sha1string  # noqa: E402

PICTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pictures")


def _count_copies(names):
    """Physical copies of exactly `names`, across all servers, scoped to
    this demo's own files since the shared storage root also holds
    whatever other labs have uploaded in the same session."""
    names = set(names)
    return sum(
        1
        for server in range(1, N_SERVERS + 1)
        for name in list_names(server)
        if name in names
    )


def main():
    pictures = sorted(glob.glob(os.path.join(PICTURES_DIR, "*")))[:30]
    if len(pictures) < 30:
        print("Not enough sample files, run make_sample_files.py first.")
        return

    names = [os.path.basename(p) for p in pictures]
    for path, name in zip(pictures, names):
        cloud_upload(path, name)

    before = _count_copies(names)
    print(f"Uploaded {len(names)} files under the OLD 8-server hash table.")
    print(f"Physical copies of these files on disk: {before} (expected {len(names) * 3} = files x 3 replicas)\n")

    print("cloud_ls() after the 'resize' to 4 servers:")
    print(f"  {len(cloud_ls())} names still listed, the bucket index doesn't know")
    print("  or care how many servers the hash table has.\n")

    reachable = sum(1 for name in names if name in list_names(h4d(sha1string(name)[0])))
    print(f"Reachable at their NEW-scheme (4-server) primary location: {reachable}/{len(names)}")
    print(
        "The rest still exist on disk, on whichever of the OLD 8 servers "
        "they originally hashed to, but a lookup that trusts the new "
        "4-server hash table will never look there.\n"
    )

    print("--- dry run ---")
    cloud_gc(dry_run=True)
    after_dry_run = _count_copies(names)
    print(f"Copies of these files still on disk after dry run: {after_dry_run} (should be unchanged: {before})\n")

    print("--- actual GC ---")
    cloud_gc(dry_run=False)
    after = _count_copies(names)
    print(f"\nCopies of these files on disk after GC: {after} (removed {before - after} orphan(s))")
    print(
        "\nNote: GC only REMOVES misplaced copies, it doesn't create the "
        "correct ones. Some files may now be under-replicated at their "
        "new-scheme location. That's exactly what Lab 3 Part 3's cloud_heal is for."
    )


if __name__ == "__main__":
    main()
