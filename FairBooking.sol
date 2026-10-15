// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Escrow {
    address public operator;
    address public oracle;
    uint256 public deposit;
    bool public open = true;
    bytes32 public roundId;

    mapping(bytes32 => bool) public idUsed;
    mapping(address => bool) public verified;
    mapping(address => bytes32) public keyOf;
    mapping(address => uint256) public locked;
    address[] public applicants;

    event Verified(address who);
    event Registered(address who, bytes32 keyHash);
    event Closed(bytes32 roundId);
    event Settled(address who, bool refunded);

    constructor(address _oracle, uint256 _deposit) {
        operator = msg.sender;
        oracle = _oracle;
        deposit = _deposit;
    }

    function verify(address who, bytes32 idHash) external {
        require(msg.sender == oracle, "only oracle");
        require(!idUsed[idHash], "identity already used");
        require(!verified[who], "address already verified");
        idUsed[idHash] = true;
        verified[who] = true;
        emit Verified(who);
    }

    function register(bytes32 keyHash) external payable {
        require(open, "registration closed");
        require(verified[msg.sender], "not verified");
        require(keyOf[msg.sender] == bytes32(0), "already registered");
        require(keyHash != bytes32(0), "empty key");
        require(msg.value == deposit, "wrong deposit");
        keyOf[msg.sender] = keyHash;
        locked[msg.sender] = msg.value;
        applicants.push(msg.sender);
        emit Registered(msg.sender, keyHash);
    }

    function close() external {
        require(msg.sender == operator, "only operator");
        require(open, "already closed");
        open = false;
        roundId = keccak256(abi.encodePacked(blockhash(block.number - 1), address(this)));
        emit Closed(roundId);
    }

    function settle(address who, bool refund) external {
        require(msg.sender == operator, "only operator");
        require(!open, "registration still open");
        uint256 amt = locked[who];
        require(amt > 0, "nothing locked");
        locked[who] = 0;
        address to = refund ? who : operator;
        (bool ok, ) = payable(to).call{value: amt}("");
        require(ok, "transfer failed");
        emit Settled(who, refund);
    }

    function isRegistered(address who) external view returns (bool) {
        return keyOf[who] != bytes32(0);
    }

    function count() external view returns (uint256) {
        return applicants.length;
    }
}

contract Ledger {
    Escrow public escrow;
    address public operator;
    uint256 public slots;
    uint256 public filled;
    bytes32 public lastBeta;

    mapping(uint256 => address) public slotOwner;
    mapping(address => uint256) public slotOf;
    mapping(address => bytes32) public betaOf;

    event Allocated(uint256 slot, address who, bytes32 beta);

    constructor(address _escrow, uint256 _slots) {
        escrow = Escrow(_escrow);
        operator = msg.sender;
        slots = _slots;
    }

    function allocate(address who, bytes32 beta) external {
        require(msg.sender == operator, "only operator");
        require(!escrow.open(), "registration still open");
        require(escrow.isRegistered(who), "not registered");
        require(filled < slots, "all slots filled");
        require(slotOf[who] == 0, "already has a slot");
        require(uint256(beta) >= uint256(lastBeta), "out of rank order");
        filled += 1;
        slotOwner[filled] = who;
        slotOf[who] = filled;
        betaOf[who] = beta;
        lastBeta = beta;
        emit Allocated(filled, who, beta);
    }
}
