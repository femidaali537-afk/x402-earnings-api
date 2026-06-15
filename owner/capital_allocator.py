"""
Capital Allocator — Kelly/risk-parity/equal methods.
"""
from typing import Dict
from utils.logger import get_module_logger

log = get_module_logger("capital_allocator")


class CapitalAllocator:
    def __init__(self, config: dict):
        self.method = config.get("capital_allocation_method", "kelly")
    
    def allocate(self, agents: Dict, total_capital: float) -> Dict[str, float]:
        if not agents:
            return {}
        if self.method == "equal":
            per = total_capital / len(agents)
            return {n: per for n in agents}
        if self.method == "kelly":
            sharpes = {n: max(0, a.get_metrics().get("sharpe", 0)) for n, a in agents.items()}
            total = sum(sharpes.values())
            if total == 0:
                return {n: total_capital / len(agents) for n in agents}
            return {n: (s / total) * total_capital for n, s in sharpes.items()}
        if self.method == "risk_parity":
            inv_vols = {n: 1.0 / max(0.01, a.get_metrics().get("max_drawdown", 0.01)) for n, a in agents.items()}
            total = sum(inv_vols.values())
            return {n: (v / total) * total_capital for n, v in inv_vols.items()}
        return {n: total_capital / len(agents) for n in agents}
