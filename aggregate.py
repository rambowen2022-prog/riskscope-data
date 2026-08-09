"""
RiskScope — automatisierte Duerre-Index-Aktualisierung (vereinfachte Version)
================================================================================

Nutzt nur die Kreis-MITTELPUNKTE (data/kreise_zentren.json, ~30 KB) statt der
vollen Grenzlinien (11+ MB) -- deutlich leichter hochzuladen und zu pflegen,
gleiche Idee wie beim Hochwasser-Layer der Website (Punktabfrage statt
Flaechenverschneidung).

Ablauf:
  1. Aktuelle SM_Lall_daily_n14.nc vom UFZ-Duerremonitor herunterladen
  2. Fuer jeden Kreis-Mittelpunkt den naechstgelegenen Rasterwert auslesen
  3. Ergebnis als data/kreis_werte.json schreiben

Installation:
    pip install requests rioxarray xarray netCDF4 --break-system-packages
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
import rioxarray  # noqa: F401
import xarray as xr

UFZ_URL = "https://files.ufz.de/~drought/SM_Lall_daily_n14.nc"
ZENTREN_PATH = Path(__file__).parent.parent / "data" / "kreise_zentren.json"
OUT_PATH = Path(__file__).parent.parent / "data" / "kreis_werte.json"
TMP_NC = Path("/tmp/smi_latest.nc")


def download_ufz_data():
    print(f"Lade UFZ-Daten von {UFZ_URL} ...")
    resp = requests.get(UFZ_URL, timeout=120)
    resp.raise_for_status()
    TMP_NC.write_bytes(resp.content)
    print(f"Heruntergeladen: {len(resp.content) / 1024:.0f} KB")


def compute():
    zentren = json.loads(ZENTREN_PATH.read_text(encoding="utf-8"))

    ds = xr.open_dataset(TMP_NC)
    latest = ds["SMI"].isel(time=-1)
    latest_date = str(ds["time"].isel(time=-1).values)[:10]
    print("Stichtag der Daten:", latest_date)

    latest = latest.rename({"easting": "x", "northing": "y"})
    latest = latest.rio.write_crs("EPSG:31468", inplace=False)

    values = {}
    for rs, info in zentren.items():
        try:
            point = latest.sel(x=info["x"], y=info["y"], method="nearest")
            smi = float(point.values)
        except Exception:
            continue
        if np.isnan(smi):
            continue
        duerre_index = round((1 - smi) * 100)
        values[rs] = {"duerre_index": duerre_index, "smi": round(smi, 3)}

    out = {
        "stichtag": latest_date,
        "aktualisiert": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "werte": values,
    }

    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"{len(values)} Kreise geschrieben -> {OUT_PATH}")


def main():
    if not ZENTREN_PATH.exists():
        print(f"FEHLER: {ZENTREN_PATH} fehlt im Repo.")
        return
    download_ufz_data()
    compute()


if __name__ == "__main__":
    main()
