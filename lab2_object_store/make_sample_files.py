"""
make_sample_files.py: generates 128 stand-in sample files (same role as
the original CSC 2025 pictures.tgz) so the labs don't depend on downloading
external material. Run once before Task 2.1.
"""
import os
import random

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pictures")
N_FILES = 128
MIN_SIZE = 2_000
MAX_SIZE = 200_000


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    rng = random.Random(2026)  # fixed seed: everyone in the room gets the same files

    for i in range(N_FILES):
        size = rng.randint(MIN_SIZE, MAX_SIZE)
        path = os.path.join(OUTPUT_DIR, f"img_{i:03d}.bin")
        with open(path, "wb") as f:
            f.write(rng.randbytes(size))

    print(f"Wrote {N_FILES} sample files to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
