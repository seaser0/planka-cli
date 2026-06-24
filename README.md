# Planka CLI v4.5

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
# Karten anzeigen — jede Zeile trägt jetzt labels + description (v4.5+)
planka cards list Autobots Backlog
planka cards list Autobots Backlog -o json \
  --jq '[.[] | select(.labels[]?.name == "needs-decision") | {id, name}]'  # Label-Filter
planka cards list Autobots Backlog -o json --jq '.[] | {name, desc: .description}'

# Einzelne Karte voll auslesen (description, labels, members, dueDate)
planka cards get Autobots "Kartentitel"
planka cards get Autobots "Kartentitel" --output json          # description sauber, ohne Tabellen-Wrapping
planka cards get Autobots "Kartentitel" --jq '.[0].description' # nur die Beschreibung
planka cards get Autobots "Kartentitel" --in Backlog           # bei mehrdeutigem Namen auf Liste scopen

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

### Members (v4.5+)
```bash
# User-Liste (username -> userId auflösen)
planka users list
planka users list -o json --jq '.[] | select(.username=="seaser") | .id'

# User einer Karte zuweisen / entfernen — --user nimmt username, email oder userId
planka cards assign   Autobots "Kartentitel" --user seaser
planka cards unassign Autobots "Kartentitel" --user seaser
```
> Hinweis: Die Planka-Route ist `card-memberships/userId:<id>` (analog zum `card-labels`-Quirk);
> eine literale Membership-ID liefert 404.

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

### Attachments (v4.6+)
```bash
# Datei an Karte anhängen (--name optional, default = Dateiname)
planka cards attach Autobots "Kartentitel" ./report.pdf
planka cards attach Autobots "Kartentitel" ./logo.png --name "Branding.png"

# Attachments einer Karte auflisten
planka cards attachments Autobots "Kartentitel"
planka cards attachments Autobots "Kartentitel" -o json --jq '[.[].id]'

# Attachment herunterladen (per id oder name; --out optional, default = Attachment-Name)
planka cards download Autobots "Kartentitel" report.pdf
planka cards download Autobots "Kartentitel" 1804723501446203345 --out /tmp/r.pdf

# Attachment löschen (per id oder name)
planka cards detach Autobots "Kartentitel" report.pdf
```
> Hinweis: Upload braucht zwingend ein `name`-Formfeld (sonst `E_MISSING_OR_INVALID_PARAMS`).
> Downloads laufen über die `/attachments/*`-Route, die per `accessToken`-Cookie authentifiziert
> (nicht via Bearer-Header) — die CLI regelt das transparent.

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
- ✅ `cards get` — einzelne Karte voll auslesen inkl. description, labels & members (v4.4+)
- ✅ `cards list` trägt `labels` (strukturiert) + `description` → `--jq`-Label-Filter (v4.5+)
- ✅ `cards assign` / `cards unassign` / `users list` — Card-Member-Verwaltung (v4.5+)
- ✅ `cards attach` / `attachments` / `download` / `detach` — Datei-Anhänge (v4.6+)
- ✅ `--jq` folgt jq-CLI-Semantik (Single-Result unwrap) + Scalar/String-Output rendert sauber in der Tabelle (v4.6+)

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
