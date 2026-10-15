import hashlib
import random

SALT = b"fairbooking-kyc"


def make_aadhaar(rng):
    return str(rng.randint(10**11, 10**12 - 1))


def id_hash(aadhaar):
    return hashlib.sha256(SALT + aadhaar.encode()).digest()


class KYC:
    def __init__(self, people):
        self.people = set(people)
        self.used = set()

    def check(self, aadhaar):
        if aadhaar not in self.people:
            return None, "fake identity"
        h = id_hash(aadhaar)
        if h in self.used:
            return None, "identity already used"
        self.used.add(h)
        return h, "ok"


def main():
    rng = random.Random(1)
    a, b = make_aadhaar(rng), make_aadhaar(rng)
    k = KYC([a, b])

    h, msg = k.check(a)
    assert h and msg == "ok"
    print("[PASS] real person is verified")

    h, msg = k.check(a)
    assert h is None and msg == "identity already used"
    print("[PASS] same person cannot register twice")

    h, msg = k.check(make_aadhaar(rng))
    assert h is None and msg == "fake identity"
    print("[PASS] fake Aadhaar number is rejected")

    assert all(a.encode() not in x for x in k.used)
    print("[PASS] only salted hashes are stored, not Aadhaar numbers")

    print("\nAll KYC tests passed.")


if __name__ == "__main__":
    main()
