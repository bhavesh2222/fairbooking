import hashlib
import random
import statistics
import time
import matplotlib.pyplot as plt

import vrf
from kyc import KYC, make_aadhaar
from fcfs_baseline import run_once as fcfs_once

N_SLOTS = 100
N_HUMANS = 900
N_BOTS = 100
BOT_TRIES = 20
N_ROUNDS = 10
DEPOSIT = 500
BITS = 1024


def make_people(rng):
    people = []
    for i in range(N_HUMANS):
        people.append({"name": f"human_{i}", "bot": False, "id": make_aadhaar(rng)})
    for i in range(N_BOTS):
        people.append({"name": f"bot_{i}", "bot": True, "id": make_aadhaar(rng)})
    return people


def register(people, rng):
    k = KYC([p["id"] for p in people])
    reg, stats = [], {"tries": 0, "ok": 0, "dup": 0, "fake": 0}

    for p in people:
        tries = [p["id"]]
        if p["bot"]:
            for t in range(BOT_TRIES - 1):
                tries.append(p["id"] if t % 2 else make_aadhaar(rng))

        for aid in tries:
            stats["tries"] += 1
            h, msg = k.check(aid)
            if msg == "ok":
                sk, pk = vrf.keygen(BITS)
                reg.append({"name": p["name"], "bot": p["bot"], "sk": sk, "pk": pk})
                stats["ok"] += 1
            elif msg == "identity already used":
                stats["dup"] += 1
            else:
                stats["fake"] += 1
    return reg, stats


def run_round(reg, rid):
    entries = []
    for a in reg:
        alpha = vrf.make_alpha(rid, a["pk"])
        pi = vrf.prove(a["sk"], alpha)
        beta = vrf.verify(a["pk"], alpha, pi)
        assert beta is not None
        entries.append((vrf.rank_value(beta), a["name"], a["bot"]))
    entries.sort()
    win = entries[:N_SLOTS]
    assert len({w[1] for w in win}) == N_SLOTS
    bots = sum(1 for w in win if w[2])
    return bots / N_SLOTS, N_SLOTS - bots


def main():
    rng = random.Random(7)
    people = make_people(rng)

    t0 = time.time()
    reg, st = register(people, rng)
    print("=== Registration (KYC + deposit) ===")
    print(f"Attempts            : {st['tries']}")
    print(f"Accepted            : {st['ok']}")
    print(f"Rejected (reused ID): {st['dup']}")
    print(f"Rejected (fake ID)  : {st['fake']}")
    print(f"Deposit locked      : {st['ok'] * DEPOSIT} (Rs {DEPOSIT} each)")
    print(f"Keygen time         : {time.time() - t0:.1f} s")

    vrf_share, vrf_humans = [], []
    for r in range(N_ROUNDS):
        rid = "ROUND-" + hashlib.sha256(f"seed-{r}".encode()).hexdigest()[:16]
        s, h = run_round(reg, rid)
        vrf_share.append(s)
        vrf_humans.append(h)

    fcfs = [fcfs_once(s) for s in range(N_ROUNDS)]
    fcfs_share = statistics.mean(f["bot_share"] for f in fcfs)
    fcfs_humans = statistics.mean(f["human_winners"] for f in fcfs)

    pop = N_BOTS / (N_BOTS + N_HUMANS)
    print(f"\n=== FCFS vs VRF lottery ({N_ROUNDS} rounds) ===")
    print(f"Bots' share of applicants : {pop:6.1%}")
    print(f"Bots' share of slots, FCFS: {fcfs_share:6.1%}")
    print(f"Bots' share of slots, VRF : {statistics.mean(vrf_share):6.1%}"
          f"  (min {min(vrf_share):.0%}, max {max(vrf_share):.0%})")
    print(f"Humans with a slot, FCFS  : {fcfs_humans:.1f} / {N_SLOTS}")
    print(f"Humans with a slot, VRF   : {statistics.mean(vrf_humans):.1f} / {N_SLOTS}")
    print("All VRF proofs verified, no slot given twice.")

    fig, ax = plt.subplots(figsize=(6, 4))
    names = ["Share of\napplicants", "Slots won\nFCFS", "Slots won\nVRF lottery"]
    vals = [pop * 100, fcfs_share * 100, statistics.mean(vrf_share) * 100]
    ax.bar(names, vals, color=["#7f7f7f", "#d62728", "#1f77b4"])
    for i, v in enumerate(vals):
        ax.text(i, v + 2, f"{v:.0f}%", ha="center", fontweight="bold")
    ax.set_ylim(0, 110)
    ax.set_ylabel("Bots (%)")
    ax.set_title("Bot share: FCFS vs VRF lottery")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
