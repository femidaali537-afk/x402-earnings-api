const express = require('express');
const cors = require('cors');
const { ethers } = require('ethers');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// --- EMPIRE CONFIG ---
const OWNER_WALLET = "0xbA1b28D0d5803eD35D2D927282F3c8108Fe97907";
const RPC_URL = "https://mainnet.base.org";
const PAYOUT_THRESHOLD = 0.001; // ETH (approx $3-4)

// STATE
let poolWealthETH = 0;
let agentCount = 0;
let logs = [];
let intelligence = {
    "Web_Scouting": 1.0,
    "Arbitrage": 1.0,
    "Data_Mining": 1.0,
    "Social_Intelligence": 1.0
};

// Automatic Payout Logic
async function sendPayout(amount) {
    const pk = process.env.PRIVATE_KEY;
    if (!pk) return console.log("PRIVATE_KEY not set!");
    try {
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const wallet = new ethers.Wallet(pk, provider);
        const tx = { to: OWNER_WALLET, value: ethers.parseEther(amount.toFixed(18)) };
        const res = await wallet.sendTransaction(tx);
        await res.wait();
        console.log(`[PAYOUT SUCCESS] Hash: ${res.hash}`);
        return true;
    } catch (e) {
        console.error("Payout Error:", e.message);
        return false;
    }
}

// --- VISUAL DASHBOARD ---
const html = `
<!DOCTYPE html>
<html>
<head>
    <title>AI OMEGA EMPIRE</title>
    <style>
        body { background: #08080a; color: #00ff88; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; padding: 30px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; max-width: 1200px; margin: auto; }
        .card { background: #111116; border: 1px solid #00ff8844; padding: 25px; border-radius: 15px; box-shadow: 0 0 20px #00ff8811; }
        .val { font-size: 2.2em; font-weight: bold; color: #fff; margin: 10px 0; }
        .log-box { background: #000; height: 250px; overflow-y: auto; text-align: left; padding: 15px; font-family: monospace; font-size: 0.85em; color: #888; border-radius: 10px; border: 1px solid #333; }
        .bar { background: #222; height: 8px; border-radius: 4px; margin: 8px 0; overflow: hidden; }
        .fill { background: linear-gradient(90deg, #00ff88, #0088ff); height: 100%; transition: 0.5s; }
        h1 { font-size: 3em; letter-spacing: 10px; margin-bottom: 40px; color: #fff; text-shadow: 0 0 10px #00ff88; }
    </style>
</head>
<body>
    <h1>OMEGA CIVILIZATION</h1>
    <div class="grid">
        <div class="card">
            <h3>TREASURY (ETH)</h3>
            <div class="val" id="eth">0.00000000</div>
            <p>Target: ${OWNER_WALLET.slice(0,10)}...</p>
        </div>
        <div class="card">
            <h3>ACTIVE AGENTS</h3>
            <div class="val" id="agents">0</div>
            <p>Self-Improving Units 24/7</p>
        </div>
        <div class="card">
            <h3>NETWORK</h3>
            <div class="val" style="font-size: 1.5em; color: #0088ff;">BASE MAINNET</div>
            <p>Status: Synchronized</p>
        </div>
    </div>
    <br>
    <div class="grid">
        <div class="card">
            <h3>CIVILIZATION INTELLIGENCE</h3>
            <div id="intel"></div>
        </div>
        <div class="card">
            <h3>LIVE OPERATION LOGS</h3>
            <div class="log-box" id="logs"></div>
        </div>
    </div>

    <script>
        async function update() {
            try {
                const res = await fetch('/api/v1/stats');
                const data = await res.json();
                document.getElementById('eth').innerText = data.pool;
                document.getElementById('agents').innerText = data.agents;
                
                let intelHtml = '';
                for(let key in data.intel) {
                    let pct = Math.min(100, data.intel[key] * 10).toFixed(1);
                    intelHtml += \`<div style="text-align:left; font-size:0.9em;">\${key}: \${pct}%</div><div class="bar"><div class="fill" style="width:\${pct}%"></div></div>\`;
                }
                document.getElementById('intel').innerHTML = intelHtml;
                document.getElementById('logs').innerHTML = data.logs.map(l => \`<div>[\${l.t}] \${l.a} -> \${l.w} (+\${l.r} ETH)</div>\`).join('');
            } catch(e) {}
        }
        setInterval(update, 2000);
        update();
    </script>
</body>
</html>
`;

app.get('/', (req, res) => res.send(html));

app.post('/api/v1/work', async (req, res) => {
    const { agent_id, way, reward } = req.body;
    const r = parseFloat(reward);
    poolWealthETH += r;
    
    // Auto-Learning
    if(intelligence[way]) intelligence[way] += 0.001;
    
    // Logging
    logs.unshift({ t: new Date().toLocaleTimeString(), a: agent_id, w: way, r: r.toFixed(8) });
    if(logs.length > 50) logs.pop();
    
    // Population Tracking
    const idNum = parseInt(agent_id.split('-').pop());
    if(idNum > agentCount) agentCount = idNum;

    // AUTO-PAYOUT
    if (poolWealthETH >= PAYOUT_THRESHOLD) {
        const success = await sendPayout(poolWealthETH);
        if (success) poolWealthETH = 0;
    }

    res.json({ success: true });
});

app.get('/api/v1/stats', (req, res) => {
    res.json({
        pool: poolWealthETH.toFixed(8),
        agents: agentCount,
        intel: intelligence,
        logs: logs
    });
});

app.listen(PORT, () => console.log('Omega Server LIVE'));