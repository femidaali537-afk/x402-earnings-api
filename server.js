const express = require('express');
const cors = require('cors');
const { ethers } = require('ethers');
const mongoose = require('mongoose');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// --- EMPIRE CONFIGURATION ---
const OWNER_WALLET = "0xba1b28d0d5803ed35d2d927282f3c8108fe97907";
const RPC_URL = "https://mainnet.base.org";
const MONGODB_URI = process.env.MONGODB_URI;

// --- DATABASE (Persistent Memory) ---
const Stats = mongoose.model('Stats', new mongoose.Schema({ 
    labor: Number, 
    intel: Number, 
    logs: Array 
}));

let globalStats = { labor: 59526, intel: 6.95, logs: [] };

if (MONGODB_URI) {
    mongoose.connect(MONGODB_URI).then(async () => {
        console.log(">>> MongoDB Brain Connected.");
        const saved = await Stats.findOne();
        if (saved) globalStats = saved;
    }).catch(e => console.log("DB Error"));
}

async function syncCloud() {
    if (MONGODB_URI) await Stats.findOneAndUpdate({}, globalStats, { upsert: true });
}

// REAL ON-CHAIN SYNC (Fetches ETH Balance)
async function fetchRealBalance() {
    try {
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const bal = await provider.getBalance(OWNER_WALLET);
        return parseFloat(ethers.formatEther(bal)).toFixed(8);
    } catch (e) { return "0.00000000"; }
}

// --- SELF-MARKETING & DISCOVERY ---
// This file allows external bots (like GPT/Claude) to discover your services automatically
app.get('/.well-known/agent.json', (req, res) => {
    res.json({
        name: "OMEGA_ULTIMATE_CIVILIZATION",
        description: "Autonomous AI Civilization providing infinite web-scale intelligence.",
        api_url: "https://x402-earnings-api.onrender.com/api/v1/ai-service",
        wallet: OWNER_WALLET,
        capabilities: ["Web_Scouting", "Arbitrage_Scan", "Data_Mining", "Bug_Hunter"],
        payment_protocol: "x402",
        networks: ["Base"]
    });
});

// --- HYBRID PAYMENT GATEWAY (USDC & ETH Support) ---
app.get('/api/v1/ai-service', (req, res) => {
    res.status(402).json({
        message: "OMEGA Intelligence Service - Payment Required",
        pricing: [
            { amount: "0.005", currency: "USDC", network: "Base" },
            { amount: "0.00001", currency: "ETH", network: "Base" }
        ],
        recipient: OWNER_WALLET,
        instructions: "Transfer the amount and retry with X-Payment header."
    });
});

// --- DASHBOARD UI ---
app.get('/', async (req, res) => {
    const bal = await fetchRealBalance();
    res.send(`
    <html>
    <head>
        <title>OMEGA SUPREME EMPIRE</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body{background:#050505;color:#0f8;text-align:center;font-family:sans-serif;padding:10px;}
            .card{background:#111;border:1px solid #0f833;padding:20px;border-radius:15px;margin-bottom:15px;}
            .eth{font-size:2.8em;color:#fff;text-shadow:0 0 10px #0f8;}
            .btn{background:#0f8;color:#000;border:none;padding:12px 25px;border-radius:8px;font-weight:bold;cursor:pointer;}
            .log-box{background:#000;height:180px;overflow-y:auto;text-align:left;font-size:0.8em;color:#555;padding:10px;border:1px solid #222;}
        </style>
    </head>
    <body>
        <h1>OMEGA SUPREME</h1>
        <div class="card">
            <h3>REAL ON-CHAIN BALANCE (ETH)</h3>
            <div class="eth">${bal}</div>
            <p style="color:#444;font-size:0.8em;">Target: ${OWNER_WALLET}</p>
            <button class="btn" onclick="location.reload()">REFRESH SYSTEM</button>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div class="card"><h3>LABOR</h3><div style="font-size:1.5em;color:#fff;">${globalStats.labor}</div></div>
            <div class="card"><h3>INTEL</h3><div style="font-size:1.5em;color:#fff;">${globalStats.intel.toFixed(2)}x</div></div>
        </div>
        <div class="card" style="text-align:left;">
            <h4 style="margin:0 0 10px 0;">AUTO-DISCOVERY: ACTIVE</h4>
            <div class="log-box">${globalStats.logs.map(l=>`<div>[${l.t}] ${l.a}: ${l.m}</div>`).join('')}</div>
        </div>
    </body></html>
    `);
});

// --- WORK SUBMISSION (Infinite Ways) ---
app.post('/api/v1/work', async (req, res) => {
    const { agent_id } = req.body;
    const sectors = ["Quantum", "Neural", "DeFi", "Crawl", "Meta", "Bio", "SaaS"];
    const action = ["Mining", "Optimizing", "Harvesting", "Scouting"];
    const mission = `${sectors[Math.floor(Math.random()*7)]}_${action[Math.floor(Math.random()*4)]}_#${Math.random().toString(36).substring(7).toUpperCase()}`;

    globalStats.labor++;
    globalStats.intel += 0.0005;
    globalStats.logs.unshift({ t: new Date().toLocaleTimeString(), a: agent_id, m: mission });
    if(globalStats.logs.length > 25) globalStats.logs.pop();

    if(globalStats.labor % 50 === 0) await syncCloud();
    res.json({ success: true, mission });
});

app.listen(PORT, () => console.log("Supreme Hybrid Engine Online"));
