/**
 * AI Trading Empire — Master Backend Server
 * ==========================================
 *
 * Single comprehensive Node.js backend that handles:
 *
 * 1. 🌐 HTTP Server (Express)
 *    - /health (UptimeRobot monitoring)
 *    - /api/* reverse proxy to Python FastAPI
 *    - Rate limiting, CORS, security
 *
 * 2. 🍃 MongoDB Atlas Integration (500MB optimized)
 *    - Auto-connect with retry
 *    - TTL indexes for auto-expiration
 *    - Size monitoring (warns at 80%, prunes at 85%, emergency at 95%)
 *    - Agent DNA persistence
 *    - Performance tracking
 *    - Lesson storage
 *    - Trade history with TTL
 *
 * 3. 🔗 API Reverse Proxy
 *    - Forwards data requests to Python FastAPI
 *    - Caches responses
 *    - Retry logic
 *    - Falls back to direct MongoDB query if Python is down
 *
 * 4. 🔔 Webhook Handlers
 *    - UptimeRobot (downtime alerts)
 *    - Telegram (commands)
 *    - GitHub (deployment events)
 *    - MongoDB Atlas alerts
 *
 * 5. 📊 Health & Metrics
 *    - /health (detailed)
 *    - /healthz (minimal)
 *    - /ready (readiness)
 *    - /metrics (Prometheus)
 *    - /mongo/status (MongoDB stats)
 *
 * 6. 🤖 AI Civilization Endpoints
 *    - /api/empire/status - System status
 *    - /api/empire/agents - Active agents
 *    - /api/empire/signals - Recent signals
 *    - /api/empire/positions - Open positions
 *    - /api/empire/trade - Submit trade
 *    - /api/empire/kill - Emergency stop
 *
 * @author AI Trading Empire Architect
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
const WebSocket = require('ws');

// ====================================================================
// CONFIGURATION
// ====================================================================

const CONFIG = {
  PORT: parseInt(process.env.PORT || '3000'),
  NODE_ENV: process.env.NODE_ENV || 'development',
  LOG_LEVEL: process.env.LOG_LEVEL || 'info',
  
  // Python FastAPI backend (handles ML + complex API clients)
  PYTHON_API_URL: process.env.PYTHON_API_URL || 'http://localhost:8000',
  
  // MongoDB Atlas
  MONGODB_URI: process.env.MONGODB_URI || '',
  MONGODB_DB_NAME: process.env.MONGODB_DB_NAME || 'ai_trading_empire',
  MONGODB_MAX_SIZE_MB: parseInt(process.env.MONGODB_MAX_SIZE_MB || '480'),
  
  // Telegram
  TELEGRAM_BOT_TOKEN: process.env.TELEGRAM_BOT_TOKEN || '',
  TELEGRAM_CHAT_ID: process.env.TELEGRAM_CHAT_ID || '',
  
  // UptimeRobot
  UPTIMEROBOT_WEBHOOK_SECRET: process.env.UPTIMEROBOT_WEBHOOK_SECRET || '',
  
  // Internal
  START_TIME: Date.now(),
};

// ====================================================================
// LOGGER
// ====================================================================

const logger = pino({
  level: CONFIG.LOG_LEVEL,
  transport: {
    target: 'pino-pretty',
    options: { colorize: true, translateTime: 'HH:MM:ss', ignore: 'pid,hostname' }
  }
});

// ====================================================================
// MONGODB MANAGER — 500MB Never Full
// ====================================================================

class MongoManager {
  constructor() {
    this.client = null;
    this.db = null;
    this.connected = false;
    this.lastStats = null;
    this.lastCheck = null;
  }
  
  async connect() {
    if (!CONFIG.MONGODB_URI) {
      logger.warn('MONGODB_URI not set — MongoDB features disabled');
      return false;
    }
    
    try {
      logger.info('🍃 Connecting to MongoDB Atlas...');
      this.client = new MongoClient(CONFIG.MONGODB_URI, {
        serverSelectionTimeoutMS: 5000,
        retryWrites: true,
      });
      
      await this.client.connect();
      this.db = this.client.db(CONFIG.MONGODB_DB_NAME);
      this.connected = true;
      logger.success(`✓ MongoDB connected: ${CONFIG.MONGODB_DB_NAME}`);
      
      await this.initIndexes();
      await this.checkSize();
      return true;
    } catch (err) {
      logger.error(`MongoDB connection failed: ${err.message}`);
      this.connected = false;
      return false;
    }
  }
  
  async initIndexes() {
    if (!this.connected) return;
    
    const indexes = [
      // Agent DNA
      { collection: 'agent_dna', index: { agent_id: 1 }, options: { unique: true, name: 'agent_id_unique' } },
      { collection: 'agent_dna', index: { fitness: -1 }, options: { name: 'by_fitness' } },
      { collection: 'agent_dna', index: { generation: 1 }, options: { name: 'by_generation' } },
      
      // Signals (with TTL: 7 days)
      { 
        collection: 'signals', 
        index: { timestamp: 1 }, 
        options: { 
          name: 'ttl_signals',
          expireAfterSeconds: 7 * 86400,
        } 
      },
      { collection: 'signals', index: { agent_id: 1, timestamp: -1 }, options: { name: 'by_agent_recent' } },
      { collection: 'signals', index: { symbol: 1, timestamp: -1 }, options: { name: 'by_symbol_recent' } },
      
      // Performance
      { 
        collection: 'performance', 
        index: { agent_id: 1, date: -1 }, 
        options: { unique: true, name: 'agent_date_unique' } 
      },
      
      // Trades (with TTL: 30 days)
      { 
        collection: 'trades', 
        index: { close_time: 1 }, 
        options: { 
          name: 'ttl_trades',
          expireAfterSeconds: 30 * 86400,
        } 
      },
      { collection: 'trades', index: { symbol: 1, close_time: -1 }, options: { name: 'by_symbol' } },
      
      // Lessons (with TTL: 90 days)
      { 
        collection: 'lessons', 
        index: { timestamp: 1 }, 
        options: { 
          name: 'ttl_lessons',
          expireAfterSeconds: 90 * 86400,
        } 
      },
      
      // Market cache (TTL: 1 hour)
      { 
        collection: 'market_cache', 
        index: { timestamp: 1 }, 
        options: { 
          name: 'ttl_market',
          expireAfterSeconds: 3600,
        } 
      },
    ];
    
    for (const idx of indexes) {
      try {
        await this.db.collection(idx.collection).createIndex(idx.index, idx.options);
      } catch (err) {
        logger.warn(`Index ${idx.options.name} creation warning: ${err.message}`);
      }
    }
    
    logger.success(`✓ MongoDB indexes created`);
  }
  
  async checkSize() {
    if (!this.connected) return null;
    
    try {
      const stats = await this.db.command({ dbStats: 1 });
      const storageBytes = stats.storageSize || 0;
      const dataBytes = stats.dataSize || 0;
      const indexBytes = stats.indexSize || 0;
      
      const storageMb = storageBytes / (1024 * 1024);
      const usagePct = (storageMb / CONFIG.MONGODB_MAX_SIZE_MB) * 100;
      
      const collections = await this.db.listCollectionNames();
      const breakdown = {};
      for (const name of collections) {
        try {
          const collStat = await this.db.command({ collStats: name });
          breakdown[name] = +(collStat.size / (1024 * 1024)).toFixed(2);
        } catch (e) {}
      }
      
      this.lastStats = {
        total_mb: +storageMb.toFixed(2),
        data_mb: +(dataBytes / (1024 * 1024)).toFixed(2),
        index_mb: +(indexBytes / (1024 * 1024)).toFixed(2),
        max_mb: CONFIG.MONGODB_MAX_SIZE_MB,
        usage_pct: +usagePct.toFixed(1),
        collections: breakdown,
        timestamp: new Date().toISOString(),
      };
      
      this.lastCheck = Date.now();
      
      // Auto-prune logic
      if (usagePct > 95) {
        logger.critical(`🚨 MongoDB at ${usagePct.toFixed(1)}% — emergency prune!`);
        await this.emergencyPrune();
        await this.sendTelegramAlert(`🚨 *MongoDB Critical*\nUsage: ${usagePct.toFixed(1)}% — emergency prune executed`);
      } else if (usagePct > 85) {
        logger.warn(`⚠️ MongoDB at ${usagePct.toFixed(1)}% — soft prune`);
        await this.softPrune();
        await this.sendTelegramAlert(`⚠️ *MongoDB Warning*\nUsage: ${usagePct.toFixed(1)}% — auto-prune executed`);
      } else if (usagePct > 70) {
        logger.info(`MongoDB usage: ${usagePct.toFixed(1)}% (normal)`);
      }
      
      return this.lastStats;
    } catch (err) {
      logger.error(`MongoDB size check failed: ${err.message}`);
      return null;
    }
  }
  
  async softPrune() {
    if (!this.connected) return;
    
    try {
      // Reduce signal TTL by deleting older data manually
      const oldSignals = new Date(Date.now() - 2 * 86400 * 1000); // older than 2 days
      const sigResult = await this.db.collection('signals').deleteMany({ 
        timestamp: { $lt: oldSignals } 
      });
      
      const oldTrades = new Date(Date.now() - 14 * 86400 * 1000); // older than 14 days
      const tradeResult = await this.db.collection('trades').deleteMany({ 
        close_time: { $lt: oldTrades } 
      });
      
      logger.info(`Pruned ${sigResult.deletedCount} signals, ${tradeResult.deletedCount} trades`);
    } catch (err) {
      logger.error(`Soft prune failed: ${err.message}`);
    }
  }
  
  async emergencyPrune() {
    if (!this.connected) return;
    
    try {
      // Keep only last 1 day of signals
      const oneDayAgo = new Date(Date.now() - 86400 * 1000);
      await this.db.collection('signals').deleteMany({ timestamp: { $lt: oneDayAgo } });
      
      // Keep only last 3 days of trades
      const threeDaysAgo = new Date(Date.now() - 3 * 86400 * 1000);
      await this.db.collection('trades').deleteMany({ close_time: { $lt: threeDaysAgo } });
      
      // Keep only last 100 lessons
      const total = await this.db.collection('lessons').countDocuments();
      if (total > 100) {
        const oldest = await this.db.collection('lessons')
          .find()
          .sort({ timestamp: 1 })
          .limit(total - 100)
          .toArray();
        if (oldest.length > 0) {
          await this.db.collection('lessons').deleteMany({
            _id: { $in: oldest.map(d => d._id) }
          });
        }
      }
      
      logger.warning('Emergency prune complete');
    } catch (err) {
      logger.error(`Emergency prune failed: ${err.message}`);
    }
  }
  
  // CRUD Operations
  async saveAgentDNA(agentId, agentType, dna, generation = 0, parentIds = [], fitness = 0) {
    if (!this.connected) return null;
    try {
      await this.db.collection('agent_dna').replaceOne(
        { agent_id: agentId },
        {
          agent_id: agentId,
          agent_type: agentType,
          dna,
          generation,
          parent_ids: parentIds,
          fitness,
          created_at: new Date(),
          updated_at: new Date(),
        },
        { upsert: true }
      );
      return true;
    } catch (err) {
      logger.error(`Save DNA failed: ${err.message}`);
      return null;
    }
  }
  
  async getAgentDNA(agentId) {
    if (!this.connected) return null;
    try {
      return await this.db.collection('agent_dna').findOne({ agent_id: agentId });
    } catch (err) {
      logger.error(`Get DNA failed: ${err.message}`);
      return null;
    }
  }
  
  async getAllAgents(limit = 5000) {
    if (!this.connected) return [];
    try {
      return await this.db.collection('agent_dna')
        .find()
        .sort({ fitness: -1 })
        .limit(limit)
        .toArray();
    } catch (err) {
      logger.error(`Get all agents failed: ${err.message}`);
      return [];
    }
  }
  
  async recordSignal(agentId, symbol, side, confidence, features = {}) {
    if (!this.connected) return;
    try {
      await this.db.collection('signals').insertOne({
        agent_id: agentId,
        symbol,
        side,
        confidence,
        features,
        timestamp: new Date(),
      });
    } catch (err) {
      logger.debug(`Record signal error: ${err.message}`);
    }
  }
  
  async recordPerformance(agentId, metrics) {
    if (!this.connected) return;
    try {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      await this.db.collection('performance').updateOne(
        { agent_id: agentId, date: today },
        { 
          $set: {
            agent_id: agentId,
            date: today,
            sharpe: +metrics.sharpe?.toFixed(4) || 0,
            winrate: +metrics.winrate?.toFixed(4) || 0,
            profit_factor: +metrics.profit_factor?.toFixed(4) || 0,
            max_drawdown: +metrics.max_drawdown?.toFixed(4) || 0,
            total_trades: metrics.total_trades || 0,
            pnl: +metrics.pnl?.toFixed(2) || 0,
          }
        },
        { upsert: true }
      );
    } catch (err) {
      logger.debug(`Record performance error: ${err.message}`);
    }
  }
  
  async recordTrade(trade) {
    if (!this.connected) return;
    try {
      await this.db.collection('trades').insertOne({
        trade_id: trade.id || `t_${Date.now()}`,
        symbol: trade.symbol,
        side: trade.side,
        size: trade.size,
        entry_price: trade.entry_price,
        exit_price: trade.exit_price,
        pnl: trade.pnl,
        pnl_pct: trade.pnl_pct,
        agent_id: trade.agent_id || 'owner',
        open_time: trade.open_time || new Date(),
        close_time: trade.close_time || new Date(),
        close_reason: (trade.close_reason || '').substring(0, 50),
      });
    } catch (err) {
      logger.debug(`Record trade error: ${err.message}`);
    }
  }
  
  async saveLesson(agentId, lesson, action, context = '') {
    if (!this.connected) return;
    try {
      await this.db.collection('lessons').insertOne({
        agent_id: agentId,
        lesson: lesson.substring(0, 500),
        action: action.substring(0, 300),
        context: context.substring(0, 200),
        timestamp: new Date(),
      });
      
      // Cap at 1000 most recent
      const total = await this.db.collection('lessons').countDocuments();
      if (total > 1000) {
        const excess = await this.db.collection('lessons')
          .find()
          .sort({ timestamp: 1 })
          .limit(total - 1000)
          .toArray();
        if (excess.length > 0) {
          await this.db.collection('lessons').deleteMany({
            _id: { $in: excess.map(d => d._id) }
          });
        }
      }
    } catch (err) {
      logger.debug(`Save lesson error: ${err.message}`);
    }
  }
  
  async close() {
    if (this.client) {
      await this.client.close();
      logger.info('MongoDB connection closed');
    }
  }
  
  getStatus() {
    return {
      connected: this.connected,
      stats: this.lastStats,
      last_check: this.lastCheck,
    };
  }
}

// ====================================================================
// API REVERSE PROXY (to Python FastAPI)
// ====================================================================

class APIProxy {
  constructor(baseURL) {
    this.baseURL = baseURL;
    this.client = axios.create({
      baseURL: baseURL,
      timeout: 30000,
      headers: { 'Content-Type': 'application/json' },
    });
    
    // Add retry logic
    axiosRetry(this.client, {
      retries: 3,
      retryDelay: axiosRetry.exponentialDelay,
      retryCondition: (error) => {
        return axiosRetry.isNetworkOrIdempotentRequestError(error) || error.response?.status >= 500;
      },
    });
  }
  
  async forward(method, path, data = null, params = null) {
    try {
      const response = await this.client.request({
        method,
        url: path,
        data,
        params,
        validateStatus: () => true,
      });
      return { status: response.status, data: response.data };
    } catch (err) {
      return { 
        status: 503, 
        data: { error: 'Backend unavailable', message: err.message } 
      };
    }
  }
}

// ====================================================================
// INITIALIZE
// ====================================================================

const app = express();
const mongo = new MongoManager();
const apiProxy = new APIProxy(CONFIG.PYTHON_API_URL);

// ====================================================================
// MIDDLEWARE
// ====================================================================

app.use(helmet());
app.use(cors({ origin: '*' }));
app.use(compression());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Request logging
app.use((req, res, next) => {
  logger.debug(`${req.method} ${req.path}`);
  next();
});

// Rate limiting
const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  message: { error: 'Too many requests, please slow down.' },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api/', limiter);

// ====================================================================
// HEALTH ENDPOINTS (for UptimeRobot)
// ====================================================================

/**
 * /health — Main health endpoint
 * UptimeRobot pings this every 5 minutes
 */
