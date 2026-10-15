# FairBooking

VRF-fair allocation + cross-server mutual exclusion for oversubscribed public resource booking
(vaccine slots, exam seats, vouchers).

Author: Bhavesh Agarwal (AE23B005), IIT Madras
Course: Blockchain Technology and Ledger Technologies

## Files

- `fcfs_baseline.py`: naive first-come-first-served booking with a bot simulator.
- `vrf.py`: Verifiable Random Function (RSA-FDH-VRF, RFC 9381) with 5 self-tests.
- `kyc.py`: mock Aadhaar e-KYC oracle (one identity = one key) with 4 self-tests.
- `lottery.py`: full single-server round (KYC registration, deposit, VRF ranking, allocation) compared with FCFS.
- `FairBooking.sol`: `Escrow` (verification, deposits, registration, closing, refund/forfeit) and `Ledger` (on-chain slot allocation in rank order).

## How to run

```
pip install -r requirements.txt
python fcfs_baseline.py
python vrf.py
python kyc.py
python lottery.py
```

`FairBooking.sol` is compiled and deployed with Remix (remix.ethereum.org).

## Progress

- [x] Naive FCFS baseline + bot simulator
- [x] VRF implementation and tests
- [x] Mock e-KYC oracle
- [x] Single-server VRF lottery vs FCFS
- [x] Escrow and Ledger contracts
- [ ] Multi-server allocation with Lamport clocks + Ricart-Agrawala mutual exclusion
- [ ] Full evaluation
