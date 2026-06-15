/**
 * AI Trading Empire — CRASH-PROOF Server
 * Won't crash even if MongoDB is unreachable.
 */
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const axios = require('axios');
const rateLimit = require('express-rate-limit');
const pino = require('pino');
const axiosRetry = require('axios-retry');
const cron = require('node-cron');
const { MongoClient } = require('mongodb');

// ====================================================================
// CONFIG
// ====================================================================
const CONFIG = {
  PORT: parseInt(process.env.PORT || '3000'),
  NODE_ENV: process.env.NODE_ENV || 'production',
  PYTHON_API_URL: process.env.PYTHON_API_URL || 'http://localhost:8000',
  MONGODB_URI: process.env.MONGODB_URI || '',
  MONGODB_DB_NAME: process.env.MONGODB_DB_NAME || 'ai_trading_empire',
  MONGODB_MAX_SIZE_MB: parseInt(process.env.MONGODB_MAX_SIZE_MB || '480'),
  TELEGRAM_BOT_TOKEN: process.env.TELEGRAM_BOT_TOKEN || '',
  TELEGRAM_CHAT_ID: process.env.TELEGRAM_CHAT_ID || '',
  START_TIME: Date.now(),
};

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: process.env.NODE_ENV === 'production' ? undefined : {
    target: 'pino-pretty',
    options: { colorize: true, translateTime: 'HH:MM:ss' }
  }
});

// ====================================================================
// MONGO MANAGER — CRASH-PROOF
// ====================================================================
class MongoManager {
  constructor() {
    this.client = null;
    this.db = null;
    this.connected = false;
  }

  async connect() {
    if (!CONFIG.MONGODB_URI) {
      logger.warn('⚠️ MONGODB_URI not set - running in NO-DB mode');
      return false;
    }

    try {
      logger.info('🍃 Connecting to MongoDB...');
      this.client = new MongoClient(CONFIG.MONGODB_URI, {
        serverSelectionTimeoutMS: 5000,
        retryWrites: true,
      });
      
      await this.client.connect();
      this.db = this.client.db(CONFIG.MONGODB_DB_NAME);
      this.connected = true;
      logger.info(`✓ MongoDB connected: ${CONFIG.MONGODB_DB_NAME}`);
      return true;
    } catch (err) {
      logger.warn(`⚠️ MongoDB connection failed (continuing without it): ${err.message}`);
      this.connected = false;
      return false;
    }
  }

  async close() {
    if (this.client) {
      try {
        await this.client.close();
      } catch (e) {}
    }
  }

  getStatus() {
    return {
      connected: this.connected,
      configured: !!CONFIG.MONGODB_URI,
    };
  }
}

// ====================================================================
// APP
// ====================================================================
const app = express();
const mongo = new MongoManager();

app.use(helmet());
app.use(cors({ origin: '*' }));
app.use(compression());
app.use(express.json({ limit: '10mb' }));

const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api/', limiter);

// ====================================================================
// HEALTH (always returns 200)
// ====================================================================
app.get('/health', async (req, res) => {
  const uptime = Math.floor((Date.now() - CONFIG.START_TIME) / 1000);
  res.status(200).json({
    status: 'healthy',
    uptime_seconds: uptime,
    uptime_human: formatUptime(uptime),
    timestamp: new Date().toISOString(),
    services: {
      node_server: 'healthy',
      mongodb: mongo.getStatus(),
    },
    version: '1.0.0',
  });
});

app.get('/healthz', (req, res) => res.status(200).send('OK'));
app.get('/ready', (req, res) => res.status(200).json({ ready: true }));

// ====================================================================
// ROOT INFO
// ====================================================================
app.get('/', (req, res) => {
  res.json({
    name: 'AI Trading Empire Server',
    version: '1.0.0',
    uptime: formatUptime(Math.floor((Date.now() - CONFIG.START_TIME) / 1000)),
    mongo: mongo.getStatus(),
    endpoints: {
      health: '/health',
      mongo_status: '/mongo/status',
    },
  });
});

// ====================================================================
// MONGO STATUS (always works)
// ====================================================================
app.get('/mongo/status', (req, res) => {
  res.json(mongo.getStatus());
});

// ====================================================================
// API PROXY (to Python)
// ====================================================================
app.use('/api/empire', async (req, res) => {
  try {
    const response = await axios({
      method: req.method,
      url: `${CONFIG.PYTHON_API_URL}${req.path}`,
      data: req.body,
      params: req.query,
      timeout: 5000,
      validateStatus: () => true,
    });
    res.status(response.status).json(response.data);
  } catch (err) {
    res.status(503).json({ error: 'Backend unavailable', message: err.message });
  }
});

// ====================================================================
// HELPERS
// ====================================================================
function formatUptime(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${days}d ${hours}h ${mins}m`;
}

// ====================================================================
// ERROR HANDLER
// ====================================================================
app.use((err, req, res, next) => {
  logger.error({ err: err.message }, 'Error');
  res.status(500).json({ error: 'Internal error' });
});

// ====================================================================
// START SERVER — CRASH-PROOF
// ====================================================================
async function start() {
  // Try to connect to MongoDB, but DON'T CRASH if fails
  await mongo.connect();
  
  // ALWAYS start the HTTP server, even if MongoDB failed
  const server = app.listen(CONFIG.PORT, '0.0.0.0', () => {
    logger.info(`🚀 Server running on port ${CONFIG.PORT}`);
    logger.info(`📡 Backend: ${CONFIG.PYTHON_API_URL}`);
    logger.info(`🍃 MongoDB: ${mongo.connected ? 'connected' : 'NOT connected (running in no-db mode)'}`);
    logger.info(`🛡️ Health: http://localhost:${CONFIG.PORT}/health`);
  });

  // Graceful shutdown
  const shutdown = async (signal) => {
    logger.info(`${signal} received, shutting down...`);
    server.close();
    await mongo.close();
    process.exit(0);
  };
  
  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));
}

start().catch(err => {
  logger.error(`Failed to start: ${err.message}`);
  process.exit(1);
});
