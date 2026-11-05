import math
import random
import statistics
import matplotlib.pyplot as plt

N_SLOTS = 100
N_RUNS = 20
P_BAD = 0.3
MEAN_COST = 300
DEPOSITS = [0, 50, 100, 250, 500, 1000, 2000]


def run(dep, seed):
    rng = random.Random(seed)
    miss = 0
    for _ in range(N_SLOTS):
        if rng.random() < P_BAD and rng.expovariate(1 / MEAN_COST) > dep:
            miss += 1
    return miss


def main():
    print(f"Winners per run: {N_SLOTS} | Runs per deposit: {N_RUNS}")
    print(f"Model: {P_BAD:.0%} of winners face a problem costing Exp(mean Rs {MEAN_COST}); "
          "they skip if the cost is above the deposit\n")
    print(f"{'Deposit (Rs)':>12} | {'No-shows / 100':>14} | {'Expected':>8} | {'Forfeited (Rs)':>14}")
    print("-" * 58)

    xs, ys = [], []
    for d in DEPOSITS:
        m = [run(d, s) for s in range(N_RUNS)]
        exp = 100 * P_BAD * math.exp(-d / MEAN_COST)
        print(f"{d:>12} | {statistics.mean(m):>14.1f} | {exp:>8.1f} | {statistics.mean(m) * d:>14.0f}")
        xs.append(d)
        ys.append(statistics.mean(m))

    assert ys[0] > ys[-1]
    assert all(a >= b - 2 for a, b in zip(ys, ys[1:]))
    print("\n[PASS] no-shows fall as the deposit grows")

    plt.figure(figsize=(6, 4))
    plt.plot(xs, ys, "o-", color="#1f77b4")
    plt.xlabel("Deposit (Rs)")
    plt.ylabel("No-shows per 100 winners")
    plt.title("Deposit size vs no-shows")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
