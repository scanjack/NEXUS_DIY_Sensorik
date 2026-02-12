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
Purpose: Statistical aggregation and summary of reconstructed detections 
         for activity pattern analysis.
         / Statistische Aggregation und Zusammenfassung der rekonstruierten 
         Detektionen zur Analyse von Aktivitätsmustern.
Version: 1.0.0
Date:    15.01.2026
"""

import pandas as pd
import glob
import os
import json
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------
# 1) CONFIGURATION / KONFIGURATION
# ---------------------------------------------------------

INPUT_DIR = "anns"         # Folder with BatDetect2 results (*.json, *.csv) / Ordner mit BatDetect2-Ergebnissen
OUTPUT_DIR = "results"     # Output directory / Ausgabeverzeichnis
INDIVIDUAL_DETECTIONS_SUBDIR = "individual_detections" # Subdirectory for CSVs per file / Unterverzeichnis für CSVs pro Datei
SCORE_THRESHOLD = 0.5      # Only calls above this score threshold / Nur Rufe oberhalb dieser Score-Schwelle

SPECIES_RULES = [
    # 1. Rhinolophus (CF callers - highest frequencies) / (CF-Rufer - höchste Frequenzen)
    ("Rhinolophus hipposideros", 106, 120),  # NEW: 105-115 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    ("Rhinolophus ferrumequinum", 77, 88),   # NEW: 75-85 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    
    # 2. Pipistrellus/Nyctalus/Eptesicus (Standard species) / (Standard-Arten)
    ("Pipistrellus pygmaeus", 53, 58),       # F_peak ~ 55 kHz (Not in frequencies.csv, kept original) / Originalwert beibehalten
    ("Pipistrellus pipistrellus", 45, 75),   # NEW: 44-50 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    ("Pipistrellus nathusii", 37, 50),       # NEW: 37-42 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    ("Eptesicus serotinus", 25, 40),         # NEW: 24-28 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    ("Nyctalus noctula", 18, 30),            # NEW: 18-25 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    ("Nyctalus leisleri", 25, 45),           # NEW: 25-30 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    ("Vespertilio murinus", 22, 35),         # NEW: 28-35 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    ("Eptesicus nilssonii", 23, 35),         # NEW: 28-33 kHz (Extended based on frequencies.csv) / NEU: Erweitert

    # 3. Myotis (CF/FM callers - often broad bands) / (CF/FM-Rufer - oft breite Bänder)
    ("Myotis mystacinus/brandtii", 40, 65),  # NEW: 50-60 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    ("Myotis daubentonii", 45, 65),          # NEW: 35-50 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    ("Myotis nattereri", 40, 65),            # Very broad, variable band (Updated to CSV values) / Sehr breites, variables Band
    ("Myotis bechsteinii", 35, 50),          # Large band (Updated to CSV values) / Großes Band
    ("Myotis myotis/blythii", 25, 50),       # NEW: 28-45 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    ("Myotis dasycneme", 40, 65),            # NEW: 35-40 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    ("Myotis capaccinii", 40, 50),           # (Not in frequencies.csv, kept original) / Originalwert beibehalten
    ("Myotis alcathoe", 55, 65),             # F_peak ~ 57 kHz (Not in frequencies.csv, kept original) / Originalwert beibehalten
    ("Myotis emarginatus", 35, 55),          # NEW: 45-55 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    
    # 4. Others / Andere
    ("Barbastella barbastellus", 30, 40),    # F_peak ~ 35 kHz (Combined Mopsfledermaus_A/B from CSV) / Kombiniert aus CSV
    ("Plecotus auritus/austriacus", 25, 40), # Extremely broad band (Updated to CSV values) / Extrem breites Band
    ("Miniopterus schreibersii", 50, 60),    # (Not in frequencies.csv, kept original) / Originalwert beibehalten
    ("Tadarida teniotis", 10, 15),           # (Not in frequencies.csv, kept original) / Originalwert beibehalten
    ("Hypsugo savii", 30, 55),               # NEW: 30-40 kHz (Extended based on frequencies.csv) / NEU: Erweitert
    ("Nyctalus lasiopterus", 18, 22),        # (Not in frequencies.csv, kept original) / Originalwert beibehalten
    ("Pipistrellus kuhlii", 35, 50),         # NEW: Added from frequencies.csv / NEU: Hinzugefügt aus CSV
    
    # FALLBACK must remain at the end / FALLBACK muss am Ende bleiben
    ("Unknown/Fallback", 0, 125),            # Ensures no call is overlooked. / Stellt sicher, dass kein Ruf übersehen wird.
]

# ---------------------------------------------------------
# 2) FUNCTIONS / FUNKTIONEN
# ---------------------------------------------------------

def assign_species(freq_mean_khz: float) -> str:
    """
    Assigns a species to a mean frequency (in kHz) (or 'undefined').
    Ordnet einer mittleren Frequenz (in kHz) eine Art zu (oder 'unbestimmt').
    """
    if pd.isna(freq_mean_khz):
        return "unbestimmt"
    for name, fmin, fmax in SPECIES_RULES:
        if fmin <= freq_mean_khz <= fmax:
            return name
    return "unbestimmt"

def load_all_json(input_dir: str, score_thresh: float) -> pd.DataFrame:
    """
    Loads all JSON files from a folder and extracts detections.
    Lädt alle JSON-Dateien aus einem Ordner und extrahiert die Detektionen.
    """
    files = glob.glob(os.path.join(input_dir, "*.json"))
    if not files:
        print(f"⚠️ Keine JSON-Dateien in {input_dir} gefunden.")
        return pd.DataFrame(columns=[
            "start", "end", "low_freq", "high_freq", "freq_max", 
            "freq_min", "freq_mean", "confidence", "source_file", "basename"
        ])

    all_records = []

    for file in files:
        try:
            with open(file, "r") as f:
                data = json.load(f)

            detections = data.get("annotation", [])
            
            for det in detections:
                low_f = det.get("low_freq")
                high_f = det.get("high_freq")
                freq_mean = det.get("freq_mean")

                if freq_mean is None and low_f is not None and high_f is not None:
                    freq_mean = (low_f + high_f) / 2000 
                else:
                    freq_mean = freq_mean / 1000 if freq_mean is not None else np.nan

                rec = {
                    "start": det.get("start_time"), 
                    "end": det.get("end_time"),     
                    "low_freq": low_f,
                    "high_freq": high_f,
                    "freq_max": det.get("freq_max"),
                    "freq_min": det.get("freq_min"),
                    "freq_mean": freq_mean,
                    "confidence": det.get("det_prob", np.nan), 
                    "source_file": os.path.basename(file),
                    "basename": os.path.splitext(os.path.basename(file))[0]
                }
                all_records.append(rec)

        except Exception as e:
            print(f"⚠️ Fehler beim Laden von {file}: {e}")

    df = pd.DataFrame(all_records)
    
    if df.empty:
        return pd.DataFrame(columns=[
            "start", "end", "low_freq", "high_freq", "freq_max", 
            "freq_min", "freq_mean", "confidence", "source_file", "basename"
        ])

    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce") 

    if not df["confidence"].isna().all(): 
        df = df[df["confidence"] >= score_thresh].copy() 
    
    if not df.empty:
        df = df.dropna(subset=['freq_mean']).copy()

    # Add initial 'species' column here, based on JSON data
    # and rename confidence to avoid conflicts during merge
    # / Füge hier die initialen 'species' Spalte hinzu, basierend auf JSON Daten
    # und benenne confidence um, damit es keine Konflikte beim Merge gibt
    df['species_json'] = df["freq_mean"].apply(assign_species)
    df['confidence_json'] = df['confidence']
    df['low_freq_json'] = df['low_freq'] # Also frequencies for consistent merging / Auch Frequenzen für konsistentes Merging
    df['high_freq_json'] = df['high_freq']
    
    return df

def load_all_csv(input_dir: str) -> pd.DataFrame:
    """
    Loads all CSV files from a folder and extracts species assignment.
    Lädt alle CSV-Dateien aus einem Ordner und extrahiert die Artenzuordnung.
    """
    files = glob.glob(os.path.join(input_dir, "*.csv"))
    if not files:
        print(f"⚠️ Keine CSV-Dateien in {input_dir} gefunden.")
        return pd.DataFrame(columns=[
            'start', 'end', 'low_freq', 'high_freq', 'species', 'confidence', 'freq_mean', 'source_file', 'basename'
        ])

    all_dfs = []
    for file in files:
        try:
            df_csv = pd.read_csv(file)
            df_csv['source_file'] = os.path.basename(file)
            df_csv['basename'] = os.path.splitext(os.path.basename(file))[0]
            
            # Adjust column names here if BatDetect2 uses different names
            # / Passe hier Spaltennamen an, falls BatDetect2 andere Namen verwendet
            df_csv = df_csv.rename(columns={
                'start_time': 'start',
                'end_time': 'end',
                'class': 'species', 
                'det_prob': 'confidence',
            }, errors='ignore') 
            
            all_dfs.append(df_csv)
        except Exception as e:
            print(f"⚠️ Fehler beim Laden von {file}: {e}")
            
    if not all_dfs:
        return pd.DataFrame(columns=[
            'start', 'end', 'low_freq', 'high_freq', 'species', 'confidence', 'freq_mean', 'source_file', 'basename'
        ])
        
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    for col in ['start', 'end', 'low_freq', 'high_freq', 'species', 'confidence', 'freq_mean']:
        if col not in combined_df.columns:
            combined_df[col] = np.nan
    
    # Prepare CSV columns for merge / Hier die CSV-Spalten für den Merge vorbereiten
    combined_df['species_csv'] = combined_df['species']
    combined_df['confidence_csv'] = combined_df['confidence']
    combined_df['low_freq_csv'] = combined_df['low_freq']
    combined_df['high_freq_csv'] = combined_df['high_freq']

    return combined_df

def plot_histogram(df: pd.DataFrame, output_path: str):
    """
    Creates a histogram of mean call frequencies (in kHz).
    Erstellt ein Histogramm der mittleren Ruf-Frequenzen (in kHz).
    """
    plt.figure(figsize=(8, 5))
    plt.hist(df["freq_mean"].dropna(), bins=50, edgecolor="black", alpha=0.7)
    plt.xlabel("Mittlere Frequenz (kHz)")
    plt.ylabel("Anzahl Rufe")
    plt.title("Histogramm der Ruf-Frequenzen")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def plot_species_counts(species_counts: pd.Series, output_path: str):
    """
    Creates a bar chart of species frequencies.
    Erstellt ein Balkendiagramm der Artenhäufigkeiten.
    """
    plt.figure(figsize=(8, 5))
    species_counts.plot(kind="bar", color="skyblue", edgecolor="black")
    plt.ylabel("Anzahl Rufe")
    plt.xlabel("Art")
    plt.title("Artenhäufigkeiten")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

# ---------------------------------------------------------
# 3) MAIN PROGRAM / HAUPTPROGRAMM
# ---------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    individual_detections_path = os.path.join(OUTPUT_DIR, INDIVIDUAL_DETECTIONS_SUBDIR)
    os.makedirs(individual_detections_path, exist_ok=True)

    print("📥 Lade BatDetect2-JSON-Ergebnisse ...")
    df_json = load_all_json(INPUT_DIR, SCORE_THRESHOLD)
    
    print("📥 Lade BatDetect2-CSV-Ergebnisse ...")
    df_csv = load_all_csv(INPUT_DIR)

    if df_json.empty and df_csv.empty:
        print("❌ Skript beendet, da keine Daten zum Verarbeiten vorhanden sind.")
        return
    
    df = pd.DataFrame() # Start with an empty DataFrame / Start mit einem leeren DataFrame

    if not df_json.empty:
        df = df_json.copy()
        # Ensure 'neutral' columns exist / Stellen wir sicher, dass die "neutralen" Spalten existieren
        if 'species' not in df.columns: df['species'] = np.nan
        if 'confidence' not in df.columns: df['confidence'] = np.nan
        if 'low_freq' not in df.columns: df['low_freq'] = np.nan
        if 'high_freq' not in df.columns: df['high_freq'] = np.nan

    if not df_csv.empty:
        merge_cols = ['basename', 'start', 'end']
        
        # List of columns from df_csv to be merged (which already have suffixes)
        # / Liste der Spalten aus df_csv, die gemergt werden sollen (die bereits Suffixe haben)
        csv_suffixed_cols = [col for col in ['species_csv', 'confidence_csv', 'low_freq_csv', 'high_freq_csv'] if col in df_csv.columns]

        if df.empty: # If df_json was empty / Wenn df_json leer war
            df = df_csv.copy()
            # Fill neutral columns directly from _csv columns
            # / Fülle die neutralen Spalten direkt aus den _csv Spalten
            df['species'] = df.get('species_csv', np.nan)
            df['confidence'] = df.get('confidence_csv', np.nan)
            df['low_freq'] = df.get('low_freq_csv', np.nan)
            df['high_freq'] = df.get('high_freq_csv', np.nan)
            
            # Apply assign_species if 'species' is still empty
            # / Wende assign_species an, falls 'species' noch leer ist
            if df['species'].isna().all() and 'freq_mean' in df.columns:
                df['species'] = df['freq_mean'].apply(assign_species)

            print(f"➡️ {len(df)} Rufe nur aus CSV-Dateien geladen.")
        else: # df_json was not empty, now merge with df_csv / df_json war nicht leer, jetzt merge mit df_csv
            # We merge df (already contains _json columns) with df_csv (contains _csv columns)
            # No suffixes in merge command here, as columns are already renamed
            # / Wir mergen df (enthält bereits _json Spalten) mit df_csv (enthält _csv Spalten)
            # Hier keine Suffixe im Merge-Befehl, da die Spalten bereits umbenannt sind
            df = pd.merge(df, df_csv[merge_cols + csv_suffixed_cols], 
                          on=merge_cols, 
                          how='left')
            print(f"➡️ Daten aus {len(df_json)} JSON-Detektionen und CSV-Dateien kombiniert.")
            
            # Assignment of final 'species' column
            # Prioritize species_csv if present and not-NaN
            # / Zuweisung der finalen 'species' Spalte
            # Priorisiere species_csv, wenn vorhanden und nicht-NaN
            df['species'] = np.where(
                df.get('species_csv').notna() if 'species_csv' in df.columns else False, 
                df['species_csv'], 
                df['species_json'] # Fallback to JSON-based species / Fallback zur JSON-basierten Art
            )

            # Assignment of final 'confidence' column
            # / Zuweisung der finalen 'confidence' Spalte
            df['confidence'] = np.where(
                df.get('confidence_csv').notna() if 'confidence_csv' in df.columns else False, 
                df['confidence_csv'], 
                df['confidence_json'] # Fallback to JSON-based confidence / Fallback zur JSON-basierten Konfidenz
            )

            # Assignment of final frequency columns
            # / Zuweisung der finalen Frequenz-Spalten
            df['low_freq'] = np.where(
                df.get('low_freq_csv').notna() if 'low_freq_csv' in df.columns else False, 
                df['low_freq_csv'], 
                df['low_freq_json']
            )
            df['high_freq'] = np.where(
                df.get('high_freq_csv').notna() if 'high_freq_csv' in df.columns else False, 
                df['high_freq_csv'], 
                df['high_freq_json']
            )
            
            # Clean up extra suffix columns
            # / Bereinige die zusätzlichen Suffix-Spalten
            df = df.drop(columns=[col for col in df.columns if col.endswith(('_json', '_csv')) and col not in ['species', 'confidence', 'low_freq', 'high_freq']], errors='ignore')
    
    # If df is still empty (e.g. no JSONs and empty CSVs), exit
    # / Wenn df immer noch leer ist (z.B. keine JSONs und leere CSVs), beenden
    if df.empty:
        print("❌ Skript beendet, da keine Daten zum Verarbeiten vorhanden sind.")
        return

    # Final check for 'species' and 'confidence'
    # / Letzte Sicherstellung für 'species' und 'confidence'
    if 'species' not in df.columns or df['species'].isna().all():
        if 'freq_mean' in df.columns:
            df['species'] = df['freq_mean'].apply(assign_species)
        else:
            df['species'] = "unbestimmt" # Absolute fallback / Absoluter Fallback

    if 'confidence' not in df.columns:
        df['confidence'] = np.nan 

    # Save total data / Gesamtdaten speichern
    all_file = os.path.join(OUTPUT_DIR, "all_detections.csv")
    df.to_csv(all_file, index=False)
    print(f"💾 Alle Detektionen gespeichert in: {all_file}")

    # NEW: Save individual CSV files per original WAV file
    # / NEU: Individuelle CSV-Dateien pro Original-WAV-Datei speichern
    print(f"💾 Speichere individuelle Detektionen pro Datei in {individual_detections_path} ...")
    
    if 'basename' not in df.columns:
        print("❌ 'basename' Spalte nicht gefunden. Kann individuelle Dateien nicht speichern.")
    else:
        for basename, group_df in df.groupby("basename"):
            output_csv_path = os.path.join(individual_detections_path, f"{basename}.csv")
            
            columns_to_save = ['start', 'end', 'low_freq', 'high_freq', 'species', 'confidence']
            existing_columns = [col for col in columns_to_save if col in group_df.columns]
            
            group_df[existing_columns].to_csv(output_csv_path, index=False)

    # Sums over all files / Summen über alle Dateien
    species_counts = df["species"].value_counts() 
    species_counts_file = os.path.join(OUTPUT_DIR, "species_summary.csv")
    species_counts.to_csv(species_counts_file)
    print(f"💾 Artenübersicht gespeichert in: {species_counts_file}")

    # Species per file / Arten pro Datei
    species_per_file = df.groupby("basename")["species"].unique() 
    species_per_file_file = os.path.join(OUTPUT_DIR, "species_per_file.csv")
    species_per_file.to_csv(species_per_file_file)
    print(f"💾 Arten pro Datei gespeichert in: {species_per_file_file}")

    # Generate graphics / Grafiken erzeugen
    hist_file = os.path.join(OUTPUT_DIR, "freq_histogram.png")
    plot_histogram(df, hist_file)
    print(f"📊 Histogramm gespeichert in: {hist_file}")

    species_plot_file = os.path.join(OUTPUT_DIR, "species_counts.png")
    plot_species_counts(species_counts, species_plot_file)
    print(f"📊 Arten-Balkendiagramm gespeichert in: {species_plot_file}")

    print("✅ Fertig!")

if __name__ == "__main__":
    main()