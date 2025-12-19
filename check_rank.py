import json
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}
VENDOR_KEYWORDS = ["bt-miners", "bt miners", "bt-miners.com"]

print("=== Rank watch started ===", flush=True)

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

urls = config["urls"]
top_n = config.get("top_n", 3)

def norm(s): return (s or "").lower().strip()

alerts = []

for url in urls:
    print(f"\nChecking: {url}", flush=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        print(f"HTTP: {r.status_code}", flush=True)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ REQUEST ERROR: {e}", flush=True)
        alerts.append((url, "REQUEST ERROR", []))
        continue

    soup = BeautifulSoup(r.text, "html.parser")

    # Heuristic: vendors often appear as links to /vendors/ or in a table.
    vendor_names = []
    for a in soup.select('a[href*="/vendors/"]'):
        name = a.get_text(" ", strip=True)
        if name and name not in vendor_names:
            vendor_names.append(name)

    if not vendor_names:
        # fallback: table first column
        for tr in soup.select("table tbody tr"):
            tds = tr.find_all("td")
            if tds:
                name = tds[0].get_text(" ", strip=True)
                if name and name not in vendor_names:
                    vendor_names.append(name)

    top3 = vendor_names[:3]
    bt_rank = None
    for i, v in enumerate(vendor_names, 1):
        if any(k in norm(v) for k in VENDOR_KEYWORDS):
            bt_rank = i
            break

    if bt_rank is None:
        print(f"❌ BT-MINERS: MISSING | Top3: {top3}", flush=True)
        alerts.append((url, "MISSING", top3))
    elif bt_rank > top_n:
        print(f"❌ BT-MINERS rank #{bt_rank} | Top3: {top3}", flush=True)
        alerts.append((url, f"#{bt_rank}", top3))
    else:
        print(f"✅ BT-MINERS rank #{bt_rank} | Top3: {top3}", flush=True)

print("\n=== ALERT SUMMARY ===", flush=True)
if not alerts:
    print("🎉 All URLs are within Top 3", flush=True)
else:
    for url, reason, top3 in alerts:
        print(f"ALERT: {url} -> {reason} | Top3: {top3}", flush=True)
