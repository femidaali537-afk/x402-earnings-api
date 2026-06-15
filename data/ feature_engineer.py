import pandas as pd
import numpy as np

class FeatureEngineer:
    def compute_features(self, df):
        if df.empty or len(df) < 20: return df
        df = df.copy()
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain/(loss+1e-9))))
        # EMA
        df['ema_21'] = df['close'].ewm(span=21).mean()
        return df.dropna()