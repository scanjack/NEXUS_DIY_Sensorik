# NEXUS Hardware-Dokumentation

**Version:** 4.3.1  
**Stand:** Februar 2026  
**Autor:** Jochen Roth

---

## 📦 Komplette Teileliste

### Kern-Komponenten

| Komponente | Typ | Spezifikation | Bezugsquelle | Preis (ca.) |
|------------|-----|---------------|--------------|-------------|
| **Mikrocontroller** | Seeed XIAO ESP32-S3 Sense | Dual-Core, WiFi, Bluetooth | [Seeed Studio](https://www.seeedstudio.com/) | ~15€ |
| **Umweltsensor** | Bosch BME680 | Temp, Humidity, Pressure, VOC (I2C) | AliExpress, Amazon | ~10€ |
| **GPS-Modul** | AIR530 GPS | UART, Positioning + Time Sync | AliExpress | ~8€ |
| **Wind/Regen** | Sparkfun Weather Meter Kit | Anemometer, Wind Vane, Rain Gauge | [Sparkfun](https://www.sparkfun.com/) | ~80€ |
| **Display** | OLED 128x64 | SSD1306, I2C, 0.96" | AliExpress, Amazon | ~5€ |
| **I/O Expander** | PCF8574 | 8-Bit I2C GPIO | AliExpress, Amazon | ~2€ |
| **Rotary Encoder** | KY-040 | Mit Drucktaster | AliExpress, Amazon | ~2€ |
| **SD-Karte Modul** | MicroSD Breakout | SPI Interface | AliExpress, Amazon | ~3€ |
| **RTC** | PCF8563 | Real-Time Clock (Backup: GPS) | AliExpress, Amazon | ~2€ |

### Stromversorgung

| Komponente | Spezifikation | Bezugsquelle | Preis (ca.) |
|------------|---------------|--------------|-------------|
| **Powerbank** | 10.000–20.000 mAh, USB-C | Beliebiger Hersteller | ~15€ |
| **USB-Kabel** | USB-C zu USB-A | Standard | ~3€ |

### Gehäuse & Befestigung

| Komponente | Spezifikation | Bezugsquelle | Preis (ca.) |
|------------|---------------|--------------|-------------|
| **Wetterfestes Gehäuse** | IP65, ca. 15×10×5 cm | Baumarkt, Amazon | ~10€ |
| **Kabelverschraubungen** | M12 oder PG7 | Baumarkt | ~5€ |
| **Montage-Stativ** | Teleskopstange/Fotostativ | Optional | ~20–50€ |

### Kleinteile

| Komponente | Spezifikation | Preis (ca.) |
|------------|---------------|-------------|
| Breadboard/Prototyping-Board | Zur Verkabelung | ~3€ |
| Jumperkabel | Dupont, M-F, F-F | ~3€ |
| Widerstände | 10kΩ Pull-up (falls nötig) | ~1€ |
| MicroSD-Karte | 8–32 GB, Class 10 | ~5€ |

---

## 💰 Gesamtkosten

| Kategorie | Kosten |
|-----------|--------|
| **Elektronik (Kern)** | ~50€ |
| **Sensoren (Wind/Regen)** | ~80€ |
| **Stromversorgung** | ~18€ |
| **Gehäuse & Montage** | ~15–50€ |
| **Kleinteile** | ~12€ |
| **GESAMT** | **~175–210€** |

**Zum Vergleich:**
- Kommerzielle Wetterstationen: 300–1.500€
- Professionelle Fledermaus-Monitoring-Systeme: 3.000–10.000€

---

## 🔌 Pin-Belegung (Seeed XIAO ESP32-S3)

### I2C-Bus (Shared)
```
SDA → GPIO5 (D4)
SCL → GPIO6 (D5)

Geräte am I2C-Bus:
- BME680 (0x76 oder 0x77)
- OLED SSD1306 (0x3C)
- PCF8574 Expander (0x20)
- RTC PCF8563 (0x51)
```

### UART (GPS AIR530)
```
GPS RX → D7 (GPIO43)
GPS TX → D6 (GPIO44)
Baudrate: 9600
```

### SPI (SD-Karte)
```
CS   → D2 (GPIO2)
MOSI → GPIO9  (Standard SPI)
MISO → GPIO8  (Standard SPI)
SCK  → GPIO7  (Standard SPI)
```

### Digital Inputs (Interrupts)
```
Wind Speed (Anemometer) → D0 (GPIO1)
Wind Direction (ADC)    → D1 (GPIO2)
SD-Karte CS             → D2 (GPIO3)
Rain Gauge              → D3 (GPIO4)
```

### PCF8574 Expander (Rotary Encoder)
```
Über I2C gesteuert (Adresse 0x20):
- Bit 0: Encoder CLK
- Bit 1: Encoder DT
- Bit 2: Encoder SW (Button)
```

---

## 🔧 Aufbau-Anleitung

### Schritt 1: I2C-Bus verkabeln
1. Alle I2C-Geräte parallel an SDA/SCL anschließen
2. Pull-up Widerstände (4.7kΩ) zu 3.3V (falls nötig - meist on-board)
3. Adressen prüfen (I2C-Scanner verwenden)

### Schritt 2: GPS-Modul
1. GPS RX → ESP32 D7 (TX)
2. GPS TX → ESP32 D6 (RX)
3. VCC → 3.3V, GND → GND
4. Antenne nach oben/außen richten

### Schritt 3: Sparkfun Weather Meters
**Anemometer (Windgeschwindigkeit):**
- Reed-Switch Ausgang → D0 (mit Pull-up)
- Bei jeder Umdrehung: 2 Impulse
- Kalibrierung: `geschwindigkeit_m/s = impulse/s × 0.6667`

**Windfahne (Windrichtung):**
- Analog Ausgang → D1 (ADC)
- 8 Widerstände für 8 Richtungen
- Wertetabelle im Code hinterlegen

**Regenmesser:**
- Reed-Switch Ausgang → D3 (mit Pull-up)
- Kalibrierung: `niederschlag_mm = impulse × 0.2794`

### Schritt 4: SD-Karte
1. CS → D2
2. Standard SPI-Pins verwenden
3. SD-Karte mit FAT32 formatieren

### Schritt 5: Display & RTC
- Bereits über I2C verkabelt (siehe Schritt 1)
- RTC mit Knopfzelle (CR2032) für Backup

### Schritt 6: Gehäuse
1. **Belüftung:** BME680 braucht Luftzirkulation
   - Löcher bohren + Membrane (z.B. Gore-Tex) für Druckausgleich
2. **Kabeldurchführung:** M12 Verschraubungen verwenden
3. **Montage:** Stativ-Gewinde oder Rohrschellen

---

## ⚡ Stromversorgung

### Powerbank-Modus
- **Problem:** Viele Powerbanks schalten bei geringem Verbrauch ab
- **Lösung im Code:** High-Performance WiFi-Modus hält Powerbank aktiv
- **Laufzeit:** 10.000 mAh Powerbank → ca. 24–48 Stunden (je nach WiFi-Nutzung)

### Alternative: Solar
- 5V Solar-Panel (5–10W)
- Laderegler (TP4056 o.ä.)
- LiPo-Akku (3.7V, 5000–10.000 mAh)
- DC-DC Boost auf 5V für ESP32

---

## 🌧️ Wetterfestigkeit

### IP-Rating Ziel: IP65
**IP6:** Staubdicht  
**IP5:** Schutz gegen Strahlwasser

### Maßnahmen:
1. **Gehäuse:** IP65-zertifiziertes Kunststoffgehäuse
2. **Sensor-Öffnungen:** 
   - BME680: PTFE-Membrane (atmungsaktiv, wasserdicht)
   - Wind/Regen: Externe Montage auf Gehäuse-Oberseite
3. **Kabel:** M12 Verschraubungen mit O-Ringen
4. **Display:** Optional innen montieren (nur für Setup)

### Field-Test Empfehlung:
- Erste Tests bei trockenem Wetter
- Sprühtest mit Wasser vor Dauereinsatz
- Silica-Gel Beutel im Gehäuse (gegen Kondensation)

---

## 🔍 Troubleshooting

### Problem: I2C-Geräte nicht erkannt
**Lösung:**
- I2C-Scanner verwenden ([Beispiel-Code](https://playground.arduino.cc/Main/I2cScanner/))
- Adressen prüfen (BME680 kann 0x76 oder 0x77 sein)
- Pull-up Widerstände prüfen

### Problem: GPS findet keine Satelliten
**Lösung:**
- Freie Sicht zum Himmel (kein Dach, keine Bäume)
- Erste Fix kann 5–15 Minuten dauern (Cold Start)
- LED am GPS-Modul sollte blinken

### Problem: Wind/Regen Sensoren geben keine Werte
**Lösung:**
- Interrupts prüfen (Serial.println in ISR)
- Pull-up Widerstände aktivieren (INPUT_PULLUP)
- Mechanik prüfen (Reed-Switches können verschmutzen)

### Problem: SD-Karte funktioniert nicht
**Lösung:**
- FAT32 formatieren (max. 32 GB)
- CS-Pin korrekt verkabelt?
- Spannungsversorgung stabil?

---

## 📊 Technische Spezifikationen

### BME680 Sensor
- **Temperatur:** -40°C bis +85°C (±1°C Genauigkeit)
- **Luftfeuchtigkeit:** 0–100% rH (±3% Genauigkeit)
- **Luftdruck:** 300–1100 hPa (±1 hPa Genauigkeit)
- **Response Time:** 1 Sekunde (Temperatur)

### GPS AIR530
- **Genauigkeit:** 2.5m CEP (Horizontal)
- **Update Rate:** 1 Hz (Standard), bis 10 Hz möglich
- **Satelliten:** GPS, BeiDou, GLONASS
- **Cold Start:** <30 Sekunden (typisch)

### Sparkfun Weather Meters
- **Anemometer:** 0–175 km/h (0–49 m/s)
- **Windfahne:** 8 Richtungen (45° Auflösung)
- **Regenmesser:** 0.2794 mm pro Kipp

---

## 🔮 Upgrade-Optionen

### Geplant für v5.0+
- **LoRa-Modul:** Fernübertragung ohne WiFi
- **Helligkeitssensor:** (BH1750) für Tag/Nacht-Erkennung
- **Bodentemperatur:** (DS18B20) für Habitatanalyse
- **Solarpanel:** Autarker 24/7-Betrieb

---

## 📝 Notizen für Selbstbau

### Was Du können solltest:
- Grundlagen Elektronik (Breadboard, Löten optional)
- Arduino IDE / PlatformIO
- I2C & SPI verstehen (Tutorials verfügbar)

### Zeitaufwand:
- **Erster Prototyp:** 4–8 Stunden
- **Wetterfestes Gehäuse:** +2–4 Stunden
- **Kalibrierung & Tests:** +4–8 Stunden

### Empfohlene Reihenfolge:
1. Breadboard-Aufbau mit BME680 + OLED
2. GPS hinzufügen (Zeit-Sync testen)
3. Wind/Regen Sensoren (einzeln testen)
4. SD-Karte + Logging
5. Gehäuse + Wetterfest-Montage
6. Feldtest

---

## 🤝 Community & Support

**Fragen? Probleme?**
- GitHub Issues: [NEXUS Repository](https://github.com/scanjack/NEXUS_DIY_Sensorik/issues)
- Blog: [paderbats.blogspot.com](https://paderbats.blogspot.com/)

**Verbesserungen?**
- Pull Requests willkommen!
- Feedback zu Teileliste, Verkabelung, Gehäuse-Lösungen

---

**Viel Erfolg beim Nachbau!**

— Jochen Roth, Februar 2026
