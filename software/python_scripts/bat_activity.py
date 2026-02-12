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
Purpose: Visualization of the temporal distribution of bat activity 
         by creating hourly activity charts.
         / Visualisierung der zeitlichen Verteilung der Fledermausaktivität 
         durch Erstellung stündlicher Aktivitätsdiagramme.
Version: 1.0.0
Date:    15.01.2026
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import sys

# ---------------------------------------------------------
# 1) CONFIGURATION / KONFIGURATION
# ---------------------------------------------------------

INPUT_FILE_NAME = "results/all_detections.csv"
OUTPUT_FILE_NAME = "results/hourly_activity.png"

# ---------------------------------------------------------
# 2) FUNCTIONS / FUNKTIONEN
# ---------------------------------------------------------

def plot_hourly_activity(df: pd.DataFrame, output_path: Path):
    """
    Creates a bar chart: Number of detections per hour (x-axis) and species (color).
    Erstellt ein Balkendiagramm: Anzahl Detektionen pro Stunde (X-Achse) und Art (Farbe).
    """
    # Convert 'start' to datetime objects / 'start' in Datetime-Objekte umwandeln
    # errors='coerce' turns invalid values into NaT / errors='coerce' macht ungültige Werte zu NaT
    df['start_dt'] = pd.to_datetime(df['start'], errors='coerce')
    
    # Remove rows without valid time / Zeilen ohne gültige Zeit entfernen
    df = df.dropna(subset=['start_dt'])
    
    if df.empty:
        print("⚠️ Keine gültigen Zeitstempel für das Aktivitätsdiagramm gefunden.")
        return

    # Extract hour / Stunde extrahieren
    df['hour'] = df['start_dt'].dt.hour
    
    # Filter: Consider only hours from 18:00 to 08:00 (Night/Twilight)
    # / Filter: Nur Stunden von 18:00 bis 08:00 berücksichtigen (Nacht/Dämmerung)
    # 18,19,20,21,22,23,0,1,2,3,4,5,6,7,8
    df_filtered = df[ (df['hour'] >= 18) | (df['hour'] <= 8) ]
    
    if df_filtered.empty:
        print("⚠️ Keine Detektionen im Zeitraum 18:00 - 08:00 Uhr.")
        # Optional: Use all data if filter is too strict
        # / Optional: Alle Daten nutzen, falls Filter zu streng
        df_filtered = df 
        print("   -> Nutze alle verfügbaren Stunden als Fallback.")

    # Sort solely for neat plotting (optional) / Sortierung rein für schöneres Plotten (optional)
    # We sort by timestamp to have the hours chronologically correct if they span one night
    # / Wir sortieren nach Zeitstempel, damit die Stunden chronologisch stimmen, falls über eine Nacht
    df_filtered = df_filtered.sort_values(by='start_dt')

    # Group data by hour and species / Gruppierung der Daten nach Stunde und Art
    activity = df_filtered.groupby(['hour', 'species']).size().unstack(fill_value=0)
    
    # HERE the problematic reindex(range(24)) line was removed,
    # to plot only hours containing data.
    # / HIER wurde die problematische reindex(range(24)) Zeile entfernt,
    # um nur die Stunden zu plotten, die noch Daten enthalten.
    
    plt.figure(figsize=(10, 6))
    
    # Plotting the bars / Plotten der Balken
    activity.plot(kind='bar', ax=plt.gca(), width=0.8) 
    
    plt.title("Hourly Activity (Calls per Hour) / Stuendliche Aktivitaet")
    plt.xlabel("Hour of Day (Start Time) / Stunde des Tages")
    plt.ylabel("Number of Detections / Anzahl der Detektionen")
    plt.xticks(rotation=0)
    plt.legend(title="Species / Art")
    plt.grid(axis='y', linestyle='--')
    plt.tight_layout()
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path)
    plt.close()
    print(f"✅ Hourly activity graph saved to / Stuendlicher Aktivitaetsgraph gespeichert in: {output_path}")


# ---------------------------------------------------------
# 3) MAIN PROGRAM / HAUPTPROGRAMM
# ---------------------------------------------------------

def main():
    BASE_DIR = Path(__file__).resolve().parent
    INPUT_PATH = BASE_DIR / INPUT_FILE_NAME
    OUTPUT_PATH = BASE_DIR / OUTPUT_FILE_NAME

    print(f"--- Bat Activity Analysis / Fledermaus-Aktivitaets-Analyse ---")
    
    if not INPUT_PATH.exists():
        print(f"❌ Input file not found / Eingabedatei nicht gefunden: {INPUT_PATH}")
        return

    try:
        # Load data / Daten laden
        df = pd.read_csv(INPUT_PATH)
        
        # Check required columns / Benötigte Spalten prüfen
        if 'start' not in df.columns or 'species' not in df.columns:
            print("❌ CSV muss 'start' und 'species' Spalten enthalten.")
            return

        plot_hourly_activity(df, OUTPUT_PATH)

    except Exception as e:
        print(f"❌ Error during processing / Fehler bei der Verarbeitung: {e}")

if __name__ == "__main__":
    main()