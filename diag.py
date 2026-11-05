import os
from eth_account import Account
from web3 import Web3

w3 = Web3(Web3.HTTPProvider(os.environ["RPC_URL"]))
op = Account.from_key(os.environ["PRIVATE_KEY"])
new = Account.create()
print("chain", w3.eth.chain_id)
print("operator", op.address)
print("operator code:", w3.eth.get_code(op.address).hex() or "none")
print("balance", w3.from_wei(w3.eth.get_balance(op.address), "ether"))
print("nonce", w3.eth.get_transaction_count(op.address))
tx = {"from": op.address, "to": new.address, "value": 10**15}
try:
    print("estimate gas:", w3.eth.estimate_gas(tx))
except Exception as e:
    print("estimate error:", e)
try:
    w3.eth.call(tx)
    print("call: ok")
except Exception as e:
    print("call error:", e)
