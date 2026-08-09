# RiskScope — automatisierte Dürre-Datenaktualisierung

Dieses Repo berechnet täglich den Dürre-Index für alle 431 deutschen
Landkreise neu und veröffentlicht das Ergebnis als JSON, das die
riskscope.de-Website live einliest.

## Einmalige Einrichtung

1. Dieses Repo auf GitHub anlegen (z.B. `riskscope-data`), diesen Ordner
   hochladen (`data/`, `scripts/`, `.github/`).
2. Unter Settings → Actions → General sicherstellen, dass "Read and write
   permissions" für den GITHUB_TOKEN aktiviert ist (nötig zum Commit).
3. Unter dem Reiter "Actions" den Workflow "Dürre-Daten aktualisieren"
   einmal manuell über "Run workflow" auslösen, um zu prüfen, dass er
   durchläuft.
4. Danach läuft er automatisch jeden Tag um 06:00 UTC.

## Ergebnis

`data/kreis_werte.json` wird bei jedem Lauf aktualisiert (falls sich die
Werte geändert haben) und ist danach über
`https://raw.githubusercontent.com/<dein-github-name>/<repo-name>/main/data/kreis_werte.json`
abrufbar. Diese URL trägst du in main.ts bei RiskScope ein (siehe
Kommentar dort).
