"""
News Ingester + FinBERT sentiment.
"""
import asyncio
from typing import Dict
from utils.logger import get_module_logger

log = get_module_logger("ingest_news")


class NewsIngester:
    def __init__(self, config: dict, db):
        self.config = config
        self.db = db
        self._pipeline = None
    
    def _init_pipeline(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
                self._pipeline = pipeline(
                    "sentiment-analysis",
                    model="ProsusAI/finbert",
                    tokenizer="ProsusAI/finbert",
                )
                log.success("✓ FinBERT loaded")
            except Exception as e:
                log.warning(f"FinBERT load failed: {e}")
    
    def score_sentiment(self, text: str) -> Dict[str, float]:
        self._init_pipeline()
        if self._pipeline is None:
            return {"label": "neutral", "score": 0.0, "confidence": 0.0}
        try:
            text = text[:512]
            result = self._pipeline(text)[0]
            label = result["label"].lower()
            score_map = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}
            return {"label": label, "score": score_map.get(label, 0.0), "confidence": result["score"]}
        except Exception:
            return {"label": "neutral", "score": 0.0, "confidence": 0.0}
    
    async def get_recent_sentiment(self, symbol: str = "BTC", hours: int = 24) -> Dict:
        from datetime import datetime
        cutoff = int((datetime.now().timestamp() - hours * 3600) * 1000)
        loop = asyncio.get_event_loop()
        def _q():
            cur = self.db.conn.execute(
                "SELECT sentiment, confidence FROM news WHERE timestamp >= ? AND symbols LIKE ?",
                (cutoff, f"%{symbol}%")
            )
            return cur.fetchall()
        rows = await loop.run_in_executor(None, _q)
        if not rows:
            return {"avg_sentiment": 0, "count": 0, "bullish_pct": 0.5}
        sentiments = [r[0] for r in rows]
        confidences = [r[1] for r in rows]
        avg_sentiment = sum(s * c for s, c in zip(sentiments, confidences)) / max(sum(confidences), 1)
        bullish_pct = sum(1 for s in sentiments if s > 0.1) / len(sentiments)
        return {"avg_sentiment": avg_sentiment, "count": len(sentiments), "bullish_pct": bullish_pct}
    
    async def ingest_cycle(self):
        log.info("News ingest cycle")
        # In real impl: fetch from NewsAPI/CryptoPanic, score with FinBERT
