import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa

SUITE = b"\x01"
H_LEN = 32


def i2osp(x: int, length: int) -> bytes:
    return x.to_bytes(length, "big")


def os2ip(b: bytes) -> int:
    return int.from_bytes(b, "big")


def mgf1(seed: bytes, length: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < length:
        out += hashlib.sha256(seed + i2osp(counter, 4)).digest()
        counter += 1
    return out[:length]


def keygen(bits: int = 2048):
    key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    priv = key.private_numbers()
    pub = priv.public_numbers
    return {"n": pub.n, "d": priv.d}, {"n": pub.n, "e": pub.e}


def _k(n: int) -> int:
    return (n.bit_length() + 7) // 8


def _encode(n: int, alpha: bytes) -> int:
    k = _k(n)
    mgf_salt = i2osp(k, 4) + i2osp(n, k)
    return os2ip(mgf1(SUITE + b"\x01" + mgf_salt + alpha, k - 1))


def prove(sk: dict, alpha: bytes) -> bytes:
    n, d = sk["n"], sk["d"]
    return i2osp(pow(_encode(n, alpha), d, n), _k(n))


def proof_to_hash(pi: bytes) -> bytes:
    return hashlib.sha256(SUITE + b"\x02" + pi).digest()


def verify(pk: dict, alpha: bytes, pi: bytes):
    n, e = pk["n"], pk["e"]
    if len(pi) != _k(n):
        return None
    s = os2ip(pi)
    if s >= n or pow(s, e, n) != _encode(n, alpha):
        return None
    return proof_to_hash(pi)


def pk_fingerprint(pk: dict) -> bytes:
    return hashlib.sha256(i2osp(pk["n"], _k(pk["n"])) + i2osp(pk["e"], 4)).digest()


def make_alpha(round_id: str, pk: dict) -> bytes:
    return round_id.encode() + b"|" + pk_fingerprint(pk)


def rank_value(beta: bytes) -> float:
    return os2ip(beta) / 2 ** (8 * H_LEN)


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
    for name, (pk, alpha, pi, beta) in published.items():
        assert verify(pk, alpha, pi) == beta
    print("[PASS] every published proof verifies with only the public key")

    sk_a, pk_a = applicants["alice"]
    assert prove(sk_a, make_alpha(round_id, pk_a)) == published["alice"][2]
    print("[PASS] same key + same round -> same proof (cannot re-roll)")

    pk, alpha, pi, _ = published["bob"]
    bad_pi = bytearray(pi)
    bad_pi[-1] ^= 1
    assert verify(pk, alpha, bytes(bad_pi)) is None
    print("[PASS] tampered proof is rejected")

    _, pk_c = applicants["carol"]
    assert verify(pk_c, make_alpha(round_id, pk_c), published["bob"][2]) is None
    print("[PASS] proof made with Bob's key fails under Carol's key")

    new_beta = proof_to_hash(prove(sk_a, make_alpha("ROUND-NEXT", pk_a)))
    assert new_beta != published["alice"][3]
    print("[PASS] a different round gives a different rank")

    print("\nAll VRF tests passed.")


if __name__ == "__main__":
    main()
