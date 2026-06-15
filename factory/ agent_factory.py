"""
AGENT FACTORY — Dynamic Agent Creation (KEY FILE!)

Per user's vision:
  - Owner creates 3000 AI agents (all active 24/7)
  - NO pre-defined strategies — agents decide themselves
  - Each agent has RANDOM DNA
  - Agents self-improve from mistakes

This file:
  1. Spawns agents with RANDOM DNA (no template)
  2. Each agent DECIDES its own:
     - data_focus (price vs volume vs news weights)
     - feature_weights (RSI vs MACD vs BB importance)
     - decision_logic (threshold vs weighted_sum)
     - risk_tolerance (0.3 to 1.0)
     - mutation_rate (how fast it evolves)
  3. Evolves population weekly (crossover + mutation)
"""
import asyncio
import random
import time
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from utils.logger import get_module_logger
from agents.base_agent import BaseAgent, AgentSignal, AgentDNA

log = get_module_logger("agent_factory")


class DynamicAgent(BaseAgent):
    """Generic agent with RANDOM DNA — decides own strategy."""
    
    def __init__(self, dna: AgentDNA = None, weight: float = 1.0, name: str = None):
        if dna is None:
            dna = self._random_dna()
        super().__init__(
            name=name or f"agent_{dna.agent_id}",
            agent_type="dynamic",
            weight=weight,
            dna=dna
        )
        self.lessons: List[str] = []
        self.prediction_history: List[Dict] = []
    
    @staticmethod
    def _random_dna() -> AgentDNA:
        """Generate RANDOM DNA — agent decides everything."""
        return AgentDNA(params={
            "data_focus": {
                "price_action": random.random(),
                "volume": random.random(),
                "orderbook": random.random(),
                "news": random.random(),
                "onchain": random.random(),
                "derivatives": random.random(),
            },
            "timeframe_focus": {
                "1m": random.random(),
                "3m": random.random(),
                "5m": random.random(),
                "15m": random.random(),
                "1h": random.random(),
            },
            "feature_weights": {
                "rsi": random.random(),
                "macd": random.random(),
                "ema_cross": random.random(),
                "bbands": random.random(),
                "adx": random.random(),
                "atr": random.random(),
                "volume_delta": random.random(),
            },
            "decision_type": random.choice(["threshold", "weighted_sum", "ensemble"]),
            "buy_threshold": random.uniform(0.5, 0.8),
            "sell_threshold": random.uniform(0.2, 0.5),
            "risk_tolerance": random.uniform(0.3, 1.0),
            "max_position_pct": random.uniform(0.005, 0.025),
            "sl_atr_multiplier": random.uniform(1.0, 3.0),
            "tp_atr_multiplier": random.uniform(2.0, 6.0),
            "max_hold_bars": random.randint(20, 200),
            "mutation_rate": random.uniform(0.05, 0.3),
            "memory_window": random.randint(50, 500),
            "preferred_regime": random.choice(["trending", "ranging", "volatile", "any"]),
        })
    
    async def analyze(self, symbol: str, market_data: Dict) -> AgentSignal:
        """Agent analyzes based on its OWN DNA."""
        df = market_data.get("ohlcv")
        if df is None or len(df) < 60:
            return AgentSignal(
                agent_id=self.dna.agent_id, agent_name=self.name,
                agent_type=self.agent_type, symbol=symbol,
                side="hold", confidence=0.0, reasoning="insufficient data"
            )
        
        p = self.dna.params
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        
        # Agent computes features IT cares about (per DNA)
        features = {}
        fw = p.get("feature_weights", {})
        
        if fw.get("rsi", 0) > 0.3:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1e-8)
            features["rsi"] = float((100 - (100 / (1 + rs))).iloc[-1])
        
        if fw.get("ema_cross", 0) > 0.3:
            ema_fast = close.ewm(span=12, adjust=False).mean().iloc[-1]
            ema_slow = close.ewm(span=50, adjust=False).mean().iloc[-1]
            features["ema_diff"] = float((ema_fast - ema_slow) / ema_slow)
        
        if fw.get("macd", 0) > 0.3:
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            features["macd"] = float((ema12 - ema26).iloc[-1])
        
        if fw.get("bbands", 0) > 0.3:
            sma = close.rolling(20).mean().iloc[-1]
            std = close.rolling(20).std().iloc[-1]
            features["bb_pct"] = float((close.iloc[-1] - sma) / (2 * std + 1e-8))
        
        # Agent decision based on its DNA
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        
        if "rsi" in features:
            w = fw.get("rsi", 0)
            if features["rsi"] < 30: buy_score += w
            elif features["rsi"] > 70: sell_score += w
            total_weight += w
        
        if "ema_diff" in features:
            w = fw.get("ema_cross", 0)
            if features["ema_diff"] > 0.01: buy_score += w
            elif features["ema_diff"] < -0.01: sell_score += w
            total_weight += w
        
        if "bb_pct" in features:
            w = fw.get("bbands", 0)
            if features["bb_pct"] < -0.8: buy_score += w
            elif features["bb_pct"] > 0.8: sell_score += w
            total_weight += w
        
        if "macd" in features:
            w = fw.get("macd", 0)
            if features["macd"] > 0: buy_score += w
            else: sell_score += w
            total_weight += w
        
        if total_weight == 0:
            side, confidence, reasoning = "hold", 0.0, "No weighted features"
        else:
            net = (buy_score - sell_score) / total_weight
            buy_th = p.get("buy_threshold", 0.6)
            if net > buy_th:
                side, confidence = "buy", min(0.95, net)
                reasoning = f"DNA-driven BUY: net={net:.2f}"
            elif net < buy_th - 1:
                side, confidence = "sell", min(0.95, abs(net))
                reasoning = f"DNA-driven SELL: net={net:.2f}"
            else:
                side, confidence, reasoning = "hold", 0.0, f"No clear signal: net={net:.2f}"
        
        atr = features.get("atr", float(close.iloc[-1] * 0.02))
        if side == "buy":
            sl = float(close.iloc[-1]) - atr * p.get("sl_atr_multiplier", 2.0)
            tp = float(close.iloc[-1]) + atr * p.get("tp_atr_multiplier", 4.0)
        elif side == "sell":
            sl = float(close.iloc[-1]) + atr * p.get("sl_atr_multiplier", 2.0)
            tp = float(close.iloc[-1]) - atr * p.get("tp_atr_multiplier", 4.0)
        else:
            sl = tp = None
        
        return AgentSignal(
            agent_id=self.dna.agent_id, agent_name=self.name,
            agent_type=self.agent_type, symbol=symbol,
            side=side, confidence=confidence, reasoning=reasoning,
            features={**features, "sl": sl, "tp": tp}
        )
    
    def learn_from_outcome(self, predicted_side: str, actual_outcome: float):
        """Agent learns from its own mistakes."""
        if actual_outcome < 0 and predicted_side != "hold":
            self.dna.params["mutation_rate"] = min(0.5, self.dna.params.get("mutation_rate", 0.1) * 1.1)
            self.lessons.append(f"Wrong prediction by ${abs(actual_outcome):.2f}")


