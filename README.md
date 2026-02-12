# NEXUS: Mikroklima-integriertes Fledermaus-Monitoring

**Status: ⚠️ Alpha / Pre-Validation**

NEXUS ist ein Open-Source-Umweltsensorik-System, das präzise Mikro-Klima-Daten (Temperatur, Luftfeuchtigkeit, Wind, Luftdruck, atmosphärische Dämpfung) mit Fledermaus-Akustikdaten korreliert.

---

## 🦇 Das Problem

**Aktuelle WKA-Gutachten (Windkraftanlagen):**

> *"Die Begehung fand bei ca. 10°C, leichtem Südwest-Wind und kaum Wolken statt."*

Diese ungenauen Angaben bilden die Grundlage für Entscheidungen über:
- Abschaltzeiten von Windkraftanlagen
- Fledermausschutz-Maßnahmen
- Monitoring-Strategien

**Das ist zu ungenau für Entscheidungen über Fledermaus-Leben und -Tod.**

---

## ✨ Die Lösung

**NEXUS kombiniert drei Komponenten:**

| Komponente | Funktion | Quelle |
|------------|----------|--------|
| **TeensyBat** | Full-Spectrum Ultraschall-Recorder (bis 150 kHz) | [teensybat.com](https://www.teensybat.com/) |
| **BatDetect2** | CNN-basierte automatische Arterkennung | [Mac Aodha et al.](https://github.com/macaodha/batdetect2) |
| **NEXUS Sensorik** | Präzise Mikro-Klima-Daten + ISO 9613-1 Dämpfung | **Eigene Entwicklung** |

---

## 📊 Beispiel-Output: Statt "ca. 10°C" → Wissenschaftliche Präzision

**Traditionelles Gutachten:**
```
Zeit: ca. 21:30 Uhr
Temperatur: ca. 10°C
Wind: leichter Südwest-Wind
Wolken: kaum
Art: Pipistrellus pipistrellus (manuell identifiziert)
```

**NEXUS-Protokoll:**
```
Timestamp:    2026-03-15 21:34:15 UTC (GPS-synchronisiert)
Temperatur:   15.84°C (±0.1°C, BME680)
Luftfeuchte:  64.39% rH
Taupunkt:     9.2°C
Luftdruck:    1013.2 hPa
Wind:         2.1 m/s aus 217° (Böen: 3.8 m/s)
Bewölkung:    3/8 Oktas
Position:     51.718534, 8.754321 (GPS AIR530, 12 Satelliten)

Art:          Pipistrellus pipistrellus (BatDetect2, Konfidenz: 0.94)

Atmosphärische Dämpfung (ISO 9613-1):
- 20 kHz:  0.12 dB/m
- 40 kHz:  0.34 dB/m
- 55 kHz:  0.58 dB/m (Hauptfrequenz P. pipistrellus)
- 80 kHz:  1.02 dB/m
- 110 kHz: 1.87 dB/m
```

**→ Wissenschaftlich reproduzierbar, GPS-verifiziert, atmosphärisch korrigiert.**

---

## 🔧 Hardware

### Kern-System (NEXUS v4.3.1)
- **Mikrocontroller:** Seeed XIAO ESP32-S3 Sense
- **Umweltsensorik:** Bosch BME680 (Temperatur, Luftfeuchtigkeit, Luftdruck, VOC)
- **GPS:** AIR530 (Position, Höhe, GPS-Zeit-Synchronisation)
- **Wind/Regen:** Sparkfun Weather Meters (Anemometer, Regenmesser)
- **Display:** OLED 128x64 (SSD1306, I2C)
- **Speicher:** SD-Karte (CSV-Logging)
- **Bedienung:** PCF8574 Expander + Rotary Encoder

### Integration
- **Akustik:** TeensyBat (extern, Ultraschall-Aufnahme)
- **Analyse:** BatDetect2 (extern, CNN-basierte Arterkennung)

### Kosten
- **NEXUS Hardware:** ca. 80–150€ (DIY)
- **TeensyBat:** ca. 150€
- **BatDetect2:** kostenlos (Open Source)

**Gesamt: ~250€** (vs. kommerzielle Systeme: 3.000–10.000€)

```mermaid
graph TD
    subgraph "Datenerfassung (Feld)"
        A[NEXUS Sensorik] -->|Umweltdaten CSV| B(Data Storage)
        C[TeensyBat] -->|Audio WAV| B
    end

    subgraph "Phase 1: Vorverarbeitung & KI"
        B --> D[wav_teiler: Segmentierung]
        D --> E[BatDetect2: KI-Klassifizierung]
    end

    subgraph "Phase 2: Validierung & Zeit-Sync"
        E --> F[batch-validator: Frequenzprüfung]
        F --> G[bat_autostart: Zeitstempel & Astro-Daten]
    end

    subgraph "Phase 3: NEXUS Integration"
        G --> H[nexus_guild_analyzer: ISO 9613-1 Reichweite]
        B --> H
        H --> I[final_3way_merge: Umwelt + Akustik + KI]
    end

    subgraph "Phase 4: Visualisierung"
        I --> J[Activity & Pareto Charts]
        I --> K[Spektrogramme mit Overlays]
        I --> L[KML-Export: Google Earth]
    end

    style A fill:#f96,stroke:#333
    style C fill:#f96,stroke:#333
    style L fill:#9f9,stroke:#333

---

## 💻 Software Features

- ✅ **WiFi Access Point** `NEXUS_Base` mit Live-Web-Interface (192.168.4.1)
- ✅ **ISO 9613-1 Berechnung** der atmosphärischen Dämpfung für Ultraschall (20–110 kHz)
- ✅ **GPS-Zeit-Synchronisation** (Präzision: ±1 Sekunde)
- ✅ **CSV-Logging** auf SD-Karte (8-Sekunden-Intervall)
- ✅ **AJAX-basiertes Dashboard** (keine Seiten-Reloads)
- ✅ **Stationär & Mobil-Modi** (für Transekt-Begehungen oder feste Standorte)

---

## 📁 Repository-Struktur

```
NEXUS_DIY_Sensorik/
├── README.md                  # Diese Datei
├── LICENSE                    # CC BY-NC 4.0
├── software/
│   └── main.cpp               # NEXUS v4.3.1 Core-Code
├── hardware/
│   ├── parts-list.md          # Komponenten & Bezugsquellen
│   ├── wiring-diagram.png     # Verkabelung (coming soon)
│   └── assembly-guide.md      # Aufbau-Anleitung (coming soon)
├── docs/
│   ├── methodology.md         # Wissenschaftliche Methodik
│   ├── iso-9613-1.md          # Dämpfungskoeffizient-Erklärung
│   └── validation-plan.md     # Feldtest-Protokoll (Frühjahr 2026)
└── data/
    └── example-dataset/       # Beispiel-Daten (coming soon)
```

---

## 🚀 Entwicklungsstatus

- [x] **v1.0** - Grundkonzept & erste Sensortests
- [x] **v2.0** - BME680 Integration
- [x] **v3.0** - GPS-Synchronisation
- [x] **v4.0** - Wind & Regen Sensoren
- [x] **v4.3.1** - ISO 9613-1 Dämpfungskoeffizient, WiFi-Interface
- [ ] **v5.0** - Feldvalidierung (geplant: März–Mai 2026, Raum Paderborn)
- [ ] **v6.0** - TeensyBat-Integration (Zeitstempel-Sync)
- [ ] **v7.0** - BatDetect2-Pipeline (automatische Analyse)
- [ ] **v8.0** - Peer-Review-Paper (Methodology & Validation)

---

## 🎯 Warum Open Source VOR der Validierung?

> **Die Eisvogel-Geschichte (2019, Paderborn):**
>
> Als ein Baum an der Dielenpader entwurzelt wurde, verloren Eisvögel ihren Ansitzast. Ich entwickelte eine einfache Lösung: alte Pappelästin den Boden rammen.
> 
> Nach 3 Monaten Wartezeit auf behördliche Genehmigung rammte ich die Äste ein.
> 
> **30 Minuten später saß der erste Eisvogel drauf und betäubte seinen Fisch.**
> 
> Kurz darauf kopierte die Stadt Paderborn die Idee, installierte eigene Ansitzäste und verkündete stolz, "die Stadt mache nun etwas für die Eisvögel".
> 
> **Ich hatte keinen Beweis, dass es meine Idee war.**
> 
> ---
> 
> **Diesmal dokumentiere ich von Anfang an.**
> 
> Diesmal kann niemand sagen: *"Das haben wir schon immer so gemacht."*
> 
> — Jochen Roth, Februar 2026

**Open Science bedeutet:**
- Transparente Entwicklung
- Reproduzierbare Methodik
- Prioritätsnachweis durch GitHub-Commits
- Community-basierte Verbesserung

---

## 📖 Wissenschaftliche Grundlage

### ISO 9613-1: Dämpfung von Schall bei der Ausbreitung im Freien

NEXUS implementiert die ISO 9613-1 Norm zur Berechnung der atmosphärischen Dämpfung von Schall. Dies ist kritisch für die Fledermaus-Bioakustik, da:

* **Ultraschallrufe (20–110 kHz)** extrem stark gedämpft werden.
* **Temperatur, Luftfeuchtigkeit und Luftdruck** die Dämpfung exponentiell beeinflussen.
* **Detektionsreichweiten** artspezifisch variieren und ohne Korrektur nicht vergleichbar sind.

👉 **[Hier findest du die ausführliche wissenschaftliche Erklärung zur ISO 9613-1 im NEXUS-Projekt](docs/iso-9613-1.md)**

**Praxis-Beispiel:**
Ein Ruf von *Pipistrellus pipistrellus* (55 kHz) wird bei 15°C und 60% rH um ca. **0,6 dB/m** gedämpft. Nach nur 10 Metern bedeutet das bereits einen **Verlust von 6 dB** – das entspricht einer **Halbierung der Amplitude**.

Ohne Kenntnis der exakten atmosphärischen Bedingungen vor Ort ist eine präzise Reichweiten-Kalibrierung der Aufnahmen unmöglich.

---

## 🌍 Anwendungsgebiete

1. **WKA-Gutachten** - Präzise Dokumentation der Messbedingungen
2. **Populationsmonitoring** - Langzeit-Datenreihen mit Umweltkontext
3. **Verhaltensforschung** - Korrelation von Aktivität & Mikroklima
4. **Citizen Science** - Kosteneffizientes Monitoring für Naturschutzgruppen
5. **Methodenvalidierung** - Vergleich verschiedener Erfassungssysteme

---

## 🤝 Beitragen

NEXUS ist ein **Work in Progress**. Feedback, Verbesserungsvorschläge und Beiträge sind willkommen!

**Besonders gesucht:**
- Feldtest-Partner (Frühjahr 2026)
- Validierung der Alpha-Berechnung (Vergleich mit Referenzdaten)
- Hardware-Optimierungen (Wetterfestigkeit, Stromverbrauch)
- Software-Erweiterungen (automatische BatDetect2-Integration)

**Kontakt:**
- Blog: [paderbats.blogspot.com](https://paderbats.blogspot.com/)
- GitHub Issues: Fragen & Diskussionen

---

## 📜 Lizenz

**Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**

- ✅ Nutzung für Forschung & Naturschutz
- ✅ Anpassungen & Verbesserungen
- ✅ Teilen mit Namensnennung
- ❌ Kommerzielle Nutzung ohne Genehmigung

---

## 🙏 Danksagungen

- **TeensyBat** - Cor Berrevoets (Hardware-Design)
- **BatDetect2** - Oisin Mac Aodha et al. (CNN-Modell)
- **Open Science Community** - Für Tools, Bibliotheken und Inspiration

---

## 📚 Zitierung

Wenn Du NEXUS in wissenschaftlichen Arbeiten verwendest, bitte zitiere:

```
Roth, J. (2026). NEXUS: Mikroklima-integriertes Fledermaus-Monitoring System.
GitHub Repository: https://github.com/scanjack/NEXUS_DIY_Sensorik
```

*(DOI folgt nach Zenodo-Upload)*

---

## 🦇 "Die One-Man-Show fährt wieder los."

Von der Werkbank eines Maschinenschlossers zur Open-Source-Fledermausforschung.

**Gebaut in Paderborn. Für die Fledermäuse.**

---

**READY._**
