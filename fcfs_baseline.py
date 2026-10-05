import random
import statistics
import matplotlib.pyplot as plt

N_SLOTS = 100
N_HUMANS = 900
N_BOTS = 100
BOT_REQUESTS_EACH = 20
N_RUNS = 20

HUMAN_MEAN_DELAY = 6.0
HUMAN_SPREAD = 4.0
BOT_MIN_DELAY, BOT_MAX_DELAY = 0.05, 0.30
BOT_GAP = 0.01
NET_MIN, NET_MAX = 0.02, 0.20


def make_requests(rng):
    requests = []
    for h in range(N_HUMANS):
        delay = max(0.5, rng.gauss(HUMAN_MEAN_DELAY, HUMAN_SPREAD))
        arrival = delay + rng.uniform(NET_MIN, NET_MAX)
        requests.append((arrival, f"human_{h}", False))
    for b in range(N_BOTS):
        start = rng.uniform(BOT_MIN_DELAY, BOT_MAX_DELAY)
        for k in range(BOT_REQUESTS_EACH):
            arrival = start + k * BOT_GAP + rng.uniform(NET_MIN, NET_MAX)
            requests.append((arrival, f"bot_{b}", True))
    return requests


def fcfs_allocate(requests):
    winners = sorted(requests, key=lambda r: r[0])[:N_SLOTS]
    return winners, winners[-1][0]


def run_once(seed):
    rng = random.Random(seed)
    winners, sellout_time = fcfs_allocate(make_requests(rng))
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
    plt.show()


if __name__ == "__main__":
    main()
