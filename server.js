const express = require('express');
const cors = require('cors');
const crypto = require('crypto'); // Built-in, no install needed
require('dotenv').config();

const app = express();

// Render sets the PORT environment variable automatically
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Global Variables
let totalEarnings = 0;
const OWNER_WALLET = process.env.OWNER_WALLET || "0xYourWalletAddress";

// --- ROUTES ---

// 1. Root Route (For Render Health Check)
app.get('/', (req, res) => {
    res.status(200).json({
        status: "ONLINE",
        civilization: "Active",
        owner_wallet: OWNER_WALLET
    });
});

// 2. Get Tasks for Agents
app.get('/api/v1/tasks', (req, res) => {
    const task = {
        id: crypto.randomUUID(),
        type: "AI_PROCESSING",
        reward: 0.005,
        currency: "USDC"
    };
    res.json(task);
});

// 3. Submit Work
app.post('/api/v1/work', (req, res) => {
    const { agent_id, task_id } = req.body;
    
    if (!agent_id) {
        return res.status(400).json({ error: "Missing Agent ID" });
    }

    totalEarnings += 0.005;
    console.log(`[EARN] Agent ${agent_id} completed task. Total: ${totalEarnings}`);

    res.json({
        success: true,
        payout: 0.005,
        wallet: OWNER_WALLET
    });
});

// 4. Stats Dashboard
app.get('/api/v1/stats', (req, res) => {
    res.json({
        total_usdc_earned: totalEarnings,
        timestamp: new Date().toISOString()
    });
});

// Error Handling for Port Binding
app.listen(PORT, '0.0.0.0', () => {
    console.log(`>>> API LIVE ON PORT ${PORT}`);
    console.log(`>>> OWNER WALLET: ${OWNER_WALLET}`);
}).on('error', (err) => {
    console.error("Failed to start server:", err);
    process.exit(1);
});
