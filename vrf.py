"""
Phase 1 - Step 2: A working Verifiable Random Function (VRF).

Scheme: RSA-FDH-VRF with SHA-256, following RFC 9381, Section 4.
(Educational implementation for this project; not audited for production.)

Plain-English idea:
    - Each applicant has a secret key (sk) and a public key (pk).
    - Input "alpha" = round_id + applicant's public key fingerprint.
    - prove(sk, alpha)  -> proof "pi"   (only the secret-key holder can make it)
    - proof_to_hash(pi) -> "beta"       (the random-looking rank value)
    - verify(pk, alpha, pi) -> True/False (ANYONE can check it with the public key)

Why it fits FairBooking:
    - Unpredictable: beta cannot be computed without sk, and the round_id
      does not exist before the round, so nobody can pre-compute rankings.
    - Unique: for one (sk, alpha) there is exactly one valid pi, so an
      applicant cannot "re-roll" for a better rank.
    - Verifiable: after the lottery, anyone can check every published rank.

Run:
    python vrf.py
"""

import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa

SUITE = b"\x01"   # RSA-FDH-VRF-SHA256 suite string (RFC 9381)
H_LEN = 32        # SHA-256 output length in bytes


# ---------- small helper functions from RFC 8017 (RSA standard) ----------
def i2osp(x: int, length: int) -> bytes:
    """Integer -> fixed-length big-endian bytes."""
    return x.to_bytes(length, "big")


def os2ip(b: bytes) -> int:
    """Bytes -> integer."""
    return int.from_bytes(b, "big")


def mgf1(seed: bytes, length: int) -> bytes:
    """Mask Generation Function 1 using SHA-256: stretches seed to `length` bytes."""
    out = b""
    counter = 0
    while len(out) < length:
        out += hashlib.sha256(seed + i2osp(counter, 4)).digest()
        counter += 1
    return out[:length]


# ---------- key generation ----------
def keygen(bits: int = 2048):
    """Return (secret_key, public_key) as plain integers dictionaries."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    priv = key.private_numbers()
    pub = priv.public_numbers
    sk = {"n": pub.n, "d": priv.d}
    pk = {"n": pub.n, "e": pub.e}
    return sk, pk


def _k(n: int) -> int:
    """Length of the modulus n in bytes."""
    return (n.bit_length() + 7) // 8


def _encode(n: int, alpha: bytes) -> int:
    """Hash alpha into a number below n (the 'full domain hash' step)."""
    k = _k(n)
    mgf_salt = i2osp(k, 4) + i2osp(n, k)
    em = mgf1(SUITE + b"\x01" + mgf_salt + alpha, k - 1)
    return os2ip(em)


# ---------- the three VRF operations ----------
def prove(sk: dict, alpha: bytes) -> bytes:
    """Make the proof pi = (hash of alpha) ^ d mod n. Needs the SECRET key."""
    n, d = sk["n"], sk["d"]
    m = _encode(n, alpha)
    s = pow(m, d, n)
    return i2osp(s, _k(n))


def proof_to_hash(pi: bytes) -> bytes:
    """Turn the proof into the 32-byte random output beta."""
    return hashlib.sha256(SUITE + b"\x02" + pi).digest()


def verify(pk: dict, alpha: bytes, pi: bytes):
    """Check a proof with the PUBLIC key. Returns beta if valid, else None."""
    n, e = pk["n"], pk["e"]
    if len(pi) != _k(n):
        return None
    s = os2ip(pi)
    if s >= n:
        return None
    m = pow(s, e, n)                       # undo the secret-key step
    if m != _encode(n, alpha):             # must equal hash of alpha
        return None
    return proof_to_hash(pi)


# ---------- FairBooking helpers ----------
def pk_fingerprint(pk: dict) -> bytes:
    """Short unique ID for a public key."""
    return hashlib.sha256(i2osp(pk["n"], _k(pk["n"])) + i2osp(pk["e"], 4)).digest()


def make_alpha(round_id: str, pk: dict) -> bytes:
    """VRF input for one applicant in one round."""
    return round_id.encode() + b"|" + pk_fingerprint(pk)


def rank_value(beta: bytes) -> float:
    """Map beta to a number in [0, 1). Lower rank value = earlier in the queue."""
    return os2ip(beta) / 2 ** (8 * H_LEN)


# ---------- demo and self-tests ----------
def main():
    print("Generating keys for 3 applicants (2048-bit RSA)...")
    applicants = {name: keygen() for name in ["alice", "bob", "carol"]}
    round_id = "ROUND-2026-10-05-VACCINE-CHENNAI"

    print(f"\nRound ID: {round_id}\n")
    published = {}
    for name, (sk, pk) in applicants.items():
        alpha = make_alpha(round_id, pk)
        pi = prove(sk, alpha)
        beta = proof_to_hash(pi)
        published[name] = (pk, alpha, pi, beta)
        print(f"{name:6s} rank = {rank_value(beta):.6f}   beta = {beta.hex()[:16]}...")

    order = sorted(published, key=lambda nm: rank_value(published[nm][3]))
    print("\nLottery order:", " -> ".join(order))

    print("\n--- Self-tests ---")
    # 1. Valid proofs verify and give the same beta
    for name, (pk, alpha, pi, beta) in published.items():
        assert verify(pk, alpha, pi) == beta
    print("[PASS] every published proof verifies with only the public key")

    # 2. Deterministic: proving again gives the identical proof (no re-rolls)
    sk_a, pk_a = applicants["alice"]
    assert prove(sk_a, make_alpha(round_id, pk_a)) == published["alice"][2]
    print("[PASS] same key + same round -> same proof (cannot re-roll)")

    # 3. Tampered proof is rejected
    pk, alpha, pi, _ = published["bob"]
    bad_pi = bytearray(pi); bad_pi[-1] ^= 1
    assert verify(pk, alpha, bytes(bad_pi)) is None
    print("[PASS] tampered proof is rejected")

    # 4. Someone else's proof cannot be claimed under your key
    _, pk_c = applicants["carol"]
    assert verify(pk_c, make_alpha(round_id, pk_c), published["bob"][2]) is None
    print("[PASS] proof made with Bob's key fails under Carol's key")

    # 5. New round -> completely different, unpredictable rank
    new_beta = proof_to_hash(prove(sk_a, make_alpha("ROUND-NEXT", pk_a)))
    assert new_beta != published["alice"][3]
    print("[PASS] a different round gives a different rank")

    print("\nAll VRF tests passed.")


if __name__ == "__main__":
    main()
