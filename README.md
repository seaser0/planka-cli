# Planka CLI v4.3

Advanced CLI for Planka with DevOps-friendly features, powered by `uv`.

## Installation & Setup

1. Installiere [uv](https://github.com/astral-sh/uv):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Abhängigkeiten installieren:
   ```bash
   cd ~/.openclaw/scripts/planka-cli
   uv sync
   ```

3. `.env` Datei erstellen:
   ```
   PLANKA_URL=https://planka.nevit.ch
   PLANKA_USERNAME=optimusprime
   PLANKA_PASSWORD=secret
   ```

   **Alternativ** — Password aus einem Secret-Store laden statt im Klartext:
   ```bash
   # Aus Datei:
   PLANKA_PASSWORD_FILE=~/.config/planka/password

   # Aus shell command (z.B. OpenBao, 1Password, pass):
   PLANKA_PASSWORD_CMD=curl -fsS -H "X-Vault-Token: $BAO_TOKEN" "https://openbao.example.com/v1/secret/data/planka/admin-password" | jq -r '.data.data.password'
   PLANKA_PASSWORD_CMD=op read "op://Vault/Planka/password"
   PLANKA_PASSWORD_CMD=pass show planka/admin
   ```
   Priorität: `PLANKA_PASSWORD` > `PLANKA_PASSWORD_FILE` > `PLANKA_PASSWORD_CMD`.

4. Wrapper-Skript (einmalig):
   ```bash
   # ~/.openclaw/scripts/planka ist der globale Wrapper
   # Aufruf einfach mit:
   ~/.openclaw/scripts/planka <command>
   ```

## Commands

### Auth
```bash
planka login
```

### Boards
```bash
planka boards list
planka boards create "Mein Board"
```

### Lists
```bash
planka lists list Autobots
planka lists create Autobots "Sprint Backlog"
```

### Cards
```bash
# Karten anzeigen
planka cards list Autobots Backlog

# Neue Karte erstellen
planka cards create Autobots Backlog "Titel der Karte" --type story
planka cards create Autobots Backlog "Titel" --type project

# Karte bearbeiten
planka cards update Autobots "Kartentitel" --name "Neuer Titel"
planka cards update Autobots "Kartentitel" --description "Beschreibung in Markdown"
planka cards update Autobots "Kartentitel" --due "2026-04-01T00:00:00Z"

# Karte verschieben
planka cards move "Kartentitel" Autobots Progress
planka cards move "Kartentitel" Autobots Done

# Karte löschen
planka cards delete Autobots "Kartentitel"
```

### Tags / Labels
```bash
# Labels eines Boards anzeigen
planka labels list Autobots

# Neues Label erstellen
planka labels create Autobots "Starscream"
planka labels create Autobots "Starscream" --color berry-red

# Tag einer Karte zuweisen
planka cards tag Autobots "Kartentitel" "Megatron"
planka cards tag Autobots "Logitech" "Bumblebee"

# Tag von einer Karte entfernen
planka cards untag Autobots "Kartentitel" "Megatron"
planka cards untag Autobots "Logitech" "Bumblebee"
```

### Comments (v4.3+)
```bash
# Comment posten — Text als Argument, aus Datei oder via stdin
planka cards comment Autobots "Kartentitel" "Quick note"
planka cards comment Autobots "Kartentitel" --file decision.md
echo "from pipe" | planka cards comment Autobots "Kartentitel"

# Comments lesen
planka cards comments Autobots "Kartentitel"
planka cards comments Autobots "Kartentitel" --output json
```

### Disambiguation (v4.3+)
Bei mehreren partial-Match-Treffern erroret die CLI mit der Kandidatenliste statt silent
die erste Karte zu picken:
```bash
$ planka cards untag Autobots "obs-trace" needs-decision
Ambiguous match: 2 cards found for 'obs-trace'
  [1775812155560429231] obs-trace-recorded Azure Mapping  (Done)
  [1776930919865649038] obs-trace-recorded Unit-Mismatch  (Backlog)
Refine the substring, pass the full id, or use --in <list> to scope.

# Mit --in scoping:
planka cards untag Autobots "obs-trace" needs-decision --in Backlog
```

### Bulk operations (v4.3+)
Alle write-Operationen auf Karten (`move`, `delete`, `tag`, `untag`) lesen mit `--stdin`
eine Liste von Card-Refs. Im --stdin Modus wird der Card-Positional weggelassen und
Label bzw. Ziel-Liste müssen als Flag (`--label` / `--to`) übergeben werden:
```bash
# Alle needs-decision Karten in Backlog untaggen
planka cards list Autobots Backlog --output json --jq '[.[].id]' \
  | planka cards untag Autobots --label needs-decision --stdin

# Bulk move aus Datei (eine ID pro Zeile)
cat sprint-done.txt | planka cards move Autobots --to Done --stdin

# Bulk delete von test cards
echo -e "test-card-1\ntest-card-2" | planka cards delete Autobots --stdin
```
Stdin akzeptiert: eine ID/Name pro Zeile, JSON-Array `["id1","id2"]`, oder Array of
Objects mit `.id` Feld.

## Output-Optionen

Alle Commands unterstützen:
```bash
--output json     # JSON Output
--output yaml     # YAML Output
--output table    # Tabellen-Ansicht (Standard)
--jq '.[].name'  # jq-Filter auf JSON
```

## Features
- ✅ Automatische Token-Erneuerung bei Ablauf
- ✅ Partial Name-Match für Cards & Labels (z.B. `"Logit"` findet `"Logitech Aktie..."`)
- ✅ Robuste Isolation via `uv` — keine globalen Python-Pakete verschmutzt
- ✅ JSON/YAML/Table Output mit jq-Support
- ✅ Label-Zuweisung per Tag-Name (kein ID-Lookup nötig)
- ✅ Duplikat-Schutz bei Tag-Zuweisung

## Verfügbare Labels (Autobots Board)
| Label        | Farbe          |
|--------------|----------------|
| Mischa       | lagoon-blue    |
| Bumblebee    | egg-yellow     |
| Megatron     | berry-red      |
| Ultra Magnus | midnight-blue  |
| Alpha Trion  | sweet-lilac    |
| Teletraan I  | modern-green   |
| Jetfire      | morning-sky    |
| Ratchet      | pink-tulip     |
| Wheeljack    | pumpkin-orange |
| Perceptor    | antique-blue   |
