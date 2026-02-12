# Hardware: Sparkfun Weather Meters (SEN-15901)

Die Wetterstation liefert die mechanischen Daten für Windgeschwindigkeit, Windrichtung und Niederschlag. Im NEXUS-Projekt dienen diese Daten primär der Validierung der Flugbedingungen und der Filterung von Störgeräuschen (Windgeräusche am Mikrofon).

## 📊 Technische Spezifikationen
* **Anemometer:** Schalenkreuz-Windmesser (1 Umdrehung/Sek = 2,4 km/h).
* **Windfahne:** Potentiometer-basiert (16 Richtungen via Widerstandsmatrix).
* **Regenmesser:** Wippen-System (0,2794 mm pro Impuls).

## 🔌 Anschluss am XIAO ESP32-S3
Die Sensoren werden über RJ11-Stecker angeschlossen. Da der XIAO ESP32-S3 begrenzte Pins hat, nutzen wir folgende Konfiguration:

| Sensor | Anschluss-Typ | XIAO Pin (Beispiel) | Hinweis |
| :--- | :--- | :--- | :--- |
| **Windspeed** | Digital (Interrupt) | D1 | Interner Pull-Up erforderlich |
| **Regen** | Digital (Interrupt) | D2 | Entprellung (Debouncing) via Software |
| **Windrichtung** | Analog (ADC) | A0 | Widerstandsteiler-Prinzip |

## 🏗️ Montage-Hinweise
1. **Ausrichtung:** Die Windfahne muss exakt nach **Norden** ausgerichtet werden, damit der AIR530 GPS-Kurs und die Windrichtung korrelieren.
2. **Höhe:** Für valide Mikroklima-Daten sollte die Station in ca. 2,0m Höhe frei stehend montiert werden (Vermeidung von Bodenturbulenzen).
3. **Stabilität:** Da das System im Wald/Feld eingesetzt wird, ist eine feste Verankerung des Mastes notwendig, um Vibrationen am TeensyBat-Mikrofon zu minimieren.

## 🛠️ Wartung (Validierungsphase)
Während der Validierung im Frühjahr 2026 muss sichergestellt werden:
* Das Schalenkreuz ist frei von Spinnweben (Anlaufgeschwindigkeit!).
* Der Regenmesser ist waagerecht ausgerichtet (Libelle nutzen).
