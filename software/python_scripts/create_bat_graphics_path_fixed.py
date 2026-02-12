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
Purpose: Statistical visualization of detection results 
         (Species, Confidence, Frequencies) for Quality Assurance.
         / Statistische Visualisierung der Detektionsergebnisse 
         (Arten, Konfidenz, Frequenzen) zur Qualitätssicherung.
Version: 1.1.0
Date:    15.01.2026
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# **********************************************************
# * CONFIGURATION / KONFIGURATION
# **********************************************************

# Base directory setup (relative to script location) /
# Basisverzeichnis-Setup (relativ zum Skript-Speicherort)
BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "results" / "all_detections.csv"
OUTPUT_DIR = BASE_DIR / "results" / "grafiken_qa"

# Create output directory if it doesn't exist /
# Ausgabeverzeichnis erstellen, falls es nicht existiert
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print(f"--- NEXUS Graphics Generator v1.1.0 ---")
    
    # 1. Load Data / Daten laden
    if not RESULTS_FILE.exists():
        print(f"[FEHLER] Datei nicht gefunden: {RESULTS_FILE}")
        sys.exit(1)
        
    try:
        all_data = pd.read_csv(RESULTS_FILE)
        print(f"Daten geladen: {len(all_data)} Zeilen.")
    except Exception as e:
        print(f"[FEHLER] Konnte CSV nicht lesen: {e}")
        sys.exit(1)

    if all_data.empty:
        print("[WARNUNG] Die Datentabelle ist leer. Keine Grafiken erstellt.")
        sys.exit(0)

    # Set Seaborn Style / Seaborn-Stil setzen
    sns.set_theme(style="whitegrid")

    # --- GRAPH 1: Species Distribution / GRAFIK 1: Artenverteilung ---
    plt.figure(figsize=(10, 6))
    
    # Order by frequency / Sortierung nach Häufigkeit
    order = all_data['species'].value_counts().index
    
    sns.countplot(y='species', data=all_data, order=order, palette='viridis')
    plt.title('Absolute Species Count / Absolute Artenhäufigkeit')
    plt.xlabel('Count / Anzahl')
    plt.ylabel('Species / Art')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '1_arten_verteilung.png')
    print("-> Graph 1 created / Grafik 1 erstellt.")

    # --- GRAPH 2: Confidence Check / GRAFIK 2: Konfidenz-Check ---
    plt.figure(figsize=(10, 6))
    if 'confidence' in all_data.columns:
        sns.histplot(data=all_data, x='confidence', hue='species', multiple='stack', bins=30, palette='magma')
        plt.title('Confidence of Identification / Sicherheit der Bestimmung')
        plt.xlabel('Probability / Wahrscheinlichkeit (0.0 - 1.0)')
        plt.ylabel('Count / Anzahl Rufe')
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / '2_confidence_check.png')
        print("-> Graph 2 created / Grafik 2 erstellt.")
    else:
        print("[INFO] Column 'confidence' missing. Skipping Graph 2. / Spalte 'confidence' fehlt. Überspringe Grafik 2.")

    # --- GRAPH 3: Frequency Analysis / GRAFIK 3: Frequenz-Analyse ---
    # Normalize column names if necessary (BatDetect2 often uses low_freq / high_freq) /
    # Spaltennamen normalisieren falls nötig (BatDetect2 nutzt oft low_freq / high_freq)
    if 'low_freq' in all_data.columns and 'high_freq' in all_data.columns:
        plt.figure(figsize=(10, 8))
        sns.scatterplot(data=all_data, x='low_freq', y='high_freq', hue='species', alpha=0.5, s=30)
        plt.title('Call Characteristics: Frequencies / Ruf-Charakteristik: Frequenzen')
        plt.xlabel('Lowest Frequency / Tiefste Frequenz (Hz)')
        plt.ylabel('Highest Frequency / Höchste Frequenz (Hz)')
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / '3_frequenz_analyse.png')
        print("-> Graph 3 created / Grafik 3 erstellt.")
    else:
        print("[INFO] Frequency columns missing. Skipping Graph 3. / Frequenzspalten fehlen. Überspringe Grafik 3.")

    # --- GRAPH 4: Timeline (Sequence) / GRAFIK 4: Timeline (Sequenz) ---
    plt.figure(figsize=(14, 6))
    
    # Convert start time if possible / Startzeit umwandeln falls möglich
    if 'start' in all_data.columns:
        # Try to parse timestamps. Note: 'start' in BatDetect output is usually relative seconds within file.
        # For a true timeline across files, we would need absolute timestamps (reconstructed elsewhere).
        # Here we plot the raw distribution of 'start' values or index if absolute time is missing.
        # / Versuche Zeitstempel zu parsen. Hinweis: 'start' im BatDetect-Output sind meist relative Sekunden in der Datei.
        # Für eine echte Timeline über Dateien hinweg bräuchten wir absolute Zeitstempel (anderswo rekonstruiert).
        # Hier plotten wir die Rohverteilung der 'start'-Werte oder den Index, falls absolute Zeit fehlt.
        
        sns.scatterplot(data=all_data, x='start', y='species', hue='species', legend=False, alpha=0.6)
        plt.title('Temporal Distribution (within files) / Zeitliche Verteilung (innerhalb Dateien)')
        plt.xlabel('Time (Seconds in File) / Zeit (Sekunden in Datei)')
        plt.ylabel('Species / Art')
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / '4_timeline_sequenz.png')
        print("-> Graph 4 created / Grafik 4 erstellt.")
    else:
        print("[INFO] Column 'start' missing. Skipping Graph 4. / Spalte 'start' fehlt. Überspringe Grafik 4.")

    print(f"✅ Finished. Graphics saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()