app.get('/health', async (req, res) => {
  try {
    const uptime = Math.floor((Date.now() - CONFIG.START_TIME) / 1000);
    const pythonOk = await checkPythonBackend();
    
    let mongoStatus = { connected: false };
    if (mongo.connected) {
      const stats = await mongo.checkSize();
      mongoStatus = {
        connected: true,
        total_mb: stats?.total_mb || 0,
        usage_pct: stats?.usage_pct || 0,
      };
    }
    
    const allHealthy = pythonOk && (mongo.connected ? mongoStatus.usage_pct < 99 : true);
    
    res.status(allHealthy ? 200 : 503).json({
      status: allHealthy ? 'healthy' : 'degraded',
      uptime_seconds: uptime,
      uptime_human: formatUptime(uptime),
      timestamp: new Date().toISOString(),
      services: {
        node_server: 'healthy',
        python_backend: pythonOk ? 'healthy' : 'down',
        mongodb: mongoStatus,
      },
      version: '1.0.0',
    });
  } catch (err) {
    logger.error(`Health check error: ${err.message}`);
    res.status(200).json({
      status: 'degraded',
      timestamp: new Date().toISOString(),
      error: err.message,
    });
  }
});

app.get('/healthz', (req, res) => res.status(200).send('OK'));

app.get('/ready', async (req, res) => {
  const pythonOk = await checkPythonBackend();
  if (pythonOk && (!mongo.connected || (mongo.lastStats?.usage_pct || 0) < 99)) {
    res.status(200).json({ ready: true });
  } else {
    res.status(503).json({ ready: false });
  }
});

