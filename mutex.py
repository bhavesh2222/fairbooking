import heapq
import random
import statistics
import matplotlib.pyplot as plt

N_SLOTS = 100
N_REQ = 100
DELAY = (0.01, 0.10)
CS_TIME = 0.005
BURST = 1.0
N_RUNS = 10
SERVERS = [2, 4, 8, 16, 25]
BATCH = 5


class Net:
    def __init__(self, rng):
        self.q, self.rng = [], rng
        self.last, self.seq = {}, 0
        self.count = {"req": 0, "rep": 0, "tok": 0, "upd": 0}

    def push(self, t, dst, kind, src=None, data=None):
        self.seq += 1
        heapq.heappush(self.q, (t, self.seq, dst, kind, src, data))

    def send(self, t, src, dst, kind, data):
        at = max(t + self.rng.uniform(*DELAY), self.last.get((src, dst), 0))
        self.last[(src, dst)] = at
        self.count[kind] += 1
        self.push(at, dst, kind, src, data)


class Server:
    def __init__(self, i, n, net, mode, batch, stats):
        self.i, self.n, self.net, self.mode, self.batch, self.st = i, n, net, mode, batch, stats
        self.clock = 0
        self.rn = [0] * n
        self.asked = False
        self.tok = {"ln": [0] * n, "q": [], "taken": set()} if i == 0 else None
        self.taken = set()
        self.wait = []
        self.req = None
        self.got = 0
        self.defer = []
        self.inside = False

    def tick(self, ts=0):
        self.clock = max(self.clock, ts) + 1
        return self.clock

    def others(self):
        return [j for j in range(self.n) if j != self.i]

    def pick(self, t, person, born):
        taken = self.tok["taken"] if self.mode == "sk" else self.taken
        free = [s for s in range(N_SLOTS) if s not in taken]
        if not free:
            self.st["full"] += 1
            return None
        s = free[0]
        taken.add(s)
        self.st["alloc"].append((s, person))
        self.st["lat"].append(t - born)
        return s

    def broadcast_update(self, t, s):
        for j in self.others():
            self.net.send(t, self.i, j, "upd", (self.tick(), s))

    def arrive(self, t, person, born):
        if self.mode == "none":
            s = self.pick(t, person, born)
            if s is not None:
                self.broadcast_update(t, s)
            return
        self.wait.append((person, born))
        if self.mode == "ra":
            if self.req is None:
                self.ask(t)
        else:
            self.want(t)

    def ask(self, t):
        self.req = (self.tick(), self.i)
        self.got = 0
        if self.n == 1:
            self.enter(t)
        for j in self.others():
            self.net.send(t, self.i, j, "req", self.req)

    def want(self, t):
        if self.inside or self.asked or not self.wait:
            return
        if self.tok is not None:
            self.enter(t)
        else:
            self.rn[self.i] += 1
            self.asked = True
            for j in self.others():
                self.net.send(t, self.i, j, "req", (self.i, self.rn[self.i]))

    def on_sk_req(self, t, data):
        j, sn = data
        self.rn[j] = max(self.rn[j], sn)
        if self.tok is not None and not self.inside and self.rn[j] == self.tok["ln"][j] + 1:
            self.send_tok(t, j)

    def send_tok(self, t, j):
        tok, self.tok = self.tok, None
        self.net.send(t, self.i, j, "tok", tok)

    def on_tok(self, t, tok):
        self.tok = tok
        self.asked = False
        self.enter(t)

    def on_req(self, t, src, data):
        if self.mode == "sk":
            return self.on_sk_req(t, data)
        ts, j = data
        self.tick(ts)
        if self.inside or (self.req is not None and self.req < (ts, j)):
            self.defer.append(src)
        else:
            self.net.send(t, self.i, src, "rep", (self.tick(), self.i))

    def on_rep(self, t, data):
        self.tick(data[0])
        self.got += 1
        if self.got == self.n - 1:
            self.enter(t)

    def enter(self, t):
        self.inside = True
        self.st["in_cs"] += 1
        self.st["max_in_cs"] = max(self.st["max_in_cs"], self.st["in_cs"])
        k = min(self.batch, len(self.wait))
        self.net.push(t + CS_TIME * k, self.i, "exit")

    def exit(self, t):
        for _ in range(min(self.batch, len(self.wait))):
            person, born = self.wait.pop(0)
            s = self.pick(t, person, born)
            if s is not None and self.mode == "ra":
                self.broadcast_update(t, s)
        self.inside = False
        self.st["in_cs"] -= 1
        if self.mode == "sk":
            return self.exit_sk(t)
        for j in self.defer:
            self.net.send(t, self.i, j, "rep", (self.tick(), self.i))
        self.defer = []
        self.req = None
        if self.wait:
            self.ask(t)

    def exit_sk(self, t):
        tok = self.tok
        tok["ln"][self.i] = self.rn[self.i]
        for j in self.others():
            if j not in tok["q"] and self.rn[j] == tok["ln"][j] + 1:
                tok["q"].append(j)
        if tok["q"]:
            self.send_tok(t, tok["q"].pop(0))
            self.want(t)
        elif self.wait:
            self.enter(t)

    def on_upd(self, data):
        self.tick(data[0])
        self.taken.add(data[1])


