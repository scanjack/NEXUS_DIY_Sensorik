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
Purpose: Final merge of Bat/GPS data with NEXUS v4.2.7 environmental logs.
         Includes ISO 9613-1 attenuation values for acoustic analysis.
         / Finaler Merge von Bat/GPS-Daten mit NEXUS v4.2.7 Umweltdaten.
         Inkludiert ISO 9613-1 Dämpfungswerte für die Akustik-Analyse.
Version: 1.3.0
Date:    15.01.2026
"""

import pandas as pd
from pathlib import Path
import datetime
import numpy as np
import sys

# **********************************************************
# * CONFIGURATION / KONFIGURATION
# **********************************************************
BASE_DIR = Path(r"C:\Fledermaus")

# Path to environmental logs (NEXUS) / Pfad zu den Umwelt-Logs (NEXUS)
NEXUS_DIR = Path(r"C:\Fledermaus\nexus-data") 

# Path to the Bat/GPS Master (result from bat_autostart_final.py) /
# Pfad zum Bat/GPS Master (Ergebnis von bat_autostart_final.py)
BAT_MASTER_FILE = BASE_DIR / "master_fledermaus_data_mit_mond_final.csv"

# Path to species classification (result from bat_summary.py) /
# Pfad zur Artbestimmung (Ergebnis von bat_summary.py)
SPECIES_FILE = BASE_DIR / "results" / "species_per_file.csv"

# Output file / Ausgabedatei
OUTPUT_FILE = BASE_DIR / 'master_data_ALL_FINAL.csv'


# **********************************************************
# * HELPER FUNCTIONS / HILFSFUNKTIONEN
# **********************************************************

def parse_timestamp(date_str, time_str):
    """
    Parses date and time from NEXUS CSV.
    Supports formats: DD.MM.YYYY, DD.MM.YY, YYYY-MM-DD.
    / Parst Datum und Zeit aus der NEXUS CSV.
    Unterstützt Formate: DD.MM.YYYY, DD.MM.YY, YYYY-MM-DD.
    """
    try:
        # Normalize date separators / Datums-Trennzeichen normalisieren
        date_str = str(date_str).replace('-', '.')
        
        # Parse logic / Parse-Logik
        if '.' in date_str:
            parts = date_str.split('.')
            if len(parts) == 3:
                day, month, year = parts
                if len(year) == 2: year = "20" + year
                date_iso = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            else:
                return pd.NaT
        else:
            return pd.NaT

        full_str = f"{date_iso} {time_str}"
        return pd.to_datetime(full_str, errors='coerce')
    except:
        return pd.NaT

def clean_species(species_str):
    """
    Cleans the aggregated species string.
    / Bereinigt den aggregierten Arten-String.
    """
    if pd.isna(species_str): return "Unidentified"
    return str(species_str).replace("nan", "").strip(", ")

# **********************************************************
# * MAIN MERGE LOGIC / HAUPT-MERGE-LOGIK
# **********************************************************

def main():
    print("--- FINAL 3-WAY MERGE (Env + GPS + Species) ---")

    # 1. Load Environmental Data / 1. Umweltdaten laden
    # ------------------------------------------------------
    nexus_files = list(NEXUS_DIR.glob("*.csv"))
    if not nexus_files:
        print(f"[FEHLER] Keine NEXUS-Daten in {NEXUS_DIR} gefunden.")
        sys.exit(1)

    print(f"[INFO] Lade {len(nexus_files)} NEXUS-Logdateien...")
    df_env_list = []
    
    for f in nexus_files:
        try:
            # Skip empty files / Leere Dateien überspringen
            if f.stat().st_size < 10: continue
            
            temp_df = pd.read_csv(f)
            # Create timestamp column / Zeitstempel-Spalte erzeugen
            if 'Date' in temp_df.columns and 'Time' in temp_df.columns:
                temp_df['nexus_timestamp'] = temp_df.apply(
                    lambda row: parse_timestamp(row['Date'], row['Time']), axis=1
                )
                df_env_list.append(temp_df)
        except Exception as e:
            print(f"[WARNUNG] Fehler beim Lesen von {f.name}: {e}")

    if not df_env_list:
        print("[FEHLER] Keine gültigen Umweltdaten geladen.")
        sys.exit(1)

    df_env = pd.concat(df_env_list, ignore_index=True)
    df_env = df_env.dropna(subset=['nexus_timestamp']).sort_values('nexus_timestamp')
    print(f"[INFO] Umweltdaten bereit: {len(df_env)} Zeilen.")

    # 2. Load Bat/GPS Data / 2. Bat/GPS-Daten laden
    # ------------------------------------------------------
    if not BAT_MASTER_FILE.exists():
        print(f"[FEHLER] Bat-Master nicht gefunden: {BAT_MASTER_FILE}")
        sys.exit(1)

    df_bat = pd.read_csv(BAT_MASTER_FILE)
    
    # Ensure timestamp format / Zeitstempel-Format sicherstellen
    if 'absolute_timestamp' in df_bat.columns:
        df_bat['absolute_timestamp'] = pd.to_datetime(df_bat['absolute_timestamp'], utc=True).dt.tz_localize(None)
    else:
        print("[FEHLER] 'absolute_timestamp' fehlt in der Bat-Master-Datei.")
        sys.exit(1)

    df_bat = df_bat.sort_values('absolute_timestamp')
    print(f"[INFO] Bat-Daten bereit: {len(df_bat)} Aufnahmen.")

    # 3. Execute Merge (Nearest Match) / 3. Merge durchführen (Nearest Match)
    # ------------------------------------------------------
    # We use merge_asof to find the nearest environmental record for each bat call.
    # Wir nutzen merge_asof, um den zeitlich nächsten Umwelteintrag für jeden Ruf zu finden.
    # Tolerance: e.g. 60 seconds (Environment data should be close)
    # Toleranz: z.B. 60 Sekunden (Umweltdaten sollten zeitnah sein)
    
    print("[INFO] Führe Zeit-Merge durch (Toleranz: 5s)...")
    
    df_merged = pd.merge_asof(
        df_bat, 
        df_env, 
        left_on='absolute_timestamp', 
        right_on='nexus_timestamp', 
        direction='nearest',
        tolerance=pd.Timedelta(seconds=5)
    )

    # 4. Supplement species determination / 4. Ergänze Artbestimmung
    # ------------------------------------------------------
    if SPECIES_FILE.exists():
        print("[INFO] Ergänze Artbestimmung aus BatDetect2...")
        df_spec = pd.read_csv(SPECIES_FILE)
        
        if 'basename' in df_spec.columns:
            df_spec['merge_key'] = df_spec['basename'].str.split('_seg').str[0].str.lower()
            # If extension missing, add it for match / Falls Endung fehlt, hinzufügen für Match
            df_spec['merge_key'] = df_spec['merge_key'].apply(lambda x: x if x.endswith('.wav') else x + '.wav')
            
            # Aggregate multiple detections per file / Mehrere Detektionen pro Datei aggregieren
            # Änderung: 'set' entfernt Duplikate, 'sorted' sortiert das Ergebnis alphabetisch
            df_agg = df_spec.groupby('merge_key')['species'].apply(lambda x: ', '.join(sorted(set(x.astype(str))))).reset_index()
            
            # Find match column in main data / Match-Spalte in Hauptdaten finden
            for cand in ['filename', 'File Name', 'Original Filename']:
                if cand in df_merged.columns:
                    df_merged['merge_key'] = df_merged[cand].astype(str).str.lower()
                    df_merged = pd.merge(df_merged, df_agg, on='merge_key', how='left')
                    df_merged['species_classified'] = df_merged['species'].apply(clean_species)
                    break
    else:
        print("[INFO] Keine Arten-Datei gefunden. Überspringe Schritt.")

    # 5. Save / 5. Speichern
    # ------------------------------------------------------
    # Cleanup: Remove helper columns / Aufräumen: Hilfsspalten entfernen
    drop_cols = ['merge_key', 'nexus_timestamp']
    df_merged.drop(columns=[c for c in drop_cols if c in df_merged.columns], inplace=True, errors='ignore')

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df_merged.to_csv(OUTPUT_FILE, index=False)
    
    print("========================================================")
    print(f"✅ FINAL MERGE ERFOLGREICH.")
    print(f"   Datei gespeichert: {OUTPUT_FILE}")
    print(f"   Datenpunkte: {len(df_merged)}")
    print("========================================================")

if __name__ == "__main__":
    main()