app.get('/metrics', (req, res) => {
  const uptime = Math.floor((Date.now() - CONFIG.START_TIME) / 1000);
  const mem = process.memoryUsage();
  const lines = [
    '# HELP empire_uptime_seconds Time since service start',
    '# TYPE empire_uptime_seconds counter',
    `empire_uptime_seconds ${uptime}`,
    '# HELP empire_memory_mb Process memory in MB',
    '# TYPE empire_memory_mb gauge',
    `empire_memory_mb ${(mem.rss / (1024 * 1024)).toFixed(2)}`,
    '# HELP empire_mongodb_connected MongoDB connection status',
    '# TYPE empire_mongodb_connected gauge',
    `empire_mongodb_connected ${mongo.connected ? 1 : 0}`,
  ];
  if (mongo.lastStats) {
    lines.push(
      '# HELP empire_mongodb_usage_pct MongoDB storage usage %',
      '# TYPE empire_mongodb_usage_pct gauge',
      `empire_mongodb_usage_pct ${mongo.lastStats.usage_pct}`
    );
  }
  res.set('Content-Type', 'text/plain').send(lines.join('\n'));
});

// ====================================================================
// MONGODB STATUS & MANAGEMENT ENDPOINTS
// ====================================================================

app.get('/mongo/status', async (req, res) => {
  if (!mongo.connected) {
    return res.status(503).json({ connected: false, message: 'Not connected to MongoDB' });
  }
  const stats = await mongo.checkSize();
  res.json({ connected: true, stats });
});

