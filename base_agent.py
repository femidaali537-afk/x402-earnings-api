"""
Base Agent — abstract class for all agents.

Every agent in the civilization inherits from this.
Defines:
  - AgentSignal (vote format)
  - AgentDNA (mutable genome for evolution)
  - analyze() — must be implemented
  - get_metrics() — performance tracking
"""
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
import numpy as np


@dataclass
class AgentSignal:
    """Every agent's output — the 'vote' in consensus."""
    agent_id: str
    agent_name: str
    agent_type: str
    symbol: str
    side: str                       # 'buy', 'sell', 'hold'
    confidence: float               # 0 to 1
    reasoning: str = ""
    features: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "symbol": self.symbol,
            "side": self.side,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "features": self.features,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentDNA:
    """
    Mutable genome — Factory mutates this to evolve new agents.
    Each agent decides its OWN behavior via DNA parameters.
    """
    params: Dict[str, Any] = field(default_factory=dict)
    fitness: float = 0.0
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def mutate(self, rate: float = 0.1) -> "AgentDNA":
        """Apply random mutation to numeric params."""
        import copy
        new_dna = copy.deepcopy(self)
        for k, v in new_dna.params.items():
            if isinstance(v, list) and len(v) > 0 and np.random.random() < rate:
                if isinstance(v[0], (int, float)):
                    new_dna.params[k] = float(np.random.choice(v))
            elif isinstance(v, (int, float)) and np.random.random() < rate:
                new_dna.params[k] = v * (1 + np.random.normal(0, 0.1))
                new_dna.params[k] = max(0.001, new_dna.params[k])
            elif isinstance(v, dict) and np.random.random() < rate:
                # Mutate a random sub-key
                for sk in v:
                    if isinstance(v[sk], (int, float)):
                        v[sk] = v[sk] * (1 + np.random.normal(0, 0.1))
                        v[sk] = max(0.001, min(1.0, v[sk]))
        return new_dna
    
    def crossover(self, other: "AgentDNA") -> "AgentDNA":
        """Combine DNA with another agent."""
        import copy
        new_dna = copy.deepcopy(self)
        for k in new_dna.params:
            if k in other.params and np.random.random() < 0.5:
                new_dna.params[k] = other.params[k]
            elif isinstance(new_dna.params.get(k), dict) and isinstance(other.params.get(k), dict):
                # Mix dict params too
                for sk in new_dna.params[k]:
                    if sk in other.params[k] and np.random.random() < 0.5:
                        new_dna.params[k][sk] = other.params[k][sk]
        new_dna.parent_ids = [self.agent_id, other.agent_id]
        new_dna.generation = max(self.generation, other.generation) + 1
        return new_dna


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Every agent implements analyze() and self-improves.
    """
    
    def __init__(self, name: str, agent_type: str, weight: float = 1.0, dna: Optional[AgentDNA] = None):
        self.name = name
        self.agent_type = agent_type
        self.weight = weight
        self.dna = dna or AgentDNA(params={})
        self.performance_history: List[Dict] = []
        self.trade_count = 0
        self.win_count = 0
        self.enabled = True
    
    @abstractmethod
    async def analyze(self, symbol: str, market_data: Dict[str, Any]) -> AgentSignal:
        """Analyze market and return signal. Must be implemented."""
        pass
    
    def record_outcome(self, pnl: float, pnl_pct: float):
        """Track prediction outcomes for self-learning."""
        self.trade_count += 1
        if pnl > 0:
            self.win_count += 1
        self.performance_history.append({
            "timestamp": datetime.now().isoformat(),
            "pnl": pnl, "pnl_pct": pnl_pct,
        })
    
    def get_metrics(self) -> Dict:
        """Performance metrics for Owner to evaluate."""
        if not self.performance_history:
            return {"sharpe": 0, "winrate": 0, "total_trades": 0, "profit_factor": 0, "max_drawdown": 0}
        
        pnls = [t["pnl"] for t in self.performance_history[-100:]]
        wins = sum(1 for p in pnls if p > 0)
        winrate = wins / len(pnls) if pnls else 0
        
        if len(pnls) > 1:
            mean = np.mean(pnls)
            std = np.std(pnls)
            sharpe = (mean / std) * np.sqrt(252) if std > 0 else 0
        else:
            sharpe = 0
        
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit
        
        return {
            "sharpe": float(sharpe),
            "winrate": float(winrate),
            "profit_factor": float(profit_factor),
            "max_drawdown": self._calc_max_drawdown(pnls),
            "total_trades": self.trade_count,
        }
    
    def _calc_max_drawdown(self, pnls: List[float]) -> float:
        if not pnls:
            return 0.0
        cumulative = np.cumsum(pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdowns = (peak - cumulative) / (np.abs(peak) + 1e-8)
        return float(drawdowns.max())
    
    def kill(self):
        """Retire this agent (called by Owner)."""
        self.enabled = False
    
    def clone_with_dna(self, new_dna: AgentDNA) -> "BaseAgent":
        """Create variant with new DNA (used by Factory)."""
        import copy
        new_agent = copy.copy(self)
        new_agent.dna = new_dna
        new_agent.performance_history = []
        new_agent.trade_count = 0
        new_agent.win_count = 0
        return new_agent
    
    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name} type={self.agent_type}>"
