const express = require('express');
const cors = require('cors');
const { ethers } = require('ethers');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// --- REAL WALLET CONFIG ---
const OWNER_WALLET = "0xba1b28d0d5803ed35d2d927282f3c8108fe97907";
const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"; // Real USDC on Base
const RPC_URL = "https://mainnet.base.org";

let poolEarnings = 0;

// REAL TRANSACTION LOGIC
async function sendUSDC(amount) {
    const pk = process.env.PRIVATE_KEY;
    if (!pk) return console.error("FATAL: Private Key missing in Environment Variables");

    try {
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const wallet = new ethers.Wallet(pk, provider);
        const usdc = new ethers.Contract(USDC_BASE, [
            "function transfer(address to, uint256 amount) public returns (bool)",
            "function balanceOf(address account) public view returns (uint256)"
        ], wallet);

        // Final check before sending
        const balance = await usdc.balanceOf(wallet.address);
        const amountToPay = ethers.parseUnits(amount.toFixed(6), 6);

        if (balance < amountToPay) {
            console.log("Error: Server wallet has insufficient real USDC balance.");
            return false;
        }

        console.log(`Sending real payout: ${amount} USDC to ${OWNER_WALLET}...`);
        const tx = await usdc.transfer(OWNER_WALLET, amountToPay);
        await tx.wait();
        console.log(`[REAL PAYOUT SUCCESS] Hash: ${tx.hash}`);
        return true;
    } catch (e) {
        console.error("Blockchain Error:", e.message);
        return false;
    }
}

// Routes for Agents
app.post('/api/v1/work', async (req, res) => {
    const { agent_id, reward } = req.body;
    const realReward = parseFloat(reward) || 0.01;
    poolEarnings += realReward;

    console.log(`[REAL-TIME] Agent ${agent_id} secured ${realReward} USDC. Total Pool: ${poolEarnings}`);

    // AUTO-WITHDRAW: When pool hits $1.00, it sends automatically
    if (poolEarnings >= 1.0) {
        const success = await sendUSDC(poolEarnings);
        if (success) poolEarnings = 0;
    }

    res.json({ status: "RECORDED", pool: poolEarnings });
});

app.get('/api/v1/stats', (req, res) => {
    res.json({
        total_real_pool: poolEarnings,
        payout_destination: OWNER_WALLET,
        network: "Base Mainnet"
    });
});

app.listen(PORT, () => console.log(`OMEGA ENGINE: REAL-VALUE MODE ACTIVE`));
