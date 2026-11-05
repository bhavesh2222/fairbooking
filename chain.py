import json
import os
import random
import sys

from eth_account import Account
from web3 import Web3

import vrf
from kyc import KYC, make_aadhaar, id_hash

N_APP = 4
N_SLOTS = 2
BITS = 1024
DEPOSIT = 10**15
GAS_FUND = 8 * 10**14
ORACLE_FUND = 2 * 10**15
MIN_BAL = 2 * 10**16
LOCAL = False
NONCE = {}
EXPLORER = {11155111: "https://sepolia.etherscan.io/tx/"}


def connect(local):
    if local:
        from web3 import EthereumTesterProvider
        return Web3(EthereumTesterProvider())
    url = os.environ.get("RPC_URL")
    if not url:
        sys.exit("Set RPC_URL to a Sepolia endpoint, or run: python chain.py --local")
    return Web3(Web3.HTTPProvider(url))


def fees(w3):
    base = w3.eth.get_block("latest")["baseFeePerGas"]
    try:
        tip = w3.eth.max_priority_fee
    except Exception:
        tip = w3.to_wei(1, "gwei")
    tip = min(max(tip, w3.to_wei(0.2, "gwei")), w3.to_wei(1.5, "gwei"))
    return {"maxFeePerGas": 2 * base + tip, "maxPriorityFeePerGas": tip}


def next_nonce(w3, a):
    n = max(NONCE.get(a, 0), w3.eth.get_transaction_count(a, "pending"))
    NONCE[a] = n + 1
    return n


def send(w3, acct, fn=None, to=None, value=0, gas=300000):
    tx = {"from": acct.address, "nonce": next_nonce(w3, acct.address),
          "value": value, "chainId": w3.eth.chain_id}
    tx.update(fees(w3))
    if fn is None:
        tx["to"] = to
    if LOCAL:
        tx["gas"] = gas if fn is not None else 21000
    else:
        base = {"from": acct.address, "value": value}
        est = w3.eth.estimate_gas({**base, "to": to}) if fn is None else fn.estimate_gas(base)
        tx["gas"] = int(est * 1.3)
    if fn is not None:
        tx = fn.build_transaction(tx)
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    rc = w3.eth.wait_for_transaction_receipt(h, timeout=300)
    link = EXPLORER.get(w3.eth.chain_id, "tx ")
    print(f"    {link}0x{h.hex().removeprefix('0x')} gas used {rc['gasUsed']}")
    assert rc["status"] == 1, "transaction failed"
    return rc


def blocked(fn, who, value=0):
    try:
        arg = {"from": who, "value": value}
        if LOCAL:
            arg["gas"] = 300000
        fn.call(arg)
    except Exception as e:
        msg = str(e).split("execution reverted:")[-1].split("', '")[0].strip().strip("'\"")
        return msg
    return None


def check(label, msg, want):
    assert msg is not None and want in msg, f"{label}: expected '{want}', got {msg}"
    print(f"  [PASS] {label} -> {msg}")


