# data_client.py
import time
import requests
import pandas as pd
from dateutil import parser

class BaseDataClient:
    def get_minutes(self, symbol: str, limit: int, timeframe: str):
        """Return DataFrame with columns: t (timestamp), o, h, l, c, v"""
        raise NotImplementedError

class MockDataClient(BaseDataClient):
    """Mock returns random-ish data for local testing."""
    import numpy as np

    def get_minutes(self, symbol, limit=18, timeframe="1Min"):
        import numpy as np
        now = pd.Timestamp.utcnow().floor('min')
        idx = pd.date_range(end=now, periods=limit, freq='T')
        # create simple random walk
        base = 100 + np.cumsum(np.random.randn(limit) * 0.2)
        o = base + np.random.randn(limit)*0.02
        c = base + np.random.randn(limit)*0.02
        h = np.maximum(o, c) + np.abs(np.random.randn(limit)*0.05)
        l = np.minimum(o, c) - np.abs(np.random.randn(limit)*0.05)
        v = (np.abs(np.random.randn(limit))*1e5).astype(int) + 1000
        df = pd.DataFrame({'t': idx, 'o': o, 'h': h, 'l': l, 'c': c, 'v': v})
        df.set_index('t', inplace=True)
        return df

class AlpacaDataClient(BaseDataClient):
    def __init__(self, api_key, api_secret, base_url="https://data.alpaca.markets/v2"):
        self.key = api_key
        self.secret = api_secret
        self.base_url = base_url

    def _headers(self):
        return {"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret}

    def get_minutes(self, symbol, limit=18, timeframe="1Min"):
        # NOTE: adapt endpoint to the actual provider; this is a starting point.
        url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
        params = {"timeframe": "1Min", "limit": limit}
        r = requests.get(url, headers=self._headers(), params=params, timeout=10)
        r.raise_for_status()
        bars = r.json().get('bars', [])
        rows = []
        for b in bars:
            rows.append({
                't': pd.to_datetime(b['t']),
                'o': b['o'],
                'h': b['h'],
                'l': b['l'],
                'c': b['c'],
                'v': b['v']
            })
        df = pd.DataFrame(rows).set_index('t')
        return df
