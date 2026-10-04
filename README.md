# FairBooking

VRF-fair allocation + cross-server mutual exclusion for oversubscribed public resource booking
(vaccine slots, exam seats, vouchers).

Author: Bhavesh Agarwal (AE23B005), IIT Madras
Course: Blockchain Technology and Ledger Technologies

## Files

- `fcfs_baseline.py`: naive first-come-first-served booking with a bot simulator.
  Result: bots are 10% of applicants but win 100% of slots.
- `vrf.py`: Verifiable Random Function (RSA-FDH-VRF, RFC 9381) with 5 self-tests.

## How to run

```
pip install -r requirements.txt
python fcfs_baseline.py
python vrf.py
```

## Progress

- [x] Naive FCFS baseline + bot simulator
- [x] VRF implementation and tests
- [ ] Solidity escrow and allocation ledger contracts (Sepolia testnet)
- [ ] Mock e-KYC oracle
- [ ] Multi-server allocation with Lamport clocks + Ricart-Agrawala mutual exclusion
- [ ] Full evaluation