class AgentFactory:
    """Spawns agents dynamically. Owner uses this to create 3000 agents."""
    
    def __init__(self, config, owner, db):
        self.config = config
        self.factory_cfg = config["factory"]
        self.owner = owner
        self.db = db
        self.population: List[DynamicAgent] = []
        self.generation = 0
        self.last_evolution = 0
        self.cycle_interval = self.factory_cfg["cycle_interval_hours"] * 3600
    
    async def initialize(self):
        """Seed population with random-DNA agents."""
        log.info("🧬 Factory spawning random-DNA agents")
        pop_size = self.factory_cfg["population_size"]
        for i in range(pop_size):
            agent = DynamicAgent(name=f"agent_{i:04d}")
            self.population.append(agent)
        log.success(f"✓ Spawned {len(self.population)} random-DNA agents")
    
    def spawn_new_agent(self) -> DynamicAgent:
        """Owner calls this to create a brand new agent."""
        new_agent = DynamicAgent(name=f"agent_spawned_{len(self.population):04d}")
        self.population.append(new_agent)
        log.info(f"➕ Spawned: {new_agent.name}")
        return new_agent
    
    async def tick(self):
        """Periodic evolution."""
        now = time.time()
        if now - self.last_evolution < self.cycle_interval:
            return
        if len(self.population) < 5:
            return
        await self.evolve_cycle()
        self.last_evolution = now
    
    async def evolve_cycle(self):
        """One generation of evolution."""
        log.info(f"🧬 Evolution cycle (gen {self.generation})")
        
        # Assign mock fitness (real impl would backtest)
        for agent in self.population:
            agent.dna.fitness = random.uniform(-1, 3)
        
        self.population.sort(key=lambda a: a.dna.fitness, reverse=True)
        
        # Elitism: top 10 survive
        elite = self.factory_cfg["elite_count"]
        new_pop = self.population[:elite]
        
        # Generate offspring
        while len(new_pop) < len(self.population):
            pa = max(random.sample(self.population, 3), key=lambda a: a.dna.fitness)
            pb = max(random.sample(self.population, 3), key=lambda a: a.dna.fitness)
            
            child_dna = pa.dna.crossover(pb.dna)
            child_dna = child_dna.mutate(rate=self.factory_cfg["mutation_rate"])
            child_agent = DynamicAgent(dna=child_dna, name=f"agent_gen{self.generation+1}_{len(new_pop):04d}")
            new_pop.append(child_agent)
        
        self.population = new_pop
        self.generation += 1
        log.success(f"✓ Gen {self.generation} evolved. Top fitness: {self.population[0].dna.fitness:.3f}")
    
    def get_best_agents(self, n: int = 10) -> List[DynamicAgent]:
        return sorted(self.population, key=lambda a: a.dna.fitness, reverse=True)[:n]
    
    async def shutdown(self):
        log.info("Factory shutting down")
