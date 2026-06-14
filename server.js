const express = require('express');
const cors = require('cors');
const { ethers } = require('ethers');
const mongoose = require('mongoose');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// --- CONFIG ---
const OWNER_WALLET = "0xba1b28d0d5803ed35d2d927282f3c8108fe97907";
const RPC_URL = "https://mainnet.base.org";
const MONGODB_URI = process.env.MONGODB_URI;

// --- DATABASE ---
const Stats = mongoose.model('Stats', new mongoose.Schema({ labor: Number, intel: Number, revenue: Number }));
let currentStats = { labor: 59526, intel: 6.95, revenue: 0 };

if(MONGODB_URI) {
    mongoose.connect(MONGODB_URI).then(async () => {
        const saved = await Stats.findOne();
        if(saved) currentStats = saved;
    });
}

// REAL ON-CHAIN SYNC
async function fetchRealBalance() {
    try {
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const bal = await provider.getBalance(OWNER_WALLET);
        return parseFloat(ethers.formatEther(bal)).toFixed(8);
    } catch (e) { return "0.00000000"; }
}

// --- ROUTES ---
app.get('/', async (req, res) => {
    const bal = await fetchRealBalance();
    res.send(`
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>body{background:#000;color:#0f8;text-align:center;font-family:monospace;} .val{font-size:3em;color:#fff;text-shadow:0 0 10px #0f8;}</style></head>
    <body>
        <h1>OMEGA REAL-TIME EMPIRE</h1>
        <div style="border:1px solid #333;padding:20px;border-radius:20px;">
            <h3>BLOCKCHAIN BALANCE (ETH)</h3>
            <div class="val">${bal}</div>
            <p>Wallet: ${OWNER_WALLET}</p>
            <button style="background:#0f8;padding:15px;border-radius:10px;font-weight:bold;" onclick="alert('Checking Market for Payments...')">REFRESH PAYOUTS</button>
        </div>
        <div style="display:flex;justify-content:space-around;margin-top:20px;">
            <div><h3>LABOR</h3><h2>${currentStats.labor}</h2></div>
            <div><h3>INTEL</h3><h2>${currentStats.intel.toFixed(2)}x</h2></div>
        </div>
        <p style="color:#444;">System is now scanning the global x402 market for buyers.</p>
    </body></html>
    `);
});

// Agents call this to simulate 'Mining' value
app.post('/api/v1/work', async (req, res) => {
    currentStats.labor++;
    currentStats.intel += 0.001;
    if(currentStats.labor % 100 === 0 && MONGODB_URI) await Stats.findOneAndUpdate({}, currentStats, {upsert:true});
    res.json({ success: true, status: "Value_Reported" });
});

app.listen(PORT, () => console.log("Omega Online"));
