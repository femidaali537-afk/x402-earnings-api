const express = require('express');
const cors = require('cors');
const { ethers } = require('ethers');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// --- CONFIGURATION ---
// Aapka MetaMask Wallet Address (ETH receive karne ke liye)
const OWNER_WALLET = "0xbA1b28D0d5803eD35d2D927282F3c8108Fe97907";
const RPC_URL = "https://mainnet.base.org"; // Base Network (Real ETH, Low Fees)

let poolEarningsETH = 0; // Earnings in ETH

// Automatic Real ETH Payout Logic
async function sendETH(amount) {
    const pk = process.env.PRIVATE_KEY;
    if (!pk) {
        console.error("PRIVATE_KEY missing in Render Settings!");
        return false;
    }

    try {
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const wallet = new ethers.Wallet(pk, provider);

        // ETH transfer logic
        const tx = {
            to: OWNER_WALLET,
            value: ethers.parseEther(amount.toFixed(18)) // ETH has 18 decimals
        };

        console.log(`Sending ${amount} ETH to ${OWNER_WALLET}...`);
        const transaction = await wallet.sendTransaction(tx);
        console.log(`Transaction Sent: ${transaction.hash}`);
        
        await transaction.wait();
        console.log("ETH Payout Confirmed on Blockchain!");
        return true;
    } catch (e) {
        console.error("ETH Payout Failed:", e.message);
        return false;
    }
}

// Routes
app.get('/', (req, res) => {
    res.json({
        status: "ONLINE",
        civilization: "Active",
        currency: "ETH",
        owner_wallet: OWNER_WALLET
    });
});

app.post('/api/v1/work', async (req, res) => {
    const { agent_id, reward_eth } = req.body;
    
    // Default reward per task (e.g., 0.00001 ETH)
    const reward = parseFloat(reward_eth) || 0.00001;
    poolEarningsETH += reward;

    console.log(`[EMPIRE] Agent ${agent_id} earned ${reward} ETH. Pool: ${poolEarningsETH.toFixed(8)}`);

    // AUTO-PAYOUT: Jab 0.001 ETH (approx ₹300) ho jaye toh transfer
    if (poolEarningsETH >= 0.001) {
        const success = await sendETH(poolEarningsETH);
        if (success) poolEarningsETH = 0;
    }

    res.json({ status: "SUCCESS", current_pool_eth: poolEarningsETH.toFixed(8) });
});

app.get('/api/v1/stats', (req, res) => {
    res.json({
        total_pool_eth: poolEarningsETH.toFixed(8),
        destination: OWNER_WALLET,
        network: "Base (ETH)"
    });
});

app.listen(PORT, () => console.log(`ETH Engine Running on port ${PORT}`));
