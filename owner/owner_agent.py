"""
OWNER AGENT — Meta-Orchestrator (VISION-ALIGNED)

Per user's vision:
  - Owner creates 3000 AI agents (all active 24/7)
  - NO pre-defined strategies — agents decide themselves
  - Agents self-improve from their own mistakes
  - Factory spawns agents dynamically with random DNA
  - Each agent is a DynamicAgent that decides:
      * what data to look at
      * what features matter
      * what decision logic to use
      * what risk profile to follow

The Owner:
  1. Gets agents from Factory (no pre-defined imports)
  2. All agents run in parallel (all 3000 active)
  3. Collects their votes (signals)
  4. Aggregates via weighted consensus
  5. Routes through Risk Manager (safety gatekeeper)
  6. Executes via Paper Trader
  7. Tracks performance per agent
  8. Tells Factory when to evolve
"""
import asyncio
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from utils.logger import get_module_logger
from data.feature_engineer import FeatureEngineer
from data.ingest_news import NewsIngester
from data.ingest_onchain import OnChainIngester
from agents.base_agent import BaseAgent, AgentSignal
from agents.risk_manager import RiskManagerAgent  # SAFETY ONLY — not a strategy
from factory.agent_factory import AgentFactory, DynamicAgent

log = get_module_logger("owner")


