#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NEXUS - Data Analysis & Visualization Tool
Part of the NEXUS Bat Research Project

SPDX-FileCopyrightText: 2026 Jochen Roth
SPDX-License-Identifier: CC-BY-NC-4.0
---------------------------------------------------------------------
Copyright (C) 2025-2026 Jochen Roth

This work is licensed under the Creative Commons Attribution-NonCommercial 
4.0 International License. To view a copy of this license, visit 
http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to 
Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

You are free to:
- Share: copy and redistribute the material in any medium or format
- Adapt: remix, transform, and build upon the material

Under the following terms:
- Attribution: You must give appropriate credit.
- NonCommercial: You may not use the material for commercial purposes.
---------------------------------------------------------------------
Project: NEXUS (Environmental Data & Bioacoustics)
Purpose: Merging BatDetect2 results with the segment index to reconstruct 
         timestamps in original recordings. Includes astronomical calculations.
         / Zusammenführung der BatDetect2-Ergebnisse mit dem Segment-Index
         zur Rekonstruktion der Zeitstempel in den Originalaufnahmen.
Version: 1.1.0
Date:    15.01.2026
"""

import pathlib
import xml.sax.saxutils as sax
import re
import datetime
import struct
import os
import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict, Any, List

# --- MISSING DEFINITIONS ADDED / FEHLENDE DEFINITIONEN NACHGETRAGEN ---

# 1. Regex for floating point numbers (used in parse_position_string) /
# 1. Regex für Fließkommazahlen (wurde in parse_position_string verwendet)
_FLOAT_RE = re.compile(r'[-+]?[0-9]*\.?[0-9]+')

# 2. Safe import for guano / 
# 2. Sicherer Import für guano
try:
    import guano
except ImportError:
    guano = None
    print("[INFO] 'guano' Bibliothek nicht gefunden. Erweiterte Metadaten können nicht gelesen werden.")

# **********************************************************
# * PLATFORM INDEPENDENT CONFIGURATION / 
# * PLATFORMUNABHÄNGIGE KONFIGURATION
# **********************************************************
BASE_DIR = pathlib.Path(__file__).resolve().parent

# Path to WAV files (relative to script) /
# Pfad zu den WAV-Dateien (relativ zum Skript)
WAV_DIRECTORY = BASE_DIR / "audio_work"

# KML Output / Die KML-Ausgabe
OUTPUT_KML_NAME = "kml_auswertung_final.kml" 
OUTPUT_KML_PATH = BASE_DIR / OUTPUT_KML_NAME

# --- Astronomy Libraries / Astronomie-Bibliotheken ---
# Global variables for Skyfield / Globale Variablen für Skyfield
ts, eph, moon, sun = None, None, None, None

try:
    from skyfield.api import load, Topos
    
    print("[INFO] Initialisiere Skyfield für Astro-Berechnung...")
    ts = load.timescale()
    
    ephem_file = BASE_DIR / 'de421.bsp'
    if not ephem_file.exists():
        print(f"[INFO] Ephemeriden-Datei {ephem_file.name} nicht gefunden. Lade herunter (dies passiert nur 1x)...")
        eph = load('de421.bsp')
    else:
        eph = load(str(ephem_file))
        
    moon = eph['moon']
    sun = eph['sun']
    earth = eph['earth']
    print("[INFO] Skyfield erfolgreich geladen.")

except ImportError:
    print("[FEHLER] 'skyfield' ist nicht installiert. Mond/Sonnen-Daten werden nicht berechnet.")
    print("Installiere es mit: pip install skyfield")

# ==============================================================================
# --- HELPER FUNCTIONS (GPS & TIME) / HILFSFUNKTIONEN (GPS & ZEIT) ---
# ==============================================================================

def parse_position_string(pos_str):
    """
    Extracts up to 3 floating point numbers from a string.
    / Extrahiert bis zu 3 Fließkommazahlen aus einem String.
    """
    if not pos_str:
        return None
    if isinstance(pos_str, bytes):
        try:
            pos_str = pos_str.decode("utf-8", errors="ignore")
        except Exception:
            pos_str = str(pos_str)
    s = str(pos_str).replace(",", " ")
    nums = _FLOAT_RE.findall(s)
    if not nums:
        return None
    vals = []
    for n in nums[:3]:  # Take up to 3 numbers / Nimm bis zu 3 Zahlen
        try:
            vals.append(float(n))
        except ValueError:
            vals.append(None)
    while len(vals) < 3:  # Fill with None if less than 3 found / Fülle mit None auf, falls weniger als 3 gefunden
        vals.append(None)
    return tuple(vals)

def extract_teensybat_header(fname):
    """
    Reads text chunks and searches for GPS data.
    Improved: Explicitly searches for 'Loc Elevation'.
    / Liest Text-Chunks und sucht nach GPS-Daten.
    Verbessert: Sucht explizit nach 'Loc Elevation'.
    """
    try:
        with open(fname, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        print(f"[FEHLER] {fname}: Datei nicht gefunden.")
        return None
    except Exception as e:
        print(f"[FEHLER] {fname}: WAV-Lesen fehlgeschlagen ({e})")
        return None

    for target_chunk_id_bytes in [b"guano", b"GUANO", b"bext", b"iXML", b"LIST", b"INFO", b"ICMT"]:
        idx = 0
        while True:
            idx = data.find(target_chunk_id_bytes, idx)
            if idx == -1:
                break

            if idx + 8 <= len(data):  # Need at least 8 bytes for ID+Size / Wir brauchen mindestens 8 Bytes für ID+Size
                try:
                    chunk_size = struct.unpack('<I', data[idx + 4:idx + 8])[0]
                except struct.error:
                    idx += 1  # Continue search / Weitersuchen
                    continue
                snippet_start = idx + 8
                snippet_end = min(snippet_start + chunk_size, len(data))
                max_snippet_len = 4096  # Max 4KB
                snippet_end = min(snippet_end, snippet_start + max_snippet_len)
                snippet = data[snippet_start:snippet_end]

                try:
                    txt = snippet.decode("utf-8", errors="ignore")
                except Exception:
                    txt = str(snippet)

                # NEW: 1. Search for Loc Elevation / NEU: 1. Suche nach Loc Elevation
                alt_match = re.search(r'Loc Elevation:\s*([-+]?\d+(?:\.\d+)?)', txt)
                alt_val = None
                if alt_match:
                    try:
                        alt_val = float(alt_match.group(1))
                    except ValueError:
                        pass
                
                # 2. Search for Position (Lat & Lon) - considers 'Position:' and 'Loc Position:' /
                # 2. Suche nach Position (Latitude und Longitude) - berücksichtigt 'Position:' und 'Loc Position:'
                pos_match = re.search(r'(?:Loc Position|Position):\s*([-+]?\d+(?:\.\d+)?)\s*([-+]?\d+(?:\.\d+)?)', txt)
                ts_match = re.search(r'Timestamp:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', txt)
                
                coords = None
                if pos_match:
                    try:
                        lat_val = float(pos_match.group(1)) if pos_match.group(1) else None
                        lon_val = float(pos_match.group(2)) if pos_match.group(2) else None
                        
                        final_alt = alt_val if alt_val is not None else 0.0 
                        
                        coords = (lat_val, lon_val, final_alt)
                    except ValueError:
                        coords = None
                
                timestamp = None
                if ts_match:
                    try:
                        timestamp_str = ts_match.group(1)
                        timestamp = datetime.datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        pass

                if coords and coords[0] is not None and coords[1] is not None:
                    # Debug Output reduced / Debug Ausgabe reduziert
                    return coords[0], coords[1], coords[2], timestamp, "TeensyBat (Text-Fallback)"

            idx += 1  # Continue search in file / Weitersuchen im File
    return None

def is_plausible_europe(lat: Optional[float], lon: Optional[float]) -> bool:
    """
    Plausibility filter for Europe (broad area).
    / Plausibilitätsfilter für Europa (Großraum).
    """
    if lat is None or lon is None: return False
    return 35.0 <= lat <= 70.0 and -10.0 <= lon <= 30.0

def get_position(fname):
    """
    Tries GUANO, then TeensyBat. Improved: Explicitly searches for 'Loc Elevation' in GUANO.
    / Versucht GUANO, dann TeensyBat. Verbessert: Sucht explizit nach 'Loc Elevation' in GUANO.
    """
    if not os.path.exists(fname) or os.path.getsize(fname) == 0:
        return None

    # Try parsing with GUANO library first / Versuche zuerst, mit der GUANO-Bibliothek zu parsen
    if guano:
        try:
            g = guano.GuanoFile(str(fname))
            lat, lon, alt, source_tag = None, None, None, None
            
            # 1. Extract LAT/LON from position keys / 1. LAT/LON aus Positionsschlüsseln extrahieren
            for key in ("Loc|Position", "Loc|Location", "Location", "Position", "GPS Position", "GPS", "gps", "TB|Loc Position", "Comment"):
                if key in g and g[key]:
                    parsed = parse_position_string(g[key])
                    if parsed and all(c is not None for c in parsed[:2]):  # At least Lat and Lon / Mindestens Lat und Lon
                        lat_raw, lon_raw, alt_raw_pos = parsed[0], parsed[1], parsed[2]
                        
                        if is_plausible_europe(lat_raw, lon_raw):
                            lat, lon = lat_raw, lon_raw
                            if alt_raw_pos is not None:
                                alt = alt_raw_pos
                            source_tag = "GUANO"
                        elif is_plausible_europe(lon_raw, lat_raw):
                            lat, lon = lon_raw, lat_raw
                            if alt_raw_pos is not None:
                                alt = alt_raw_pos
                            source_tag = "GUANO (Lat/Lon swapped)"
                        
                        if lat is not None and lon is not None:
                            break 

            # 2. Retrieve ELEVATION from separate key 'Loc Elevation' /
            # 2. HÖHE aus dem separaten Schlüssel 'Loc Elevation' abrufen
            if lat is not None and lon is not None:
                elevation_str = g.get("Loc Elevation")
                if elevation_str:
                    try:
                        alt = float(elevation_str) 
                        source_tag += " (+Elev)" 
                    except ValueError:
                        pass 

                # 3. Timestamp / 3. Zeitstempel
                timestamp_str = g.get("Timestamp")
                timestamp = None
                if timestamp_str:
                    try:
                        timestamp = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    except ValueError:
                        pass
                
                final_alt = alt if alt is not None else 0.0
                return lat, lon, final_alt, timestamp, source_tag
        
        except Exception as e:
            # Fallback on error / Fallback bei Fehlern
            pass

    # If GUANO fails, try TeensyBat fallback / Falls GUANO fehlschlägt, versuche TeensyBat-Fallback
    tb_data = extract_teensybat_header(fname)
    if tb_data:
        lat, lon, alt, timestamp, source = tb_data
        if lat is not None and lon is not None:
            return lat, lon, alt, timestamp, source
    return None

# ==============================================================================
# --- ASTRONOMY FUNCTIONS (SUN & MOON) / ASTRONOMIE FUNKTION (SONNE & MOND) ---
# ==============================================================================

def calculate_astro_data(lat: Optional[float], lon: Optional[float], alt_m: Optional[float], timestamp: Optional[datetime.datetime]) -> Dict[str, Any]:
    """
    Calculates moon phase, moon position AND sun position.
    / Berechnet Mondphase, Mondposition UND Sonnenposition.
    """
    astro_data: Dict[str, Any] = {
        "moon_phase": "N/A", "moon_azimuth": np.nan, "moon_elevation": np.nan,
        "sun_azimuth": np.nan, "sun_elevation": np.nan
    }
    
    if moon is None or sun is None or timestamp is None or lat is None or lon is None:
        return astro_data

    try:
        micro = timestamp.microsecond if timestamp.microsecond < 1000000 else 0
        time_obj = ts.utc(timestamp.year, timestamp.month, timestamp.day, 
                          timestamp.hour, timestamp.minute, timestamp.second + micro / 1_000_000.0)
        
        elevation_m = alt_m if alt_m is not None else 0.0
        observer_location = eph['earth'] + Topos(latitude_degrees=lat, 
                                                longitude_degrees=lon, 
                                                elevation_m=elevation_m)
        
        # Moon / Mond
        astrometric_moon = observer_location.at(time_obj).observe(moon)
        alt_moon, az_moon, _ = astrometric_moon.apparent().altaz()
        astro_data["moon_phase"] = f"{astrometric_moon.fraction_illuminated(sun=sun):.2f}" 
        astro_data["moon_azimuth"] = az_moon.degrees  
        astro_data["moon_elevation"] = alt_moon.degrees 

        # Sun / Sonne
        astrometric_sun = observer_location.at(time_obj).observe(sun)
        alt_sun, az_sun, _ = astrometric_sun.apparent().altaz()
        astro_data["sun_azimuth"] = az_sun.degrees
        astro_data["sun_elevation"] = alt_sun.degrees
        
        return astro_data

    except Exception as e:
        print(f"[WARNUNG] Fehler bei Astro-Berechnung für {timestamp}: {e}") 
        return astro_data

# ==============================================================================
# --- OUTPUT FUNCTIONS / AUSGABE FUNKTIONEN ---
# ==============================================================================

def create_output_files(points: List[Dict[str, Any]], out_kml: pathlib.Path, doc_name: str):
    """
    Writes the Master CSV and the KML file.
    / Schreibt die Master CSV und die KML-Datei.
    """
    
    # --- 1. CREATE CSV / 1. CSV ERSTELLEN ---
    df_master = pd.DataFrame(points)
    df_master = df_master.rename(columns={
        'latitude': 'gps_lat_bat', 'longitude': 'gps_lon_bat', 
        'elevation': 'gps_hoehe_bat', 'timestamp': 'absolute_timestamp'
    })
    
    output_csv_name = 'master_fledermaus_data_mit_mond_final.csv'
    df_master.to_csv(out_kml.parent / output_csv_name, index=False)
    print(f"\n✅ Master-Datenbank inkl. Sonnenstand gespeichert: {output_csv_name}")

    # --- 2. CREATE KML / 2. KML ERSTELLEN ---
    placemarks = []
    for p in points:
        name = sax.escape(p.get("filename", "unknown"))
        desc_lines = [f"Quelle: {p.get('source')}"]
        
        if p.get("timestamp"):
            desc_lines.append(f"Zeit: {sax.escape(str(p['timestamp']))}")
        
        if p.get("sun_elevation") is not None and not np.isnan(p.get("sun_elevation")):
            elev = p.get("sun_elevation")
            if elev > 0: status = "Tag"
            elif elev > -6: status = "Bürgerl. Dämmerung"
            elif elev > -12: status = "Naut. Dämmerung"
            elif elev > -18: status = "Astron. Dämmerung"
            else: status = "Nacht"
            
            desc_lines.append("<b>--- Astronomie ---</b>")
            desc_lines.append(f"Sonne: {elev:.1f}° ({status})")
            desc_lines.append(f"Mond: {p.get('moon_phase')} (Elev: {p.get('moon_elevation'):.1f}°)")
            
        desc = "<br/>".join(desc_lines)
        elevation = p.get("elevation")
        elev_str = str(float(elevation)) if elevation is not None else "0.0"
        
        placemark = f"""  <Placemark>
    <name>{name}</name>
    <description><![CDATA[{desc}]]></description>
    <Point><coordinates>{p['longitude']},{p['latitude']},{elev_str}</coordinates></Point>
  </Placemark>"""
        placemarks.append(placemark)

    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{sax.escape(doc_name)}</name>
    <Style id="pushpin"><IconStyle><Icon><href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href></Icon></IconStyle></Style>
{chr(10).join(placemarks)}
  </Document>
</kml>
"""
    with open(out_kml, "w", encoding="utf-8") as fh:
        fh.write(kml)
    print(f"KML-Datei '{out_kml}' erfolgreich erstellt.")

