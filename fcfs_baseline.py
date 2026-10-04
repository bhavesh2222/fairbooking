"""
Phase 1 - Step 1: Naive First-Come-First-Served (FCFS) baseline + bot simulator.

What this script shows:
    When slots are given out in the order requests arrive, fast automated
    "bots" grab far more slots than their share of the population.

How it works (simple version):
    1. The booking window opens at time t = 0.
    2. Every applicant sends request(s). Each request has an arrival time.
         - Humans: react in a few seconds, send ONE request.
         - Bots:   react in milliseconds, send MANY requests very fast.
    3. All requests are sorted by arrival time.
    4. The first N_SLOTS requests win a slot. (No identity check, no lottery
       - that is exactly the weakness of the naive system.)
    5. We count what share of slots went to bots.

Run:
    python fcfs_baseline.py
"""

import random
import statistics
import matplotlib.pyplot as plt

# ---------------- Settings (change these to experiment) ----------------
N_SLOTS = 100            # number of slots released
N_HUMANS = 900           # number of human applicants
N_BOTS = 100             # number of bot applicants (10% of everyone)
BOT_REQUESTS_EACH = 20   # how many requests each bot fires
N_RUNS = 20              # repeat the experiment with different random seeds

# Human reaction time (seconds): most people take 2-15 s to click "Book"
HUMAN_MEAN_DELAY = 6.0
HUMAN_SPREAD = 4.0
# Bot reaction time (seconds): scripts fire within ~50-300 ms
BOT_MIN_DELAY, BOT_MAX_DELAY = 0.05, 0.30
BOT_GAP = 0.01           # 10 ms between two requests from the same bot
# Network delay added to every request (seconds)
NET_MIN, NET_MAX = 0.02, 0.20


def make_requests(rng):
    """Create a list of (arrival_time, applicant_id, is_bot) for one run."""
    requests = []

    # Humans: one request each, a few seconds after opening
    for h in range(N_HUMANS):
        delay = max(0.5, rng.gauss(HUMAN_MEAN_DELAY, HUMAN_SPREAD))
        arrival = delay + rng.uniform(NET_MIN, NET_MAX)
        requests.append((arrival, f"human_{h}", False))

    # Bots: many requests each, starting within milliseconds
    for b in range(N_BOTS):
        start = rng.uniform(BOT_MIN_DELAY, BOT_MAX_DELAY)
        for k in range(BOT_REQUESTS_EACH):
            arrival = start + k * BOT_GAP + rng.uniform(NET_MIN, NET_MAX)
            requests.append((arrival, f"bot_{b}", True))

    return requests


def fcfs_allocate(requests):
    """Naive FCFS: sort by arrival time, first N_SLOTS requests win."""
    requests_sorted = sorted(requests, key=lambda r: r[0])
    winners = requests_sorted[:N_SLOTS]
    sellout_time = winners[-1][0]          # when the last slot was taken
    return winners, sellout_time


def run_once(seed):
    rng = random.Random(seed)
    requests = make_requests(rng)
    winners, sellout_time = fcfs_allocate(requests)

    bot_slots = sum(1 for (_, _, is_bot) in winners if is_bot)
    human_winners = len({aid for (_, aid, is_bot) in winners if not is_bot})
    return {
        "bot_share": bot_slots / N_SLOTS,
        "sellout_time": sellout_time,
        "human_winners": human_winners,
    }


def main():
    results = [run_once(seed) for seed in range(N_RUNS)]

    bot_pop_share = N_BOTS / (N_BOTS + N_HUMANS)
    avg_bot_share = statistics.mean(r["bot_share"] for r in results)
    avg_sellout = statistics.mean(r["sellout_time"] for r in results)
    avg_humans = statistics.mean(r["human_winners"] for r in results)

    print("=== Naive FCFS baseline ===")
    print(f"Slots: {N_SLOTS} | Humans: {N_HUMANS} | Bots: {N_BOTS} | Runs: {N_RUNS}")
    print(f"Bots' share of population : {bot_pop_share:6.1%}")
    print(f"Bots' share of slots (avg): {avg_bot_share:6.1%}")
    print(f"Humans who got a slot     : {avg_humans:.1f} out of {N_HUMANS}")
    print(f"All slots gone after      : {avg_sellout:.2f} seconds")

    # ---- Chart: population share vs slot share ----
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ["Share of applicants", "Share of slots won"]
    bots = [bot_pop_share * 100, avg_bot_share * 100]
    humans = [100 - bots[0], 100 - bots[1]]
    ax.bar(labels, bots, label="Bots", color="#d62728")
    ax.bar(labels, humans, bottom=bots, label="Humans", color="#1f77b4")
    for i, v in enumerate(bots):
        ax.text(i, v / 2, f"{v:.0f}%", ha="center", color="white", fontweight="bold")
    ax.set_ylabel("Percent")
    ax.set_title("Naive FCFS: bots vs humans")
    ax.legend()
    plt.tight_layout()
    plt.savefig("fcfs_bot_share.png", dpi=150)
    print("Chart saved as fcfs_bot_share.png")


if __name__ == "__main__":
    main()
