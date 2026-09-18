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
    """Laedt die UFZ-Datei und gibt deren HTTP-Last-Modified zurueck (Zeitpunkt der letzten Aenderung DER QUELLE)."""
    print(f"Lade UFZ-Daten von {UFZ_URL} ...")
    resp = requests.get(UFZ_URL, timeout=120)
    resp.raise_for_status()
    TMP_NC.write_bytes(resp.content)
    last_modified = resp.headers.get("Last-Modified")
    print(f"Heruntergeladen: {len(resp.content) / 1024:.0f} KB | Last-Modified der Quelle: {last_modified}")
    return last_modified


def compute(quelle_last_modified):
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

    # Veraltete Quelle sichtbar machen (GitHub zeigt ::warning:: als Hinweis am Lauf an)
    alter_tage = (datetime.now(timezone.utc).date() - datetime.strptime(latest_date, "%Y-%m-%d").date()).days
    if alter_tage > 3:
        print(f"::warning::UFZ-Daten veraltet: Stichtag {latest_date} ist {alter_tage} Tage alt "
              f"(Quelle zuletzt geaendert: {quelle_last_modified}).")

    # Nur schreiben, wenn sich Daten ODER die Quelle geaendert haben. Sonst bliebe "aktualisiert"
    # taeglich frisch, obwohl die UFZ-Quelle stillsteht -- das taeuscht einen aktuellen Stand vor.
    if OUT_PATH.exists():
        try:
            alt = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            alt = {}
        if (alt.get("stichtag") == latest_date
                and alt.get("werte") == values
                and alt.get("quelle_last_modified") == quelle_last_modified):
            print(f"Quelle unveraendert (Stichtag {latest_date}, Last-Modified {quelle_last_modified}) "
                  f"-- Datei bleibt unveraendert, kein Commit.")
            return

    out = {
        "stichtag": latest_date,
        "aktualisiert": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "quelle_last_modified": quelle_last_modified,
        "werte": values,
    }

    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"{len(values)} Kreise geschrieben -> {OUT_PATH}")


def main():
    if not ZENTREN_PATH.exists():
        print(f"FEHLER: {ZENTREN_PATH} fehlt im Repo.")
        return
    last_modified = download_ufz_data()
    compute(last_modified)


if __name__ == "__main__":
    main()
