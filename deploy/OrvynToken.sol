// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract OrvynToken is ERC20 {
    address public owner;
    uint256 public rate = 7000; // 1 ORV = 7000 Euros (or equivalent in ETH)
    uint256 public referralRewardPercent = 2; // 2% reward for referrals

    mapping(address => address) public referrals; // stores referrer for each user

    event TokensPurchased(address indexed buyer, uint256 amount);
    event ReferralReward(address indexed referrer, address indexed referee, uint256 reward);

    constructor(uint256 initialSupply) ERC20("Orvyn", "ORV") {
        _mint(msg.sender, initialSupply);
        owner = msg.sender;
    }

    function buyTokens(address referrer) public payable {
        require(msg.value > 0, "Send ETH to buy ORV");
        uint256 ethToEuro = 3549; // Adjust this to the current ETH to Euro conversion rate
        uint256 tokenAmount = (msg.value * ethToEuro) / rate;
        require(balanceOf(owner) >= tokenAmount, "Not enough tokens available");

        // Transfer tokens to buyer
        _transfer(owner, msg.sender, tokenAmount);
        emit TokensPurchased(msg.sender, tokenAmount);

        // Register referrer if not already set
        if (referrals[msg.sender] == address(0) && referrer != address(0) && referrer != msg.sender) {
            referrals[msg.sender] = referrer;
        }

        // Reward referrer if set
        if (referrals[msg.sender] != address(0)) {
            address ref = referrals[msg.sender];
            uint256 reward = (tokenAmount * referralRewardPercent) / 100;
            _transfer(owner, ref, reward);
            emit ReferralReward(ref, msg.sender, reward);
        }
    }

    function transfer(address recipient, uint256 amount) public override returns (bool) {
        address sender = _msgSender();
        _transfer(sender, recipient, amount);

        // Reward referrer if set
        if (referrals[sender] != address(0)) {
            address ref = referrals[sender];
            uint256 reward = (amount * referralRewardPercent) / 100;
            _transfer(sender, ref, reward);
            emit ReferralReward(ref, sender, reward);
        }

        return true;
    }

    function withdraw() public {
        require(msg.sender == owner, "Only the owner can withdraw");
        payable(owner).transfer(address(this).balance);
    }
}
