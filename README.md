# Planka CLI v4.2

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
