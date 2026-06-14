const express = require('express');
const cors = require('cors');
const { ethers } = require('ethers');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// --- EMPIRE CONFIG ---
const OWNER_WALLET = "0xba1b28d0d5803ed35d2d927282f3c8108fe97907";
const RPC_URL = "https://mainnet.base.org";
const PAYOUT_THRESHOLD = 0.001; 

// STATE - Initialization with safe numbers
let poolWealthETH = 0.00000000;
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
        return true;
    } catch (e) {
        console.error("Payout Error:", e.message);
        return false;
    }
}

// --- DASHBOARD UI ---
const html = `
<!DOCTYPE html>
<html>
<head>
    <title>AI OMEGA EMPIRE</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #08080a; color: #00ff88; font-family: sans-serif; text-align: center; padding: 20px; margin: 0; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; max-width: 1200px; margin: auto; }
        .card { background: #111116; border: 1px solid #00ff8833; padding: 20px; border-radius: 12px; }
        .val { font-size: 1.8em; font-weight: bold; color: #fff; margin: 5px 0; }
        .log-box { background: #000; height: 200px; overflow-y: auto; text-align: left; padding: 10px; font-family: monospace; font-size: 0.8em; color: #00ff88; border-radius: 8px; border: 1px solid #333; }
        .bar { background: #222; height: 6px; border-radius: 3px; margin: 5px 0; overflow: hidden; }
        .fill { background: #00ff88; height: 100%; transition: 0.5s; }
        h1 { font-size: 2em; letter-spacing: 5px; color: #fff; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>OMEGA CIVILIZATION</h1>
    <div class="grid">
        <div class="card">
            <h3 style="margin:0; font-size:0.9em;">TREASURY (ETH)</h3>
            <div class="val" id="eth">0.00000000</div>
            <p style="font-size:0.7em; color:#555;">Target: ${OWNER_WALLET}</p>
        </div>
        <div class="card">
            <h3 style="margin:0; font-size:0.9em;">ACTIVE AGENTS</h3>
            <div class="val" id="agents">0</div>
            <p style="font-size:0.7em; color:#555;">Self-Improving Units 24/7</p>
        </div>
    </div>
    <br>
    <div class="grid">
        <div class="card">
            <h3 style="margin:0; font-size:0.9em; margin-bottom:10px;">CIVILIZATION INTELLIGENCE</h3>
            <div id="intel"></div>
        </div>
        <div class="card">
            <h3 style="margin:0; font-size:0.9em; margin-bottom:10px;">LIVE OPERATION LOGS</h3>
            <div class="log-box" id="logs"></div>
        </div>
    </div>

    <script>
        async function update() {
            try {
                const res = await fetch('/api/v1/stats');
                const data = await res.json();
                
                // Safety check for NaN
                const ethVal = parseFloat(data.pool);
                document.getElementById('eth').innerText = isNaN(ethVal) ? "0.00000000" : ethVal.toFixed(8);
                document.getElementById('agents').innerText = data.agents || 0;
                
                let intelHtml = '';
                for(let key in data.intel) {
                    let pct = Math.min(100, data.intel[key] * 1).toFixed(1);
                    intelHtml += \`<div style="text-align:left; font-size:0.8em; color:#aaa;">\${key}: \${pct}%</div><div class="bar"><div class="fill" style="width:\${pct}%"></div></div>\`;
                }
                document.getElementById('intel').innerHTML = intelHtml;
                document.getElementById('logs').innerHTML = data.logs.map(l => \`<div>[\${l.t}] \${l.a}: +\${l.r} ETH</div>\`).join('');
            } catch(e) { console.log("Update error", e); }
        }
        setInterval(update, 2000);
        update();
    </script>
</body>
</html>
`;

app.get('/', (req, res) => res.send(html));

app.post('/api/v1/work', async (req, res) => {
    try {
        const { agent_id, way, reward } = req.body;
        const r = parseFloat(reward) || 0;
        
        if (!isNaN(r)) {
            poolWealthETH += r;
        }
        
        // Update Intel
        if(way && intelligence[way]) {
            intelligence[way] += 0.01;
            if(intelligence[way] > 100) intelligence[way] = 100;
        }
        
        // Logging
        logs.unshift({ t: new Date().toLocaleTimeString(), a: agent_id, w: way, r: r.toFixed(8) });
        if(logs.length > 30) logs.pop();
        
        // Agent Count
        const idParts = agent_id.split('-');
        const idNum = parseInt(idParts[idParts.length - 1]);
        if(!isNaN(idNum) && idNum > agentCount) agentCount = idNum;

        // Auto Payout
        if (poolWealthETH >= PAYOUT_THRESHOLD) {
            const success = await sendPayout(poolWealthETH);
            if (success) poolWealthETH = 0;
        }

        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.get('/api/v1/stats', (req, res) => {
    res.json({
        pool: isNaN(poolWealthETH) ? "0.00000000" : poolWealthETH.toFixed(8),
        agents: agentCount,
        intel: intelligence,
        logs: logs
    });
});

app.listen(PORT, () => console.log('Omega Server LIVE'));