def run(n, mode, seed, batch=1):
    rng = random.Random(seed)
    net = Net(rng)
    st = {"alloc": [], "lat": [], "full": 0, "in_cs": 0, "max_in_cs": 0}
    srv = [Server(i, n, net, mode, batch, st) for i in range(n)]

    for p in range(N_REQ):
        t = rng.uniform(0, BURST)
        net.push(t, rng.randrange(n), "arrive", None, (p, t))

    while net.q:
        t, _, dst, kind, src, data = heapq.heappop(net.q)
        s = srv[dst]
        if kind == "arrive":
            s.arrive(t, *data)
        elif kind == "req":
            s.on_req(t, src, data)
        elif kind == "rep":
            s.on_rep(t, data)
        elif kind == "tok":
            s.on_tok(t, data)
        elif kind == "upd":
            s.on_upd(data)
        elif kind == "exit":
            s.exit(t)

    slots = [a[0] for a in st["alloc"]]
    double = len(slots) - len(set(slots))
    ra = net.count["req"] + net.count["rep"] + net.count["tok"]
    return {
        "double": double,
        "max_in_cs": st["max_in_cs"],
        "msgs": ra / max(1, len(slots)),
        "lat": statistics.mean(st["lat"]) * 1000 if st["lat"] else 0,
    }


def avg(rs, k):
    return statistics.mean(r[k] for r in rs)


MODES = [
    ("none", 1, "No mutex"),
    ("ra", 1, "Ricart-Agrawala"),
    ("sk", 1, "Suzuki-Kasami"),
    ("ra", BATCH, f"R-A batch {BATCH}"),
    ("sk", BATCH, f"S-K batch {BATCH}"),
]


def main():
    print(f"Slots: {N_SLOTS} | Requests: {N_REQ} | Runs per setting: {N_RUNS}\n")
    print(f"{'Servers':>7} | {'Mode':<16} | {'Double-booked':>13} | "
          f"{'Max in CS':>9} | {'Msgs/slot':>9} | {'Avg wait (ms)':>13}")
    print("-" * 82)

    res = {}
    for n in SERVERS:
        for mode, b, name in MODES:
            rs = [run(n, mode, s, b) for s in range(N_RUNS)]
            res[(n, name)] = rs
            print(f"{n:>7} | {name:<16} | {avg(rs, 'double'):>13.1f} | "
                  f"{max(r['max_in_cs'] for r in rs):>9} | {avg(rs, 'msgs'):>9.1f} | "
                  f"{avg(rs, 'lat'):>13.1f}")
        print("-" * 82)

    for n in SERVERS:
        for mode, b, name in MODES[1:]:
            rs = res[(n, name)]
            assert all(r["double"] == 0 for r in rs), name
            assert all(r["max_in_cs"] <= 1 for r in rs), name
    print("[PASS] R-A and S-K: zero double bookings, never more than 1 server in CS")
    print("[INFO] expected msgs/slot, batch 1: R-A 2(n-1), S-K at most n:",
          ", ".join(f"n={n}: {2 * (n - 1)}/{n}" for n in SERVERS))

    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    cols = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e"]
    for (mode, b, name), c in zip(MODES, cols):
        for a, key in zip(ax, ("double", "msgs", "lat")):
            if key == "msgs" and mode == "none":
                continue
            a.plot(SERVERS, [avg(res[(n, name)], key) for n in SERVERS], "o-", color=c, label=name)
    ax[0].set_ylabel("Double-booked slots")
    ax[1].set_ylabel("Messages per slot")
    ax[2].set_ylabel("Average wait (ms)")
    for a in ax:
        a.set_xlabel("Number of servers")
        a.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
