# Validierungsprotokoll: NEXUS Feldtest Frühjahr 2026

Dieses Dokument dient der systematischen Überprüfung der Messgenauigkeit des NEXUS-Systems unter realen Freilandbedingungen. Ziel ist es, die Korrelation zwischen den Mikroklima-Daten und der akustischen Detektionsreichweite (ISO 9613-1) nachzuweisen.

## 1. Versuchsaufbau & Equipment

### Referenz-Hardware
* **Audio-Referenz:** TeensyBat (Full-Spectrum Recording)
* **Thermische Verifizierung:** TOPDON TS004 Thermalkamera (zur visuellen Bestätigung der Flugaktivität und Distanzschätzung)
* **NEXUS v4.3.1:** * Umweltsensor: BME680 (Temperatur, Feuchte, Druck)
    * GPS: AIR530 (Präzisions-Zeitstempel & Position)
    * Anemometer: Sparkfun SEN-15901 (Windgeschwindigkeit/Richtung)

### Konfiguration
* **Kein Pin-Tapping:** Die Systeme laufen autark. Die Synchronisation erfolgt ausschließlich über die GPS-Zeitstempel im Post-Processing.
* **Kein "Set-and-Forget":** Während der Validierungsphase erfolgt eine aktive Überwachung der Sensoren vor Ort, um Fehlmessungen durch externe Einflüsse (z.B. Bewuchs, Insekten auf den Sensoren) auszuschließen.

## 2. Messparameter & Toleranzen

| Parameter | Sensor | Erwartete Genauigkeit | Referenzabgleich |
| :--- | :--- | :--- | :--- |
| Temperatur | BME680 | ±0.5 °C | Kalibriertes Außenthermometer |
| Luftfeuchte | BME680 | ±3 % rH | Hygrometer-Referenz |
| Windspeed | SEN-15901 | ±1 m/s | Hand-Anemometer |
| Zeitstempel | AIR530 | ±1.0 s | GPS-Referenzzeit |

## 3. Durchführung der Testreihen

### Phase A: Statische Kalibrierung
* Vergleich der BME680-Werte mit einer stationären Wetterstation über 24 Stunden.
* Prüfung der GPS-Drift bei festem Standort.

### Phase B: Akustische Reichweiten-Validierung (ISO 9613-1)
1.  Aufstellung des NEXUS an einem bekannten Fledermaus-Hotspot.
2.  Parallelaufzeichnung mit dem TeensyBat.
3.  Einsatz der **TOPDON TS004**, um die Distanz vorbeifliegender Individuen visuell zu schätzen.
4.  Berechnung der theoretischen Dämpfung via `nexus_pipeline_commander.py`.
5.  Abgleich: Entspricht die Signalstärke im Sonogramm der berechneten Dämpfung über die geschätzte Distanz?

## 4. Dokumentation & Fotografie
* Fotografische Dokumentation jedes Messaufbaus (Einhaltung der DIN-Vorgaben für Wetterstationen: Höhe, freie Anströmung).
* Screenshots der Live-Web-Interface-Daten während markanter Wetterereignisse.
* Speicherung der Roh-CSV-Logs für den Peer-Review-Nachweis.

## 5. Auswertung (Pipeline-Check)
Die Daten werden durch die 13 Module des Commanders prozessiert. Ein Test gilt als validiert, wenn:
- [ ] Der Zeitstempel-Sync zwischen Audio (WAV) und Klima (CSV) fehlerfrei erfolgt.
- [ ] Die ISO-Dämpfungswerte innerhalb der physikalischen Plausibilität liegen.
- [ ] Der automatisierte Batch-Validator keine signifikanten Diskrepanzen zwischen KI-Arterkennung und Frequenzspektrum meldet.

---
**Protokollführer:** Jochen Roth  
**Start der Validierung:** Geplant März/April 2026