def main():
    global LOCAL
    local = LOCAL = "--local" in sys.argv
    w3 = connect(local)
    with open("contracts.json") as f:
        art = json.load(f)
    rng = random.Random(11)

    if local:
        op = Account.create()
        w3.eth.send_transaction({"from": w3.eth.accounts[0], "to": op.address, "value": w3.to_wei(5, "ether")})
    else:
        op = Account.from_key(os.environ["PRIVATE_KEY"])
    print(f"Chain id {w3.eth.chain_id} | operator {op.address}")
    print(f"Operator balance: {w3.from_wei(w3.eth.get_balance(op.address), 'ether')} ETH\n")

    if not local and w3.eth.get_balance(op.address) < MIN_BAL:
        sys.exit(f"Need at least {w3.from_wei(MIN_BAL, 'ether')} Sepolia ETH in the operator wallet to run.")

    oracle = Account.create()
    apps = [Account.create() for _ in range(N_APP)]
    with open("testkeys.json", "w") as f:
        json.dump({"oracle": oracle.key.hex(), "applicants": [a.key.hex() for a in apps]}, f)
    print("Funding the oracle and applicants (throwaway keys saved in testkeys.json)")
    for a in [oracle] + apps:
        send(w3, op, to=a.address, value=ORACLE_FUND if a is oracle else GAS_FUND + DEPOSIT)

    print("\nDeploying Escrow and Ledger")
    E = w3.eth.contract(abi=art["Escrow"]["abi"], bytecode=art["Escrow"]["bytecode"])
    rc = send(w3, op, E.constructor(oracle.address, DEPOSIT), gas=3000000)
    esc = w3.eth.contract(address=rc["contractAddress"], abi=art["Escrow"]["abi"])
    L = w3.eth.contract(abi=art["Ledger"]["abi"], bytecode=art["Ledger"]["bytecode"])
    rc = send(w3, op, L.constructor(esc.address, N_SLOTS), gas=3000000)
    led = w3.eth.contract(address=rc["contractAddress"], abi=art["Ledger"]["abi"])
    print(f"  Escrow {esc.address}\n  Ledger {led.address}")

    ids = [make_aadhaar(rng) for _ in apps]
    kyc = KYC(ids)
    keys = [vrf.keygen(BITS) for _ in apps]

    print("\nVerification by the KYC oracle")
    for a, aid in zip(apps, ids):
        h, msg = kyc.check(aid)
        assert msg == "ok"
        send(w3, oracle, esc.functions.verify(a.address, h))
    check("same identity on a second account",
          blocked(esc.functions.verify(oracle.address, id_hash(ids[0])), oracle.address), "identity already used")
    check("verify called by a non-oracle",
          blocked(esc.functions.verify(oracle.address, b"\x01" * 32), apps[0].address), "only oracle")

    print("\nRegistration with deposit")
    kh = [vrf.pk_fingerprint(pk) for sk, pk in keys]
    check("register without the deposit", blocked(esc.functions.register(kh[0]), apps[0].address), "wrong deposit")
    for a, k in zip(apps, kh):
        send(w3, a, esc.functions.register(k), value=DEPOSIT)
    check("register twice", blocked(esc.functions.register(kh[0]), apps[0].address), "already registered")
    print(f"  Escrow holds {w3.from_wei(w3.eth.get_balance(esc.address), 'ether')} ETH")

    print("\nClosing registration")
    send(w3, op, esc.functions.close())
    rid = esc.functions.roundId().call().hex()
    print(f"  Round ID {rid}")
    check("register after closing", blocked(esc.functions.register(kh[0]), apps[0].address), "registration closed")

    print("\nRanking")
    rows = []
    for a, (sk, pk) in zip(apps, keys):
        al = vrf.make_alpha(rid, pk)
        beta = vrf.verify(pk, al, vrf.prove(sk, al))
        assert beta is not None
        rows.append((int.from_bytes(beta, "big"), a, beta))
    rows.sort(key=lambda r: r[0])
    for i, (v, a, b) in enumerate(rows):
        print(f"  rank {i + 1}: {a.address[:10]}...  r = {v / 2**256:.4f}")

    print("\nAllocating the lowest ranks")
    for v, a, b in rows[:N_SLOTS - 1]:
        send(w3, op, led.functions.allocate(a.address, b))
    check("a slot for the same person again",
          blocked(led.functions.allocate(rows[0][1].address, rows[0][2]), op.address), "already has a slot")
    low = (rows[N_SLOTS - 2][0] - 1).to_bytes(32, "big")
    check("a worse rank placed ahead of a better one",
          blocked(led.functions.allocate(rows[N_SLOTS][1].address, low), op.address), "out of rank order")
    v, a, b = rows[N_SLOTS - 1]
    send(w3, op, led.functions.allocate(a.address, b))
    check("a slot beyond the limit",
          blocked(led.functions.allocate(rows[N_SLOTS][1].address, rows[N_SLOTS][2]), op.address), "all slots filled")
    for i, (v, a, b) in enumerate(rows[:N_SLOTS]):
        assert led.functions.slotOwner(i + 1).call() == a.address
    print(f"  Ledger holds {led.functions.filled().call()} slots in rank order")

    print("\nSettlement (last winner does not show up)")
    for i, (v, a, b) in enumerate(rows):
        noshow = i == N_SLOTS - 1
        send(w3, op, esc.functions.settle(a.address, not noshow))
        print(f"    {a.address[:10]}... {'forfeited' if noshow else 'refunded'}")
    assert w3.eth.get_balance(esc.address) == 0
    print("  [PASS] Escrow is empty, the no-show deposit went to the operator")
    print("\nAll on-chain checks passed.")


if __name__ == "__main__":
    main()
