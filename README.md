# NSE Sector Pulse — Minervini × Qullamaggie Scanner

Automated weekly scanner for NSE India stocks. Runs every **Sunday 9PM EST** via GitHub Actions.
Generates an interactive sector heatmap showing which sectors are bullish or bearish.

---

## 🗂️ Files

| File | Purpose |
|---|---|
| `scanner.py` | Main scanner — Minervini SEPA + Qullamaggie VCP criteria |
| `generate_heatmap.py` | Injects live JSON data into the HTML template |
| `sector_heatmap.html` | Interactive visual dashboard (open in browser) |
| `sector_heatmap_data.json` | Raw scan output (auto-generated) |
| `.github/workflows/weekly_scan.yml` | GitHub Actions automation |
| `requirements.txt` | Python dependencies |

---

## ⚡ Quick Start (Local)

```bash
# 1. Clone your repo
git clone https://github.com/YOUR_USERNAME/nse-pulse.git
cd nse-pulse

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the scanner
python scanner.py

# 4. Generate the heatmap
python generate_heatmap.py

# 5. Open the dashboard
open sector_heatmap.html   # macOS
# or just double-click the file in Windows/Linux
```

---

## 🤖 GitHub Actions Setup (Automated Every Sunday 9PM EST)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/nse-pulse.git
git push -u origin main
```

### Step 2 — Set up Notion Integration (Optional)

#### Create a Notion Database with these properties:
| Property | Type |
|---|---|
| Sector | Title |
| Scan Date | Date |
| Bullish Score | Number |
| Minervini % | Number |
| Qullamaggie % | Number |
| Volume Surge % | Number |
| Avg ADR % | Number |
| Stocks Scanned | Number |
| Sentiment | Select |

#### Get your Notion credentials:
1. Go to https://www.notion.so/my-integrations → Create integration → Copy **Internal Integration Token**
2. Share your Notion database with the integration
3. Copy the **Database ID** from the database URL:
   `https://notion.so/workspace/DATABASE_ID?v=...`

### Step 3 — Add GitHub Secrets
Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|---|---|
| `NOTION_TOKEN` | Your Notion integration token (`secret_...`) |
| `NOTION_DB_ID` | Your Notion database ID (32-char UUID) |

### Step 4 — Enable Actions
Go to your repo → **Actions tab** → Enable workflows if prompted.

The scan will now run automatically every **Sunday at 9PM EST (Monday 2AM UTC)**.

You can also trigger it manually: Actions → "NSE Weekly Sector Scan" → "Run workflow"

---

## 📊 Screening Criteria

### Minervini SEPA (all 6 must pass)
- ✅ Price > 50 SMA > 150 SMA > 200 SMA (trend structure)
- ✅ 200 SMA trending up vs 1 month ago
- ✅ Price within 25% of 52-week high
- ✅ Price at least 30% above 52-week low

### Qullamaggie VCP (4+ of 6 must pass)
- ✅ ADR% > 3% (volatile, momentum stock)
- ✅ Volatility contraction: recent range < 60% of prior range
- ✅ Volume dry-up before potential breakout
- ✅ Price within 15% of 52-week high (setup zone)
- ✅ Higher volume on up days vs down days
- ✅ RS: stock up 10%+ in last 3 months

### Volume Surge Indicator
- 🔥 Last week avg volume > 1.5× the 50-day average
- Combined with positive price action = Bullish Surge

### Bullish Score (0–100)
```
Score = (Minervini % × 0.40) + (Qullamaggie % × 0.40) + (Vol Surge % × 0.20)
```

---

## 🎨 Reading the Heatmap

| Score | Signal | Color |
|---|---|---|
| 65–100 | 🟢 BULLISH | Green |
| 40–64 | 🟡 NEUTRAL | Dark/Muted |
| 0–39 | 🔴 BEARISH | Red |

Click any sector card to see the stock-level breakdown with individual scores.

Use the **tabs** at the top to switch between Composite, Minervini-only, Qullamaggie-only, or Volume Surge views.

---

## 🛠️ Customization

**Add more stocks:** Edit the `NSE_SECTORS` dictionary in `scanner.py`

**Change criteria thresholds:** Modify constants inside `check_minervini()` and `check_qullamaggie()`

**Change schedule:** Edit the cron in `.github/workflows/weekly_scan.yml`
- Current: `0 2 * * 1` = Monday 2AM UTC = Sunday 9PM EST
- Use https://crontab.guru to build custom schedules

---

## ⚠️ Notes

- Uses `yfinance` for data — free, no API key needed
- Data has a ~15 min delay for live prices (fine for weekly scans)
- GitHub Actions free tier gives 2,000 minutes/month — this scan uses ~15 min/week
- First run may take longer as yfinance caches data