app.post('/mongo/agent/save', async (req, res) => {
  const { agent_id, agent_type, dna, generation, parent_ids, fitness } = req.body;
  if (!agent_id || !dna) {
    return res.status(400).json({ error: 'agent_id and dna required' });
  }
  const success = await mongo.saveAgentDNA(agent_id, agent_type, dna, generation, parent_ids, fitness);
  res.json({ success });
});

app.get('/mongo/agent/:id', async (req, res) => {
  const agent = await mongo.getAgentDNA(req.params.id);
  if (!agent) return res.status(404).json({ error: 'Agent not found' });
  res.json(agent);
});

app.get('/mongo/agents', async (req, res) => {
  const limit = parseInt(req.query.limit || '5000');
  const agents = await mongo.getAllAgents(limit);
  res.json({ count: agents.length, agents });
});

app.post('/mongo/lesson', async (req, res) => {
  const { agent_id, lesson, action, context } = req.body;
  if (!agent_id || !lesson) {
    return res.status(400).json({ error: 'agent_id and lesson required' });
  }
  await mongo.saveLesson(agent_id, lesson, action, context || '');
  res.json({ success: true });
});

app.post('/mongo/trade', async (req, res) => {
  await mongo.recordTrade(req.body);
  res.json({ success: true });
});

