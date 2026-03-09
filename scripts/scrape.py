"""
3GPP 시리즈별 스펙 정보 스크래퍼
https://www.3gpp.org/DynaReport/{N}-series.htm
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SERIES = [21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38]

SERIES_DESC = {
    21: "Vocabulary & terminology",
    22: "Service aspects (Stage 1)",
    23: "Technical realization (Stage 2)",
    24: "Signalling protocols – UE to network (Stage 3)",
    25: "Radio Access Network (UMTS/WCDMA)",
    26: "Codecs",
    27: "Data",
    28: "Telecom management (OAM)",
    29: "Signalling protocols (MAP & related)",
    31: "SIM / UICC",
    32: "OAM&P & Charging",
    33: "Security aspects",
    34: "UE & SIM test specifications",
    35: "Security algorithms",
    36: "LTE (E-UTRA)",
    37: "Multiple Radio Access Technology",
    38: "NR (5G New Radio)",
}

BASE_URL = "https://www.3gpp.org/DynaReport/{series}-series.htm"
DATA_DIR = Path(__file__).parent.parent / "docs" / "data"
SLEEP_SEC = 2  # 서버 부하 방지


def scrape_series(series: int) -> list[dict]:
    url = BASE_URL.format(series=series)
    print(f"[{series}] Fetching {url}")

    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", id="a3dyntab") or soup.find("table", class_="dsptab")
    if not table:
        print(f"[{series}] Table not found")
        return []

    specs = []
    for row in table.find("tbody").find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        spec_cell = cells[0]
        title_cell = cells[1]
        notes_cell = cells[2] if len(cells) > 2 else None

        # spec 번호 파싱: "TS 38.101" or "TR 38.716-01-01"
        spec_text = spec_cell.get_text(separator=" ", strip=True)
        match = re.match(r"^(TS|TR)\s+([\d.\-]+)", spec_text)
        if not match:
            continue

        spec_type = match.group(1)   # TS or TR
        spec_no = match.group(2)     # 38.101 or 38.716-01-01

        # 링크
        link_tag = spec_cell.find("a", href=True)
        link = f"https://www.3gpp.org{link_tag['href']}" if link_tag else None

        # 제목
        title = title_cell.get_text(strip=True)

        # WITHDRAWN 여부
        notes = notes_cell.get_text(strip=True) if notes_cell else ""
        withdrawn = "WITHDRAWN" in notes.upper()

        specs.append({
            "type": spec_type,
            "no": spec_no,
            "title": title,
            "withdrawn": withdrawn,
            "link": link,
        })

    print(f"[{series}] {len(specs)} specs found")
    return specs


def main():
    DATA_DIR.mkdir(exist_ok=True)
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = []

    for series in SERIES:
        try:
            specs = scrape_series(series)
            out_path = DATA_DIR / f"series-{series}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(specs, f, ensure_ascii=False, indent=2)

            total = len(specs)
            ts_count = sum(1 for s in specs if s["type"] == "TS")
            tr_count = sum(1 for s in specs if s["type"] == "TR")
            withdrawn_count = sum(1 for s in specs if s["withdrawn"])

            summary.append({
                "series": series,
                "desc": SERIES_DESC.get(series, ""),
                "total": total,
                "ts": ts_count,
                "tr": tr_count,
                "withdrawn": withdrawn_count,
            })
        except Exception as e:
            print(f"[{series}] ERROR: {e}")
            summary.append({
                "series": series,
                "desc": SERIES_DESC.get(series, ""),
                "total": 0,
                "ts": 0,
                "tr": 0,
                "withdrawn": 0,
                "error": str(e),
            })

        time.sleep(SLEEP_SEC)

    meta = {"updated_at": updated_at, "series": summary}
    with open(DATA_DIR / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\nDone. updated_at={updated_at}")


if __name__ == "__main__":
    main()
