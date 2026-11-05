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
- `mutex.py`: multi-server simulation with Lamport clocks, Ricart-Agrawala and Suzuki-Kasami mutual exclusion, optional batching, up to 25 servers.
- `noshow.py`: effect of the deposit size on the no-show rate.
- `chain.py`: Python script that deploys `Escrow` and `Ledger`, runs a full round on-chain and tests cheating attempts.
- `contracts.json`: ABI and bytecode of the two contracts (compiled with solc 0.8.26, EVM shanghai).

## How to run

```
pip install -r requirements.txt
python fcfs_baseline.py
python vrf.py
python kyc.py
python lottery.py
python mutex.py
python noshow.py
python chain.py --local
```

`chain.py --local` runs on an in-memory test chain (needs the extra package `eth-tester[py-evm]`, which requires a C compiler on Windows). To run on the Ethereum Sepolia testnet:

```
export RPC_URL=https://ethereum-sepolia-rpc.publicnode.com
export PRIVATE_KEY=<private key of a test-only wallet funded with Sepolia ETH>
python chain.py | tee chain_log.txt
```

On Windows PowerShell, use `$env:RPC_URL="..."` and `$env:PRIVATE_KEY="..."` instead of `export`.

`FairBooking.sol` can also be compiled and deployed by hand with Remix (remix.ethereum.org).

## Progress

- [x] Naive FCFS baseline + bot simulator
- [x] VRF implementation and tests
- [x] Mock e-KYC oracle
- [x] Single-server VRF lottery vs FCFS
- [x] Escrow and Ledger contracts
- [x] Multi-server allocation with Lamport clocks + Ricart-Agrawala mutual exclusion
- [x] Batching and Suzuki-Kasami comparison, scaling to 25 servers
- [x] Deposit size vs no-show evaluation
- [x] Python script that writes a full round to the contracts
- [ ] Run on the Sepolia testnet
- [x] Final report