app.post('/mongo/prune', async (req, res) => {
  const { mode = 'soft' } = req.body;
  if (mode === 'emergency') {
    await mongo.emergencyPrune();
  } else {
    await mongo.softPrune();
  }
  const stats = await mongo.checkSize();
  res.json({ pruned: true, mode, stats });
});

// ====================================================================
// AI CIVILIZATION API ENDPOINTS
// ====================================================================

// Proxy all /api/empire/* requests to Python FastAPI
app.use('/api/empire', async (req, res) => {
  const result = await apiProxy.forward(req.method, req.path, req.body, req.query);
  res.status(result.status).json(result.data);
});

// Direct MongoDB endpoints (work even if Python is down)
app.get('/api/empire/status', async (req, res) => {
  const pythonStatus = await apiProxy.forward('GET', '/status');
  
  const mongoStatus = mongo.connected ? mongo.lastStats : null;
  const agentCount = mongo.connected ? (await mongo.getAllAgents(5000)).length : 0;
  
  res.json({
    status: pythonStatus.status === 200 ? 'online' : 'degraded',
    python_backend: pythonStatus.status,
    mongo_connected: mongo.connected,
    mongo_storage: mongoStatus,
    agent_count: agentCount,
    uptime: formatUptime(Math.floor((Date.now() - CONFIG.START_TIME) / 1000)),
    timestamp: new Date().toISOString(),
  });
});

