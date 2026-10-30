"""Generate an operator password verifier locally; never sends credentials anywhere."""
import argparse
import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from leakprobe.ui.live_policy import password_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['hash-password'])
    parser.parse_args()
    print(password_hash(getpass.getpass('Operator access code (16+ characters): ')))


if __name__ == '__main__':
    main()
