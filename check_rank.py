import json
import csv
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}
VENDOR_KEYWORDS = ["bt-miners", "bt miners", "bt-miners.com"]

def norm(s): 
    return (s or "").lower().strip()

def guess_model_from_url(url: str) -> str:
    # best-effort: last slug
    slug = url.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").upper()

print("=== Rank watch started ===", flush=True)

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

urls = config["urls"]
top_n = int(config.get("top_n", 3))

rows_out = []
alerts = []

for url in urls:
    model = guess_model_from_url(url)
    bt_rank = "missing"
    top3 = []
    status = "ALERT"

    print(f"\nChecking: {url}", flush=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        print(f"HTTP: {r.status_code}", flush=True)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ REQUEST ERROR: {e}", flush=True)
        alerts.append((model, url, "REQUEST ERROR", top3))
        rows_out.append([model, url, "request_error", "", "ALERT"])
        continue

    soup = BeautifulSoup(r.text, "html.parser")

    # 1) Primary: vendor profile links
    vendor_names = []
    for a in soup.select('a[href*="/vendors/"]'):
        name = a.get_text(" ", strip=True)
        if name and name not in vendor_names:
            vendor_names.append(name)

    # 2) Fallback: table first column
    if not vendor_names:
        for tr in soup.select("table tbody tr"):
            tds = tr.find_all("td")
            if tds:
                name = tds[0].get_text(" ", strip=True)
                if name and name not in vendor_names:
                    vendor_names.append(name)

    top3 = vendor_names[:3]

    # Find BT-Miners rank
    found = None
    for i, v in enumerate(vendor_names, 1):
        if any(k in norm(v) for k in VENDOR_KEYWORDS):
            found = i
            break

    if found is None:
        bt_rank = "missing"
        status = "ALERT"
        print(f"❌ BT-MINERS: MISSING | Top3: {top3}", flush=True)
        alerts.append((model, url, "missing", top3))
    else:
        bt_rank = f"#{found}"
        if found <= top_n:
            status = "OK"
            print(f"✅ BT-MINERS rank {bt_rank} | Top3: {top3}", flush=True)
        else:
            status = "ALERT"
            print(f"❌ BT-MINERS rank {bt_rank} | Top3: {top3}", flush=True)
            alerts.append((model, url, bt_rank, top3))

    rows_out.append([model, url, bt_rank, " / ".join(top3), status])

# Print ALERT summary
print("\n=== ALERT SUMMARY ===", flush=True)
if not alerts:
    print("🎉 All URLs are within Top 3", flush=True)
else:
    for model, url, reason, top3 in alerts:
        print(f"ALERT: {model} | {reason} | {url} | Top3: {top3}", flush=True)

# Print Markdown table
print("\n=== FULL TABLE (Markdown) ===", flush=True)
print("| Model | URL | BT Rank | Top 3 Vendors | Status |")
print("|---|---|---:|---|---|")
for model, url, bt_rank, top3s, status in rows_out:
    print(f"| {model} | {url} | {bt_rank} | {top3s} | {status} |")

# Write CSV artifact
csv_path = "rank_report.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Model", "URL", "BT Rank", "Top 3 Vendors", "Status"])
    w.writerows(rows_out)

print(f"\nCSV saved: {csv_path}", flush=True)
