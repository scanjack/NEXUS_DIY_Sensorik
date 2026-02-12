# NEXUS Python Analysis Suite 🦇

Diese Suite ist das zentrale Bindeglied zwischen der Hardware im Feld und der wissenschaftlichen Auswertung. Das Master-Skript `nexus_pipeline_commander.py` orchestriert vollautomatisch 13 spezialisierte Module, um Rohdaten in präzise Erkenntnisse zu verwandeln.

## 🚀 Schnellstart

### 1. Abhängigkeiten installieren
Stellen Sie sicher, dass Python 3.10 oder neuer installiert ist. Führen Sie im Terminal folgenden Befehl aus, um alle benötigten Bibliotheken (inkl. BatDetect2, Pandas, SciPy) zu installieren:

```bash
pip install -r requirements.txt
```

### 2. Pfad-Konfiguration
Öffnen Sie `nexus_pipeline_commander.py` in einem Editor. Passen Sie im Abschnitt `PATH CONFIGURATION` die Verzeichnisse an Ihre lokale Struktur an:
* `BASE_DIR`: Ihr Hauptarbeitsverzeichnis.
* `RAW_AUDIO`: Der Ort Ihrer WAV-Aufnahmen.

### 3. Analyse starten
Führen Sie das Master-Skript aus:

```bash
python nexus_pipeline_commander.py
```

Das Skript schaltet das Windows-Energiemanagement während der Laufzeit automatisch auf "Höchstleistung", um die KI-Berechnungen zu beschleunigen, und kehrt danach in den Standardmodus zurück.

## ⚙️ Zentrale Features & Einstellungen

* **KI-Threshold:** Standardmäßig arbeitet die Pipeline mit einem Schwellenwert von **0.8**. Dies kann im Skript angepasst werden, um die Sensitivität der Artbestimmung zu steuern.
* **ISO 9613-1 Berechnung:** Die Suite nutzt die BME680-Umweltdaten des NEXUS, um für jeden Ruf die atmosphärische Dämpfung und die tatsächliche Reichweite zu kalkulieren.
* **Validierung:** Ein automatisierter Abgleich stellt sicher, dass die KI-Ergebnisse physikalisch plausibel sind (Frequenzprüfung).

## 🛠 Die 13 Analyse-Schritte

Der Commander führt folgende Prozesse sequenziell aus:
1.  **Segmentierung:** Zerlegung großer WAV-Dateien.
2.  **KI-Klassifizierung:** Spezies-Erkennung via BatDetect2.
3.  **Physikalische Validierung:** Frequenz-Check der Ergebnisse.
4.  **Astro-Zeitstempel:** Abgleich mit Sonnenauf/-untergang.
5.  **Umwelt-Korrelation:** Einbindung der NEXUS-Sensordaten.
6.  **Reichweiten-Korrektur:** Dämpfungsberechnung nach ISO-Norm.
7.  **Daten-Zusammenführung:** Finaler Merge aller Parameter.
8.  **Visualisierung:** Erstellung von Pareto-Analysen und Aktivitätsdiagrammen.
9.  **Geografie-Export:** Generierung von KML-Dateien für Google Earth.

## 📄 Lizenz & Urheberrecht

Copyright (C) 2025-2026 Jochen Roth.

Dieses Projekt ist unter der **Creative Commons Attribution-NonCommercial 4.0 International (CC-BY-NC-4.0)** lizenziert. 

* **Namensnennung:** Sie müssen angemessene Urheberangaben machen.
* **Nicht-kommerziell:** Die Software darf nicht für kommerzielle Zwecke verwendet werden.

Weitere Informationen zur Lizenz finden Sie unter: http://creativecommons.org/licenses/by-nc/4.0/
