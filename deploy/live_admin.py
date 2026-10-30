"""Local-only access-code hashing and explicit, boot-bound spending authorization."""
import argparse
import getpass
import hashlib
import hmac
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from leakprobe.ui.live_policy import password_hash


def sign_challenge(challenge, key):
    if set(challenge) != {'boot_id', 'policy', 'expires_at', 'limits'} or len(bytes.fromhex(key)) != 32:
        raise ValueError('Invalid challenge or administrator key.')
    return {**challenge, 'signature': hmac.new(bytes.fromhex(key),
            json.dumps(challenge, sort_keys=True, separators=(',', ':')).encode(), hashlib.sha256).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['hash-password', 'sign'])
    parser.add_argument('--challenge', type=Path)
    args = parser.parse_args()
    if args.action == 'hash-password':
        print(password_hash(getpass.getpass('Operator access code (16+ characters): ')))
        return
    if not args.challenge or args.challenge.stat().st_size > 8192:
        parser.error('Provide a downloaded challenge file of at most 8 KiB.')
    challenge = json.loads(args.challenge.read_text(encoding='utf-8'))
    print('Review this immutable spending policy before authorizing:', file=sys.stderr)
    print(json.dumps(challenge, indent=2), file=sys.stderr)
    print('Type AUTHORIZE to grant this process its stated reservation budget:', file=sys.stderr)
    if input() != 'AUTHORIZE':
        raise SystemExit('No authorization produced.')
    permit = sign_challenge(challenge, getpass.getpass('Administrator signing key (64 hex characters): '))
    print(json.dumps(permit, indent=2))


if __name__ == '__main__':
    main()
