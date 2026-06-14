const express = require('express');
const cors = require('cors');
const { ethers } = require('ethers');
const mongoose = require('mongoose');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// --- EMPIRE CONFIG ---
const OWNER_WALLET = "0xbA1b28D0d5803eD35d2D927282F3c8108Fe97907";
const RPC_URL = "https://mainnet.base.org";
const MONGODB_URI = process.env.MONGODB_URI;

// --- STATE (Memory Resilience) ---
let empireStats = { labor: 182478, intel: 19.25 };
let isDBConnected = false;

// Cloud Schema
const statsSchema = new mongoose.Schema({ id: String, labor: Number, intel: Number });
const StatsModel = mongoose.model('Stats', statsSchema);

// --- SAFE CLOUD CONNECTION ---
if (MONGODB_URI) {
    mongoose.connect(MONGODB_URI, { serverSelectionTimeoutMS: 5000 })
        .then(async () => {
            console.log(">>> MongoDB Brain Connected.");
            isDBConnected = true;
            const saved = await StatsModel.findOne({ id: "OMEGA_CORE" });
            if (saved) empireStats = { labor: saved.labor, intel: saved.intel };
        })
        .catch(err => console.log(">>> Running in Local Memory Mode."));
}

async function syncToCloud() {
    if (isDBConnected) {
        try {
            await StatsModel.findOneAndUpdate({ id: "OMEGA_CORE" }, empireStats, { upsert: true });
        } catch (e) {}
    }
}

// REAL ON-CHAIN SYNC
async function fetchBal() {
    try {
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const b = await provider.getBalance(OWNER_WALLET);
        return parseFloat(ethers.formatEther(b)).toFixed(8);
    } catch(e) { return "0.00000000"; }
}

// --- DASHBOARD UI ---
app.get('/', async (req, res) => {
    const bal = await fetchBal();
    res.send(`
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>body{background:#050505;color:#0f8;text-align:center;font-family:sans-serif;padding:15px;} .card{background:#111;padding:20px;border-radius:15px;border:1px solid #0f833;margin-bottom:15px;} .val{font-size:2.5em;color:#fff;text-shadow:0 0 10px #0f8;} .btn{background:#0f8;color:#000;border:none;padding:15px 30px;border-radius:10px;font-weight:bold;cursor:pointer;width:100%;}</style></head>
    <body>
        <h1>OMEGA SUPREME</h1>
        <div class="card">
            <h3>REAL ON-CHAIN BALANCE (ETH)</h3>
            <div class="val">${bal}</div>
            <p style="color:#555;">Target: ${OWNER_WALLET}</p>
            <button class="btn" onclick="location.reload()">REFRESH SYSTEM</button>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;">
            <div class="card"><h3>LABOR</h3><h2>${empireStats.labor}</h2></div>
            <div class="card"><h3>INTEL</h3><h2>${empireStats.intel.toFixed(2)}x</h2></div>
        </div>
        <p style="color:#333;font-size:0.7em;">Market Discovery Active | DB: ${isDBConnected ? "Connected" : "Offline"}</p>
    </body></html>
    `);
});

// --- WORK SUBMISSION (Infinite Ways) ---
app.post('/api/v1/work', async (req, res) => {
    empireStats.labor++;
    empireStats.intel += 0.0001;
    if (empireStats.labor % 50 === 0) syncToCloud();
    res.json({ success: true });
});

app.get('/api/v1/stats', (req, res) => {
    res.json({ labor: empireStats.labor, intel: empireStats.intel });
});

app.listen(PORT, () => console.log("Final Stable Engine Online"));
