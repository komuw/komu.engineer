#!/usr/bin/env python3
"""
fetch_data.py
-------------
Reproducibly downloads the raw World Bank World Development Indicators (WDI)
series used in this folder and writes them to ./data/raw/<INDICATOR>.json,
exactly matching the files that build_dataset.py consumes.

Run:  python fetch_data.py
Deps: requests   (pip install requests)   -- standard library urllib fallback included.

NOTE ON ACCESS
--------------
api.worldbank.org sits behind Cloudflare. On most normal networks a plain
HTTPS GET works fine. In some sandboxed/proxied environments Cloudflare issues
a JavaScript "bot check" that a scripted client cannot pass, and the request
will hang or return an HTML challenge page instead of JSON. If that happens:
  * run this script from a normal machine/network, OR
  * open each URL below in a browser and save the JSON manually, OR
  * use the raw JSON already provided in ./data/raw/ (that is how the shipped
    copies were obtained).
"""
import json, os, sys, time

INDICATORS = [
    "NE.CON.PRVT.ZS",  # Household & NPISH final consumption expenditure (% of GDP)   -> C
    "NE.CON.GOVT.ZS",  # General government final consumption expenditure (% of GDP)  -> G
    "NE.GDI.TOTL.ZS",  # Gross capital formation (% of GDP)                           -> I
    "NE.GDI.FTOT.ZS",  # Gross fixed capital formation (% of GDP)
    "NE.EXP.GNFS.ZS",  # Exports of goods and services (% of GDP)                     -> X
    "NE.IMP.GNFS.ZS",  # Imports of goods and services (% of GDP)                     -> M
    "NE.RSB.GNFS.ZS",  # External balance on goods and services (% of GDP)            -> X-M
    "NY.GDP.MKTP.CD",  # GDP (current US$)
    "NY.GDP.MKTP.CN",  # GDP (current LCU = Kenyan shillings)
]

BASE = "https://api.worldbank.org/v2/country/KE/indicator/{code}?format=json&per_page=300"
OUT  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")


def get(url):
    """GET a URL, preferring requests, falling back to urllib."""
    try:
        import requests
        r = requests.get(url, timeout=60,
                          headers={"User-Agent": "Mozilla/5.0 (data-fetch)"})
        r.raise_for_status()
        return r.json()
    except ImportError:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (data-fetch)"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))


def main():
    os.makedirs(OUT, exist_ok=True)
    for code in INDICATORS:
        url = BASE.format(code=code)
        print("fetching", code, "...", end=" ", flush=True)
        try:
            payload = get(url)
        except Exception as e:
            print("FAILED:", e); continue
        if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
            print("unexpected response (Cloudflare challenge?) - skipped"); continue
        with open(os.path.join(OUT, code + ".json"), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        n = len([r for r in payload[1] if r["value"] is not None])
        print(f"ok ({n} observations)")
        time.sleep(0.5)  # be polite to the API
    print("done. now run:  python build_dataset.py")


if __name__ == "__main__":
    main()