class OwnerAgent:
    """
    The Boss. Manages 3000 dynamic agents (all active 24/7).
    Uses Factory to spawn NEW agents (not pre-defined ones).
    """
    
    def __init__(self, config, db, guardrails, perf_tracker, capital_allocator):
        self.config = config
        self.owner_cfg = config["owner"]
        self.db = db
        self.guardrails = guardrails
        self.perf_tracker = perf_tracker
        self.capital_allocator = capital_allocator
        
        # Factory will spawn agents dynamically
        self.factory: Optional[AgentFactory] = None
        
        # All active agents (started as empty, populated by Factory)
        self.live_agents: Dict[str, BaseAgent] = {}
        
        # Data sources
        self.feature_eng = FeatureEngineer(config)
        self.news_ingester = NewsIngester(config, db)
        self.onchain_ingester = OnChainIngester(config, db)
        
        # Portfolio state
        self.equity = self.config["backtest"]["initial_capital"]
        self.positions: Dict[str, dict] = {}
        self.recent_signals: deque = deque(maxlen=1000)
        self.last_review = 0
        self.regime = "unknown"
        
        # Market data cache
        self.market_cache: Dict[str, dict] = {}
    
    async def initialize(self):
        """
        Initialize civilization.
        Owner does NOT pre-create agents — Factory does that.
        Owner just connects to Factory and gets the dynamic agents.
        """
        log.info("👑 Owner Agent initializing civilization...")
        
        # Step 1: Initialize Factory (will spawn 50 random-DNA agents to start)
        self.factory = AgentFactory(self.config, self, self.db)
        await self.factory.initialize()
        
        # Step 2: Get initial population from Factory
        # Each agent has its own RANDOM DNA — no pre-defined strategy
        for agent in self.factory.population:
            self.live_agents[agent.name] = agent
        
        # Step 3: Spawn Risk Manager (SAFETY ONLY — not a trading strategy)
        # Risk Manager has a fixed DNA because it enforces sacred limits
        # It's not a "strategy" — it's the gatekeeper
        risk_agent = RiskManagerAgent()
        self.live_agents["risk_manager"] = risk_agent
        
        log.success(f"✓ Civilization online: {len(self.live_agents)} agents")
        log.info(f"   • {len(self.factory.population)} DynamicAgents (each with random DNA)")
        log.info(f"   • 1 RiskManager (safety gatekeeper)")
        log.info(f"   • Each agent decides its OWN strategy based on its DNA")
    
    async def spawn_more_agents(self, count: int = 50):
        """
        Spawn MORE agents (called periodically to grow toward 3000).
        Owner tells Factory to create new random-DNA agents.
        """
        if self.factory is None:
            log.error("Factory not initialized")
            return
        
        for _ in range(count):
            new_agent = self.factory.spawn_new_agent()
            self.live_agents[new_agent.name] = new_agent
        
        log.info(f"➕ Spawned {count} new agents. Total: {len(self.live_agents)}")
    
    async def tick(self):
        """
        Main loop tick — runs every review_interval_minutes.
        """
        try:
            now = time.time()
            if now - self.last_review < self.owner_cfg["review_interval_minutes"] * 60:
                return
            
            log.info(f"👑 Owner tick (cycle #{self.last_review // 60 + 1})")
            self.last_review = now
            
            # Step 1: Refresh market data
            await self._refresh_market_data()
            
            # Step 2: Detect regime
            await self._detect_regime()
            
            # Step 3: Gather signals from ALL agents (3000 in parallel)
            signals = await self._gather_signals()
            
            # Step 4: Aggregate via weighted consensus
            consensus = self._aggregate_signals(signals)
            
            # Step 5: Risk Manager validation
            decision = await self._risk_check(consensus)
            
            # Step 6: Execute if approved
            if decision["approved"]:
                await self._execute_decision(decision)
                log.success(
                    f"📊 TRADE: {decision['side'].upper()} {decision['symbol']} "
                    f"size={decision['size_pct']:.3f} conf={decision['confidence']:.2f} "
                    f"agents_agreed={decision.get('n_agents', 0)}"
                )
            
            # Step 7: Evaluate agent performance
            await self._evaluate_agents()
            
            # Step 8: Trigger factory evolution (weekly)
            if self.factory:
                await self.factory.tick()
            
            # Step 9: Update equity
            await self._update_equity()
            
        except Exception as e:
            log.error(f"Owner tick error: {e}")
            import traceback
            traceback.print_exc()
    
    # ==================================================================
    # MARKET DATA REFRESH
    # ==================================================================
    async def _refresh_market_data(self):
        """Pull latest OHLCV for all tracked symbols."""
        symbols = (
            self.config["data"]["crypto"]["symbols"] +
            self.config["data"]["forex"]["symbols"]
        )
        for symbol in symbols:
            try:
                tf = "1h" if "/" in symbol else "H1"
                df = await self.db.get_ohlcv(symbol, tf, limit=300)
                if not df.empty:
                    self.market_cache[symbol] = {
                        "ohlcv": df,
                        "last_close": float(df["close"].iloc[-1]),
                        "last_update": time.time(),
                    }
                    self.guardrails.update_data_timestamp(time.time())
            except Exception as e:
                log.debug(f"Data refresh failed for {symbol}: {e}")
    
    # ==================================================================
    # REGIME DETECTION
    # ==================================================================
    async def _detect_regime(self):
        """Detect market regime."""
        btc_data = self.market_cache.get("BTC/USDT", {})
        df = btc_data.get("ohlcv")
        if df is None or len(df) < 50:
            return
        
        try:
            returns = df["close"].pct_change().dropna().tail(50)
            volatility = float(returns.std())
            
            if volatility > 0.04:
                self.regime = "volatile"
            elif abs(returns.mean()) > volatility * 0.3:
                self.regime = "trending"
            else:
                self.regime = "ranging"
            
            log.debug(f"Regime: {self.regime} (vol={volatility:.4f})")
        except Exception as e:
            log.debug(f"Regime detection error: {e}")
    
    # ==================================================================
    # SIGNAL GATHERING — ALL agents vote in parallel
    # ==================================================================
    async def _gather_signals(self) -> Dict[str, Dict[str, AgentSignal]]:
        """
        All 3000 agents analyze the market in parallel.
        Each returns its OWN decision (based on its own DNA).
        """
        signals = {}
        
        for symbol, data in self.market_cache.items():
            # Add sentiment + onchain data
            try:
                sent = await self.news_ingester.get_recent_sentiment(
                    symbol.split("/")[0], hours=24
                )
                data["sentiment"] = sent
            except Exception:
                data["sentiment"] = {}
            
            if "BTC" in symbol:
                try:
                    data["onchain"] = await self.onchain_ingester.get_snapshot("BTC")
                except Exception:
                    data["onchain"] = {}
            
            # Query all agents (parallel)
            symbol_signals = {}
            tasks = []
            
            for agent_name, agent in self.live_agents.items():
                if not agent.enabled or agent_name == "risk_manager":
                    continue
                tasks.append(self._query_agent(agent, symbol, data, agent_name, symbol_signals))
            
            # Run all agents in parallel
            await asyncio.gather(*tasks, return_exceptions=True)
            signals[symbol] = symbol_signals
            
            self.recent_signals.append({
                "timestamp": time.time(),
                "symbol": symbol,
                "signals": symbol_signals,
            })
        
        return signals
    
    async def _query_agent(self, agent, symbol, data, agent_name, signals_dict):
        """Query a single agent."""
        try:
            sig = await agent.analyze(symbol, data)
            signals_dict[agent_name] = sig
            await self.db.record_signal(
                agent_name, symbol, sig.side, sig.confidence, sig.features
            )
        except Exception as e:
            log.debug(f"Agent {agent_name} failed on {symbol}: {e}")
    
    # ==================================================================
    # WEIGHTED CONSENSUS AGGREGATION
    # ==================================================================
    def _aggregate_signals(
        self, all_signals: Dict[str, Dict[str, AgentSignal]]
    ) -> Dict[str, dict]:
        """
        Aggregate 3000 agent votes via weighted consensus.
        Each agent votes BUY/SELL/HOLD based on its OWN DNA.
        Disagreement = NO TRADE.
        """
        consensus = {}
        
        for symbol, sigs in all_signals.items():
            buy_score = 0.0
            sell_score = 0.0
            contributing = []
            
            for agent_name, sig in sigs.items():
                if sig.side == "hold":
                    continue
                
                agent = self.live_agents.get(agent_name)
                weight = agent.weight if agent else 1.0
                contribution = weight * sig.confidence
                
                if sig.side == "buy":
                    buy_score += contribution
                elif sig.side == "sell":
                    sell_score += contribution
                
                contributing.append((agent_name, sig.side, sig.confidence))
            
            net_score = buy_score - sell_score
            
            # Strong consensus = trade, weak = no trade
            if net_score > 1.0:    # need strong agreement
                side = "buy"
                confidence = min(0.95, abs(net_score) / 10)
            elif net_score < -1.0:
                side = "sell"
                confidence = min(0.95, abs(net_score) / 10)
            else:
                side = "hold"
                confidence = 0.0
            
            consensus[symbol] = {
                "side": side,
                "confidence": confidence,
                "buy_score": buy_score,
                "sell_score": sell_score,
                "net_score": net_score,
                "n_agents": len(contributing),
                "contributing": contributing,
            }
        
        return consensus
    
    # ==================================================================
    # RISK MANAGER VALIDATION
    # ==================================================================
    async def _risk_check(self, consensus: Dict[str, dict]) -> dict:
        """Pass consensus through Risk Manager (final veto)."""
        best = max(
            consensus.items(),
            key=lambda x: x[1]["confidence"],
            default=(None, None)
        )
        if best[0] is None or best[1]["side"] == "hold":
            return {"approved": False, "reason": "no_consensus"}
        
        symbol, decision = best
        risk_agent = self.live_agents.get("risk_manager")
        if risk_agent is None:
            return {"approved": False, "reason": "no_risk_manager"}
        
        market_data = self.market_cache.get(symbol, {})
        
        # Calculate ATR for position sizing
        atr = 0.0
        df = market_data.get("ohlcv")
        if df is not None and len(df) > 14:
            tr = pd.concat([
                df["high"] - df["low"],
                (df["high"] - df["close"].shift()).abs(),
                (df["low"] - df["close"].shift()).abs(),
            ], axis=1).max(axis=1)
            atr = float(tr.rolling(14).mean().iloc[-1])
        
        # Position size (Kelly-fraction)
        size = risk_agent.calculate_position_size(
            equity=self.equity,
            signal_confidence=decision["confidence"],
            atr=atr,
            price=market_data.get("last_close", 1),
        )
        
        # Build proposed trade + portfolio state
        proposed_trade = {"side": decision["side"], "size_pct": size}
        portfolio = {
            "daily_pnl_pct": (self.guardrails.state.daily_pnl / self.equity) if self.equity else 0,
            "current_drawdown_pct": (
                (self.guardrails.state.peak_equity - self.guardrails.state.current_equity)
                / self.guardrails.state.peak_equity
            ) if self.guardrails.state.peak_equity > 0 else 0,
            "open_positions": len(self.positions),
            "total_exposure_pct": sum(
                p.get("size_pct", 0) for p in self.positions.values()
            ),
        }
        
        # Submit to Risk Manager
        risk_signal = await risk_agent.analyze(
            symbol,
            {"proposed_trade": proposed_trade, "portfolio": portfolio}
        )
        
        # Also check hard guardrails
        allowed, reason = self.guardrails.check_trade_allowed(
            symbol=symbol,
            side=decision["side"],
            size_pct=size,
            equity=self.equity,
        )
        
        if not allowed:
            return {"approved": False, "reason": reason}
        if not risk_signal.features.get("approved", False):
            return {"approved": False, "reason": risk_signal.reasoning}
        
        return {
            "approved": True,
            "symbol": symbol,
            "side": decision["side"],
            "confidence": decision["confidence"],
            "size_pct": size,
            "atr": atr,
            "price": market_data.get("last_close", 0),
            "n_agents": decision["n_agents"],
        }
    
    # ==================================================================
    # EXECUTION (via Paper Trader)
    # ==================================================================
    async def _execute_decision(self, decision: dict):
        """Open trade via Paper Trader."""
        from execution.paper_trader import PaperTrader
        trader = PaperTrader(self.config, self)
        trade_id = await trader.open_trade(
            symbol=decision["symbol"],
            side=decision["side"],
            size_pct=decision["size_pct"],
            price=decision["price"],
            atr=decision["atr"],
        )
        if trade_id:
            log.success(
                f"📊 TRADE OPENED: {decision['side'].upper()} {decision['symbol']} "
                f"size=${self.equity * decision['size_pct']:.2f} "
                f"agents_agreed={decision['n_agents']}"
            )
    
    # ==================================================================
    # AGENT EVALUATION
    # ==================================================================
    async def _evaluate_agents(self):
        """Evaluate all dynamic agents based on their predictions."""
        min_trades = self.owner_cfg.get("min_trades_before_eval", 30)
        kill_threshold = self.owner_cfg.get("kill_threshold_sharpe", -0.3)
        
        to_kill = []
        for name, agent in list(self.live_agents.items()):
            if name == "risk_manager":
                continue  # Never kill safety
            metrics = agent.get_metrics()
            if metrics.get("total_trades", 0) >= min_trades:
                if metrics.get("sharpe", 0) < kill_threshold:
                    to_kill.append(name)
                    log.warning(f"⚠️ Killing {name}: sharpe={metrics['sharpe']:.2f}")
                await self.db.record_performance(name, metrics)
        
        for name in to_kill:
            self.live_agents[name].kill()
            del self.live_agents[name]
    
    # ==================================================================
    # EQUITY UPDATE
    # ==================================================================
    async def _update_equity(self):
        """Mark-to-market equity."""
        total = self.equity
        for symbol, pos in self.positions.items():
            data = self.market_cache.get(symbol, {})
            current_price = data.get("last_close", pos.get("entry_price", 0))
            pnl = (current_price - pos["entry_price"]) * pos["size"] * pos.get("side_multiplier", 1)
            total += pnl
        
        new_exposure = sum(p.get("size_pct", 0) for p in self.positions.values())
        self.guardrails.update_post_trade(
            pnl=0,
            equity=total,
            new_exposure_pct=new_exposure,
            position_opened=False,
        )
    
    # ==================================================================
    # PUBLIC API
    # ==================================================================
    def get_status(self) -> dict:
        """Status for API/dashboard."""
        return {
            "equity": self.equity,
            "regime": self.regime,
            "n_agents": len(self.live_agents),
            "n_dynamic_agents": len([a for a in self.live_agents.values() if isinstance(a, DynamicAgent)]),
            "agents": {
                name: {
                    "type": a.agent_type,
                    "enabled": a.enabled,
                    "weight": a.weight,
                    "fitness": a.dna.fitness if a.dna else 0,
                }
                for name, a in list(self.live_agents.items())[:20]  # first 20 for display
            },
            "guardrails": self.guardrails.get_state(),
            "open_positions": len(self.positions),
        }
    
    async def shutdown(self):
        log.info("👑 Owner Agent shutting down")
        if self.factory:
            await self.factory.shutdown()