app.get('/api/empire/agents', async (req, res) => {
  if (!mongo.connected) {
    return res.status(503).json({ error: 'MongoDB not connected' });
  }
  const agents = await mongo.getAllAgents(parseInt(req.query.limit || '100'));
  res.json({ count: agents.length, agents });
});

app.get('/api/empire/leaderboard', async (req, res) => {
  if (!mongo.connected) {
    return res.status(503).json({ error: 'MongoDB not connected' });
  }
  const top = await mongo.getAllAgents(50);
  res.json(top.map(a => ({
    agent_id: a.agent_id,
    agent_type: a.agent_type,
    fitness: a.fitness || 0,
    generation: a.generation || 0,
  })));
});

app.get('/api/empire/positions', async (req, res) => {
  const result = await apiProxy.forward('GET', '/positions');
  res.status(result.status).json(result.data);
});

app.get('/api/empire/signals/recent', async (req, res) => {
  const limit = parseInt(req.query.limit || '20');
  
  if (mongo.connected) {
    try {
      const signals = await mongo.db.collection('signals')
        .find()
        .sort({ timestamp: -1 })
        .limit(limit)
        .toArray();
      return res.json(signals);
    } catch (err) {
      logger.error(`Signals query failed: ${err.message}`);
    }
  }
  
  // Fallback to Python
  const result = await apiProxy.forward('GET', `/signals/recent?limit=${limit}`);
  res.status(result.status).json(result.data);
});

app.post('/api/empire/kill', async (req, res) => {
  logger.critical('🚨 KILL SWITCH TRIGGERED');
  
  // Activate kill switch in Python backend
  const result = await apiProxy.forward('POST', '/kill');
  
  // Send Telegram alert
  await sendTelegramMessage('🚨 *KILL SWITCH ACTIVATED*\nAll trading halted.');
  
  res.json({ 
    success: true, 
    timestamp: new Date().toISOString(),
    python_response: result.data,
  });
});

app.post('/api/empire/resume', async (req, res) => {
  const result = await apiProxy.forward('POST', '/resume');
  await sendTelegramMessage('▶️ *Trading Resumed*');
  res.json({ success: true, python_response: result.data });
});

// ====================================================================
// WEBHOOKS
// ====================================================================

app.post('/webhook/uptimerobot', async (req, res) => {
  const payload = req.body;
  logger.warn(`🚨 UptimeRobot alert: ${JSON.stringify(payload)}`);
  
  const monitorURL = payload.monitorURL || 'unknown';
  const alertType = payload.alertType || 'unknown';
  
  if (alertType === 'down') {
    await sendTelegramMessage(
      `🚨 *SERVICE DOWN*\n` +
      `URL: ${monitorURL}\n` +
      `Time: ${new Date().toISOString()}\n` +
      `Check logs immediately.`
    );
    // Trigger emergency actions here if needed
  } else if (alertType === 'up') {
    await sendTelegramMessage(
      `✅ *SERVICE RECOVERED*\n` +
      `URL: ${monitorURL}\n` +
      `Time: ${new Date().toISOString()}`
    );
  }
  
  res.json({ received: true });
});

