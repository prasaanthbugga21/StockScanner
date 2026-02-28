"""
NSE India Stock Scanner — Minervini + Qullamaggie Criteria
Runs every Sunday 9PM EST via GitHub Actions
Outputs: sector_heatmap_data.json + updates Notion dashboard
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import requests
from datetime import datetime, timedelta
from jugaad_data.nse import NSELive
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DB_ID = os.environ.get("NOTION_DB_ID")

NSE_SECTORS = {
    "IT": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTIM.NS", "MPHASIS.NS", "COFORGE.NS", "PERSISTENT.NS", "KPITTECH.NS"],
    "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "SBIN.NS", "INDUSINDBK.NS", "BANDHANBNK.NS", "FEDERALBNK.NS", "IDFCFIRSTB.NS", "RBLBANK.NS"],
    "Pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "BIOCON.NS", "LUPIN.NS", "AUROPHARMA.NS", "TORNTPHARM.NS", "ALKEM.NS", "GLENMARK.NS"],
    "Auto": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "EICHERMOT.NS", "TVSMOTOR.NS", "ASHOKLEY.NS", "BALKRISIND.NS", "MOTHERSON.NS"],
    "FMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS", "MARICO.NS", "COLPAL.NS", "GODREJCP.NS", "EMAMILTD.NS", "VBL.NS"],
    "Metals": ["TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS", "SAIL.NS", "VEDL.NS", "COALINDIA.NS", "NMDC.NS", "MOIL.NS", "NATIONALUM.NS", "HINDCOPPER.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS", "GAIL.NS", "POWERGRID.NS", "NTPC.NS", "ADANIGREEN.NS", "TATAPOWER.NS", "CESC.NS"],
    "Realty": ["DLF.NS", "GODREJPROP.NS", "OBEROIRLTY.NS", "PRESTIGE.NS", "BRIGADE.NS", "SOBHA.NS", "PHOENIXLTD.NS", "MAHLIFE.NS", "SUNTECK.NS", "LODHA.NS"],
    "Chemicals": ["PIDILITIND.NS", "SRF.NS", "AARTIIND.NS", "DEEPAKNITRITE.NS", "NAVINFLUOR.NS", "FINPIPE.NS", "GALAXYSURF.NS", "TATACHEM.NS", "VINATI.NS", "CLEAN.NS"],
    "Capital Goods": ["LT.NS", "SIEMENS.NS", "ABB.NS", "BHEL.NS", "THERMAX.NS", "CUMMINSIND.NS", "AIAENG.NS", "GRINDWELL.NS", "CARBORUNDUM.NS", "SCHAEFFLER.NS"],
    "Consumer Durables": ["TITAN.NS", "HAVELLS.NS", "VOLTAS.NS", "BLUESTARCO.NS", "CROMPTON.NS", "DIXON.NS", "AMBER.NS", "VGUARD.NS", "BAJAJELEC.NS", "ORIENTELEC.NS"],
    "Financial Services": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "SBILIFE.NS", "HDFCLIFE.NS", "ICICIPRULI.NS", "CHOLAFIN.NS", "MUTHOOTFIN.NS", "MANAPPURAM.NS", "L&TFH.NS", "PNBHOUSING.NS"],
}

# ─────────────────────────────────────────────
# HELPER: Fetch OHLCV data
# ─────────────────────────────────────────────
def fetch_data(ticker, period="1y"):
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 50:
            return None
        df.dropna(inplace=True)
        return df
    except Exception:
        return None

# ─────────────────────────────────────────────
# MINERVINI SEPA CRITERIA
# ─────────────────────────────────────────────
def check_minervini(df):
    try:
        close = df["Close"]
        
        sma50  = close.rolling(50).mean()
        sma150 = close.rolling(150).mean()
        sma200 = close.rolling(200).mean()
        
        price = close.iloc[-1]
        s50   = sma50.iloc[-1]
        s150  = sma150.iloc[-1]
        s200  = sma200.iloc[-1]
        
        high_52w = close.rolling(252).max().iloc[-1]
        low_52w  = close.rolling(252).min().iloc[-1]
        
        # 200 SMA trending up (compare current vs 1 month ago)
        sma200_1m_ago = sma200.iloc[-22] if len(sma200) > 22 else sma200.iloc[0]
        sma200_trending_up = s200 > sma200_1m_ago
        
        criteria = {
            "price_above_sma50":        price > s50,
            "sma50_above_sma150":       s50 > s150,
            "sma150_above_sma200":      s150 > s200,
            "sma200_trending_up":       sma200_trending_up,
            "price_within_25pct_high":  price >= (0.75 * high_52w),
            "price_30pct_above_low":    price >= (1.30 * low_52w),
        }
        
        passed = sum(criteria.values())
        total  = len(criteria)
        score  = round(passed / total * 100, 1)
        
        return {
            "passed": passed == total,
            "score": score,
            "criteria": criteria
        }
    except Exception:
        return {"passed": False, "score": 0, "criteria": {}}

# ─────────────────────────────────────────────
# QULLAMAGGIE VCP + MOMENTUM CRITERIA
# ─────────────────────────────────────────────
def check_qullamaggie(df):
    try:
        close  = df["Close"]
        high   = df["High"]
        low    = df["Low"]
        volume = df["Volume"]
        
        # ADR% — Average Daily Range over last 21 days
        adr = ((high - low) / close).rolling(21).mean().iloc[-1] * 100
        
        # Volatility Contraction: compare last 3-week range vs prior 6-week range
        recent_range = (high.iloc[-15:].max() - low.iloc[-15:].min()) / close.iloc[-15]
        prior_range  = (high.iloc[-45:-15].max() - low.iloc[-45:-15].min()) / close.iloc[-45]
        vcp_contraction = recent_range < (prior_range * 0.6)  # 40%+ contraction
        
        # Volume dry-up: last 2-week avg volume < prior 4-week avg
        vol_recent = volume.iloc[-10:].mean()
        vol_prior  = volume.iloc[-30:-10].mean()
        volume_dryup = vol_recent < (vol_prior * 0.8)
        
        # Relative Strength proxy: stock return vs prior 3 months
        rs_period = min(63, len(close) - 1)
        stock_return = (close.iloc[-1] / close.iloc[-rs_period] - 1) * 100
        
        # Near 52-week high (within 15% = setting up for breakout)
        high_52w = high.rolling(252).max().iloc[-1]
        near_high = close.iloc[-1] >= (0.85 * high_52w)
        
        # Rising volume on up days (last 20 days)
        up_days    = df[df["Close"] > df["Close"].shift(1)].tail(20)
        down_days  = df[df["Close"] < df["Close"].shift(1)].tail(20)
        avg_up_vol   = up_days["Volume"].mean() if len(up_days) > 0 else 0
        avg_down_vol = down_days["Volume"].mean() if len(down_days) > 0 else 1
        vol_on_up_days = avg_up_vol > avg_down_vol
        
        criteria = {
            "adr_above_3pct":    adr > 3,
            "vcp_contraction":   vcp_contraction,
            "volume_dryup":      volume_dryup,
            "near_52w_high":     near_high,
            "vol_on_up_days":    vol_on_up_days,
            "strong_rs":         stock_return > 10,  # 10%+ in 3 months
        }
        
        passed = sum(criteria.values())
        total  = len(criteria)
        score  = round(passed / total * 100, 1)
        
        return {
            "passed": passed >= 4,  # Qullamaggie: 4+ of 6
            "score": score,
            "adr": round(adr, 2),
            "rs_return": round(stock_return, 2),
            "criteria": criteria
        }
    except Exception:
        return {"passed": False, "score": 0, "adr": 0, "rs_return": 0, "criteria": {}}

# ─────────────────────────────────────────────
# VOLUME SURGE INDICATOR
# ─────────────────────────────────────────────
def check_volume_surge(df):
    try:
        volume = df["Volume"]
        close  = df["Close"]
        
        avg_vol_50   = volume.rolling(50).mean().iloc[-1]
        last_week_vol = volume.iloc[-5:].mean()
        surge_ratio  = last_week_vol / avg_vol_50 if avg_vol_50 > 0 else 0
        
        # Price direction during surge
        price_change = (close.iloc[-1] / close.iloc[-6] - 1) * 100
        
        return {
            "surge_ratio":   round(surge_ratio, 2),
            "surge_detected": surge_ratio > 1.5,
            "price_change_5d": round(price_change, 2),
            "bullish_surge":   surge_ratio > 1.5 and price_change > 0
        }
    except Exception:
        return {"surge_ratio": 1.0, "surge_detected": False, "price_change_5d": 0, "bullish_surge": False}

# ─────────────────────────────────────────────
# SCAN ALL SECTORS
# ─────────────────────────────────────────────
def scan_all_sectors():
    results = {}
    scan_date = datetime.now().strftime("%Y-%m-%d %H:%M EST")
    
    print(f"\n{'='*60}")
    print(f"  NSE MARKET SCAN — {scan_date}")
    print(f"{'='*60}\n")
    
    for sector, tickers in NSE_SECTORS.items():
        print(f"Scanning {sector}...", end=" ", flush=True)
        
        sector_data = {
            "sector": sector,
            "total_stocks": len(tickers),
            "minervini_passed": 0,
            "qullamaggie_passed": 0,
            "volume_surge_count": 0,
            "bullish_surge_count": 0,
            "stocks": [],
            "avg_minervini_score": 0,
            "avg_qullamaggie_score": 0,
            "avg_adr": 0,
        }
        
        m_scores, q_scores, adrs = [], [], []
        
        for ticker in tickers:
            df = fetch_data(ticker)
            if df is None:
                continue
            
            m_result = check_minervini(df)
            q_result = check_qullamaggie(df)
            v_result = check_volume_surge(df)
            
            if m_result["passed"]:
                sector_data["minervini_passed"] += 1
            if q_result["passed"]:
                sector_data["qullamaggie_passed"] += 1
            if v_result["surge_detected"]:
                sector_data["volume_surge_count"] += 1
            if v_result["bullish_surge"]:
                sector_data["bullish_surge_count"] += 1
            
            m_scores.append(m_result["score"])
            q_scores.append(q_result["score"])
            adrs.append(q_result["adr"])
            
            sector_data["stocks"].append({
                "ticker": ticker,
                "minervini_score": m_result["score"],
                "qullamaggie_score": q_result["score"],
                "minervini_passed": m_result["passed"],
                "qullamaggie_passed": q_result["passed"],
                "adr": q_result["adr"],
                "rs_return": q_result["rs_return"],
                "volume_surge": v_result,
            })
        
        n = len(sector_data["stocks"]) or 1
        sector_data["avg_minervini_score"] = round(np.mean(m_scores) if m_scores else 0, 1)
        sector_data["avg_qullamaggie_score"] = round(np.mean(q_scores) if q_scores else 0, 1)
        sector_data["avg_adr"] = round(np.mean(adrs) if adrs else 0, 2)
        sector_data["minervini_pct"] = round(sector_data["minervini_passed"] / n * 100, 1)
        sector_data["qullamaggie_pct"] = round(sector_data["qullamaggie_passed"] / n * 100, 1)
        sector_data["surge_pct"] = round(sector_data["bullish_surge_count"] / n * 100, 1)
        
        # Composite bullish score (0–100)
        sector_data["bullish_score"] = round(
            sector_data["avg_minervini_score"] * 0.4 +
            sector_data["avg_qullamaggie_score"] * 0.4 +
            min(sector_data["surge_pct"], 100) * 0.2,
            1
        )
        
        results[sector] = sector_data
        print(f"✓  Minervini: {sector_data['minervini_pct']}%  |  Qullamaggie: {sector_data['qullamaggie_pct']}%  |  Bull Score: {sector_data['bullish_score']}")
    
    output = {
        "scan_date": scan_date,
        "sectors": results
    }
    
    # Save JSON
    with open("sector_heatmap_data.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print("\n✅ Scan complete. Data saved to sector_heatmap_data.json")
    return output

# ─────────────────────────────────────────────
# NOTION INTEGRATION
# ─────────────────────────────────────────────
def update_notion(scan_data):
    if not NOTION_TOKEN or not NOTION_DB_ID:
        print("⚠️  Notion credentials not set — skipping Notion update")
        return
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    sectors = scan_data["sectors"]
    
    for sector_name, data in sectors.items():
        sentiment = "🟢 Bullish" if data["bullish_score"] >= 60 else "🔴 Bearish" if data["bullish_score"] < 35 else "🟡 Neutral"
        
        payload = {
            "parent": {"database_id": NOTION_DB_ID},
            "properties": {
                "Sector": {"title": [{"text": {"content": sector_name}}]},
                "Scan Date": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
                "Bullish Score": {"number": data["bullish_score"]},
                "Minervini %": {"number": data["minervini_pct"]},
                "Qullamaggie %": {"number": data["qullamaggie_pct"]},
                "Volume Surge %": {"number": data["surge_pct"]},
                "Avg ADR %": {"number": data["avg_adr"]},
                "Stocks Scanned": {"number": data["total_stocks"]},
                "Sentiment": {"select": {"name": sentiment}},
            }
        }
        
        resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
        if resp.status_code == 200:
            print(f"  ✓ Notion updated: {sector_name}")
        else:
            print(f"  ✗ Notion error for {sector_name}: {resp.text[:100]}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    scan_data = scan_all_sectors()
    update_notion(scan_data)
    print("\n🎯 All done! Open sector_heatmap.html to view the dashboard.")