# ==============================================================================
# --- MAIN ---
# ==============================================================================

def main():
    wav_dir = WAV_DIRECTORY
    out_kml = OUTPUT_KML_PATH
    
    if not wav_dir.is_dir():
        print(f"[FEHLER] Verzeichnis '{wav_dir}' nicht gefunden.")
        return

    points_for_kml: List[Dict[str, Any]] = []
    
    print(f"\nDurchsuche {wav_dir}...")
    
    for fpath in wav_dir.glob("*.wav"):
        pos_data = get_position(fpath)
        
        if pos_data:
            lat, lon, alt, timestamp, source = pos_data
            
            # Astro-Daten (Sonne & Mond) berechnen
            astro_data = calculate_astro_data(lat, lon, alt, timestamp)
            
            if lat is not None and lon is not None and is_plausible_europe(lat, lon):
                point_data = {
                    "filename": fpath.name,
                    "filepath": str(fpath.resolve()),
                    "latitude": lat,
                    "longitude": lon,
                    "elevation": alt,
                    "timestamp": timestamp,
                    "source": source
                }
                point_data.update(astro_data)
                points_for_kml.append(point_data)
                
                print(f"  {fpath.name}: Sonne {astro_data['sun_elevation']:.1f}° | Mond {astro_data['moon_phase']}")
            
    if points_for_kml:
        create_output_files(points_for_kml, out_kml, doc_name=f"Fledermaus Daten {wav_dir.name}")
    else:
        print("[INFO] Keine Dateien mit gültigem GPS gefunden.")

if __name__ == "__main__":
    main()