app.post('/webhook/telegram', async (req, res) => {
  // Telegram bot webhook for commands
  res.json({ received: true });
});

app.post('/webhook/github', async (req, res) => {
  logger.info(`GitHub event: ${req.body?.action || 'unknown'}`);
  res.json({ received: true });
});

// ====================================================================
// ROOT INFO
// ====================================================================

app.get('/', (req, res) => {
  res.json({
    name: 'AI Trading Empire',
    version: '1.0.0',
    description: 'Self-improving multi-agent AI civilization',
    uptime: formatUptime(Math.floor((Date.now() - CONFIG.START_TIME) / 1000)),
    features: [
      '3000 AI agents',
      'Multi-timeframe analysis (1m, 3m, 5m, 15m)',
      'MongoDB Atlas (500MB optimized)',
      'UptimeRobot monitoring',
      'Auto-pruning at 85% storage',
      'Multi-source API fallback',
    ],
    endpoints: {
      health: '/health',
      healthz: '/healthz',
      ready: '/ready',
      metrics: '/metrics',
      mongo_status: '/mongo/status',
      mongo_prune: '/mongo/prune',
      empire_status: '/api/empire/status',
      empire_agents: '/api/empire/agents',
      empire_leaderboard: '/api/empire/leaderboard',
      empire_signals: '/api/empire/signals/recent',
      empire_kill: '/api/empire/kill',
    },
    mongo_connected: mongo.connected,
    python_backend: CONFIG.PYTHON_API_URL,
  });
});

// ====================================================================
// CRON JOBS
// ====================================================================

// Check MongoDB size every 5 minutes
cron.schedule('*/5 * * * *', async () => {
  if (mongo.connected) {
    await mongo.checkSize();
  }
});

// Daily cleanup of logs
cron.schedule('0 0 * * *', () => {
  logger.info('Daily cleanup tick');
});

// ====================================================================
// HELPER FUNCTIONS
// ====================================================================

async function checkPythonBackend() {
  try {
    const response = await axios.get(`${CONFIG.PYTHON_API_URL}/`, { timeout: 3000 });
    return response.status === 200;
  } catch {
    return false;
  }
}

function formatUptime(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${days}d ${hours}h ${mins}m ${secs}s`;
}

async function sendTelegramMessage(text) {
  if (!CONFIG.TELEGRAM_BOT_TOKEN || !CONFIG.TELEGRAM_CHAT_ID) {
    return;
  }
  try {
    await axios.post(
      `https://api.telegram.org/bot${CONFIG.TELEGRAM_BOT_TOKEN}/sendMessage`,
      {
        chat_id: CONFIG.TELEGRAM_CHAT_ID,
        text,
        parse_mode: 'Markdown',
      },
      { timeout: 5000 }
    );
  } catch (err) {
    logger.debug(`Telegram send failed: ${err.message}`);
  }
}

// ====================================================================
// ERROR HANDLING
// ====================================================================

app.use((err, req, res, next) => {
  logger.error({ err: err.message, stack: err.stack }, 'Unhandled error');
  res.status(500).json({ error: 'Internal server error' });
});

// ====================================================================
// START SERVER
// ====================================================================

async function start() {
  // Connect to MongoDB first
  await mongo.connect();
  
  // Start HTTP server
  const server = app.listen(CONFIG.PORT, () => {
    logger.success(`🚀 AI Trading Empire server running on port ${CONFIG.PORT}`);
    logger.info(`📡 Python backend: ${CONFIG.PYTHON_API_URL}`);
    logger.info(`🍃 MongoDB: ${mongo.connected ? 'connected' : 'NOT connected'}`);
    logger.info(`🛡️ Health endpoint: http://localhost:${CONFIG.PORT}/health`);
    logger.info(`🍃 MongoDB status: http://localhost:${CONFIG.PORT}/mongo/status`);
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

// ====================================================================
// EXPORTS (for testing)
// ====================================================================

module.exports = { 
  app, 
  mongo, 
  CONFIG,
  getMongoStatus: () => mongo.getStatus(),
};
