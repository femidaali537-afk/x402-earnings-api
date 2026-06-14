"""
Risk Manager Agent — THE FINAL GATEKEEPER.

Every proposed trade MUST pass through this agent.
If Risk Manager says NO, no trade happens. No exceptions.

Responsibilities:
  1. Validate every proposed trade against portfolio constraints
  2. Calculate position size (Kelly-fraction based)
  3. Approve or veto trades
  4. Track portfolio-level risk (correlation, exposure)

This is a SPECIAL agent — it doesn't generate directional signals.
It VALIDATES signals from other agents (trend, sentiment, etc.).
"""
from typing import Dict, Any, Optional, List
from agents.base_agent import BaseAgent, AgentSignal, AgentDNA
from utils.logger import get_module_logger

log = get_module_logger("risk_manager")


class RiskManagerAgent(BaseAgent):
    """
    The final veto authority.
    
    Flow:
      Other agents propose: "BUY BTC/USDT"
      Risk Manager checks:
        ✓ Position size < 2%?
        ✓ Total exposure < 30%?
        ✓ Not too correlated with other positions?
        ✓ Drawdown within limits?
      Risk Manager decides: APPROVE or REJECT
    """
    
    def __init__(self, dna: AgentDNA = None, weight: float = 2.0):
        # Risk manager gets HIGHER weight in consensus
        if dna is None:
            dna = AgentDNA(params={
                "max_position_pct": 0.02,        # 2% max per trade
                "max_daily_loss_pct": 0.03,       # 3% daily loss limit
                "max_drawdown_pct": 0.15,         # 15% → kill switch
                "max_open_positions": 5,
                "max_correlation": 0.7,
                "max_total_exposure_pct": 0.30,    # 30% total exposure
            })
        super().__init__(
            name="RiskManager",
            agent_type="risk",
            weight=weight,    # Higher weight = stronger vote
            dna=dna
        )
    
    async def analyze(self, symbol: str, market_data: Dict[str, Any]) -> AgentSignal:
        """
        Validates a proposed trade.
        
        market_data must contain:
          - proposed_trade: {"side": "buy"|"sell", "size_pct": 0.015, ...}
          - portfolio: {daily_pnl_pct, current_drawdown_pct, open_positions, total_exposure_pct, ...}
        
        Returns AgentSignal:
          - If approved: side = proposed side, confidence = high (0.95)
          - If rejected: side = "hold", reasoning = violation details
        """
        proposed = market_data.get("proposed_trade", {})
        portfolio = market_data.get("portfolio", {})
        
        # If no trade proposed, return neutral signal
        if not proposed:
            return AgentSignal(
                agent_id=self.dna.agent_id,
                agent_name=self.name,
                agent_type=self.agent_type,
                symbol=symbol,
                side="hold",
                confidence=1.0,
                reasoning="No trade proposed — risk manager idle",
                features={"approved": False, "reason": "no_proposal"}
            )
        
        p = self.dna.params
        violations = []
        
        # ============ CHECK 1: Position Size ============
        proposed_size = proposed.get("size_pct", 0)
        if proposed_size > p["max_position_pct"]:
            violations.append(
                f"Position size {proposed_size:.3f} > max {p['max_position_pct']}"
            )
        
        # ============ CHECK 2: Daily Loss Limit ============
        daily_pnl_pct = portfolio.get("daily_pnl_pct", 0)
        if daily_pnl_pct < -p["max_daily_loss_pct"]:
            violations.append(
                f"Daily loss {daily_pnl_pct:.3f} > limit {-p['max_daily_loss_pct']}"
            )
        
        # ============ CHECK 3: Drawdown ============
        current_dd = portfolio.get("current_drawdown_pct", 0)
        if current_dd > p["max_drawdown_pct"]:
            violations.append(
                f"Drawdown {current_dd:.3f} > max {p['max_drawdown_pct']}"
            )
        
        # ============ CHECK 4: Open Positions Count ============
        open_pos = portfolio.get("open_positions", 0)
        if open_pos >= p["max_open_positions"]:
            violations.append(
                f"Open positions {open_pos} >= max {p['max_open_positions']}"
            )
        
        # ============ CHECK 5: Total Exposure ============
        total_exposure = portfolio.get("total_exposure_pct", 0)
        if total_exposure + proposed_size > p["max_total_exposure_pct"]:
            violations.append(
                f"Total exposure {total_exposure + proposed_size:.3f} > {p['max_total_exposure_pct']}"
            )
        
        # ============ CHECK 6: Correlation (if provided) ============
        open_symbols = portfolio.get("open_symbols", [])
        correlation_matrix = market_data.get("correlation_matrix", {})
        for sym in open_symbols:
            key = f"{symbol}-{sym}"
            if key in correlation_matrix:
                corr = correlation_matrix[key]
                if abs(corr) > p["max_correlation"]:
                    violations.append(
                        f"High correlation with {sym}: {corr:.2f}"
                    )
        
        # ============ DECISION ============
        if violations:
            log.warning(f"REJECTED {proposed.get('side', '?')} {symbol}: {'; '.join(violations)}")
            return AgentSignal(
                agent_id=self.dna.agent_id,
                agent_name=self.name,
                agent_type=self.agent_type,
                symbol=symbol,
                side="hold",
                confidence=0.95,    # High confidence in REJECTION
                reasoning=f"REJECTED: {'; '.join(violations)}",
                features={
                    "violations": violations,
                    "approved": False,
                    "proposed_size": proposed_size,
                }
            )
        
        log.success(f"APPROVED {proposed.get('side', '?')} {symbol}: size={proposed_size:.3f}")
        return AgentSignal(
            agent_id=self.dna.agent_id,
            agent_name=self.name,
            agent_type=self.agent_type,
            symbol=symbol,
            side=proposed.get("side", "hold"),
            confidence=0.95,    # High confidence in APPROVAL
            reasoning=f"APPROVED: all checks passed. Size={proposed_size:.3f}, open_pos={open_pos}",
            features={
                "violations": [],
                "approved": True,
                "proposed_size": proposed_size,
            }
        )
    
    def calculate_position_size(
        self,
        equity: float,
        signal_confidence: float,
        atr: float,
        price: float,
    ) -> float:
        """
        Calculate optimal position size using Kelly-fraction method.
        
        Higher confidence → larger size
        Higher volatility → smaller size
        
        Returns: size as fraction of equity (e.g., 0.015 = 1.5%)
        """
        p = self.dna.params
        base_size = p["max_position_pct"]
        
        # Confidence multiplier (0.5x to 1.5x)
        conf_mult = 0.5 + signal_confidence  # conf=0 → 0.5x, conf=1 → 1.5x
        
        # Volatility adjustment (smaller size when volatile)
        atr_pct = atr / price if price > 0 else 0.01
        vol_mult = max(0.3, 1.0 - atr_pct * 10)  # 1% ATR → 0.9x, 5% ATR → 0.5x
        
        final_size = base_size * conf_mult * vol_mult
        
        # Hard cap at max position
        return min(final_size, p["max_position_pct"])
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        side: str,
        multiplier: float = 2.0,
    ) -> float:
        """
        Calculate stop loss using ATR (Average True Range).
        ATR-based stops adapt to current volatility.
        """
        sl_distance = atr * multiplier
        if side == "buy":
            return entry_price - sl_distance
        else:  # sell
            return entry_price + sl_distance
    
    def calculate_take_profit(
        self,
        entry_price: float,
        atr: float,
        side: str,
        multiplier: float = 4.0,
    ) -> float:
        """
        Calculate take profit using ATR.
        Default 4x ATR for 1:2 risk-reward ratio.
        """
        tp_distance = atr * multiplier
        if side == "buy":
            return entry_price + tp_distance
        else:  # sell
            return entry_price - tp_distance
