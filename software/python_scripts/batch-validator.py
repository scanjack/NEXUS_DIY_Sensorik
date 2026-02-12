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
Purpose: Physical validation of AI inference results. 
         Validation of frequency bands (Low/High kHz), plausibility checks,
         and automated generation of cluster plots and reports.
         / Physikalische Endkontrolle der KI-Inferenz. Validierung von 
         Frequenzbändern (Low/High kHz), Plausibilitätsprüfungen 
         sowie automatisierte Erstellung von Cluster-Grafiken und Berichten.
Version: 7.2.2
Date:    07.02.2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import shutil
import matplotlib.pyplot as plt
import seaborn as sns

# --- KONFIGURATION ---
INPUT_DIR = Path("anns")           # Ordner mit BatDetect2-Ergebnissen
OUTPUT_DIR = Path("validierung")   # Hauptausgabeordner
REVIEW_DIR = OUTPUT_DIR / "manuelle_prüfung" # Unterordner für Problemfälle
REF_CSV = "Frequenzen.csv"         # Deine Referenzdaten

# Verzeichnisse erstellen, falls nicht vorhanden
OUTPUT_DIR.mkdir(exist_ok=True)
REVIEW_DIR.mkdir(exist_ok=True)

def load_reference_db(csv_path):
    """Lädt die 24 Arten und Parameter aus der Referenz-CSV."""
    try:
        df = pd.read_csv(csv_path)
        df = df.dropna(subset=['Art'])
        db = {}
        for _, row in df.iterrows():
            # Name säubern (entfernt wissenschaftlichen Namen in Klammern)
            name = row['Art'].split('(')[0].strip().lower()
            
            # Auch den wissenschaftlichen Namen als Key speichern
            full_name = row['Art'].strip().lower()
            
            params = {
                'f_min': float(row['Hauptfrequenz_min kHz']) * 1000,
                'f_max': float(row['Hauptfrequenz_max kHz']) * 1000,
                'd_min': float(row['Rufdauer_min ms']),
                'd_max': float(row['Rufdauer_max ms'])
            }
            
            db[name] = params
            # Falls wissenschaftlicher Name vorhanden, auch diesen als Key
            if '(' in row['Art']:
                sci_name = row['Art'].split('(')[1].replace(')', '').strip().lower()
                db[sci_name] = params
                
        return db
    except Exception as e:
        print(f"Fehler beim Laden der Referenz-CSV: {e}")
        return None

def validate_row(row, db):
    """Prüft eine einzelne Zeile gegen die Datenbank."""
    # BatDetect2 verwendet 'class' für den Artnamen (wissenschaftlich)
    species_detected = str(row.get('class', '')).lower()
    
    # Frequenz aus 'low_freq' (schon in Hz)
    freq = row.get('low_freq', 0)
    
    # Dauer aus der bereits berechneten Spalte holen
    duration = row.get('duration_ms')

    # Art in DB suchen (Teil-Übereinstimmung)
    match = None
    for key in db:
        if key in species_detected:
            match = db[key]
            break
            
    if not match:
        return "Unknown_Species", "Review_Required"

    issues = []
    
    # Frequenz-Check
    if freq > 0:  # Nur prüfen wenn Frequenz vorhanden
        if not (match['f_min'] <= freq <= match['f_max']):
            issues.append(f"Freq_Outlier({freq/1000:.1f}kHz)")
    
    # Dauer-Check
    if duration and not pd.isna(duration):
        if not (match['d_min'] <= duration <= match['d_max']):
            issues.append(f"Duration_Outlier({duration:.1f}ms)")

    if not issues:
        return "NEXUS_Verified", "OK"
    else:
        return "Review_Required", "|".join(issues)

def main():
    print(f"--- NEXUS Batch Validator gestartet ---")
    print(f"Input:  {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}\n")
    
    db = load_reference_db(REF_CSV)
    if not db:
        print("Fehler: Referenz-Datenbank konnte nicht geladen werden!")
        return
    
    print(f"✓ Referenz-Datenbank geladen: {len(db)} Arten/Einträge\n")

    all_data = []
    files = list(INPUT_DIR.glob("*.csv"))
    
    if not files:
        print(f"Keine CSV-Dateien in '{INPUT_DIR}' gefunden!")
        return

    print(f"Verarbeite {len(files)} CSV-Dateien...")
    print("-" * 60)
    
    for f_path in files:
        try:
            df = pd.read_csv(f_path)
            if df.empty:
                print(f"⊘  {f_path.name}: Datei ist leer")
                continue
            
            # Duration berechnen (BatDetect2 hat start_time und end_time in Sekunden)
            if 'start_time' in df.columns and 'end_time' in df.columns:
                df['duration_ms'] = (df['end_time'] - df['start_time']) * 1000
            else:
                df['duration_ms'] = np.nan
                print(f"⚠  {f_path.name}: Keine Zeit-Spalten (start_time/end_time)")
            
            # Validierung anwenden
            results = df.apply(lambda row: validate_row(row, db), axis=1)
            df['Validation_Status'], df['Quality_Notes'] = zip(*results)
            
            # Statistik für diese Datei
            verified = len(df[df['Validation_Status'] == 'NEXUS_Verified'])
            review = len(df[df['Validation_Status'] == 'Review_Required'])
            unknown = len(df[df['Validation_Status'] == 'Unknown_Species'])
            
            print(f"✓  {f_path.name}: {len(df)} Rufe | V:{verified} R:{review} U:{unknown}")
            
            # Falls die Datei mindestens einen Review-Fall hat -> Kopie in Review-Ordner
            if review > 0 or unknown > 0:
                shutil.copy(f_path, REVIEW_DIR / f_path.name)
            
            all_data.append(df)
            
        except Exception as e:
            print(f"✗  {f_path.name}: Fehler beim Verarbeiten: {e}")
            continue

    if not all_data:
        print("\n✗ Keine Daten verarbeitet!")
        return

    # Gesamte Tabelle speichern
    final_df = pd.concat(all_data, ignore_index=True)
    report_path = OUTPUT_DIR / "validierung_gesamt.csv"
    final_df.to_csv(report_path, index=False)
    print(f"\n✓ Gesamtbericht gespeichert: {report_path}")
    
    # --- VISUALISIERUNG ---
    # Prüfen ob notwendige Spalten vorhanden sind
    if 'duration_ms' in final_df.columns and 'low_freq' in final_df.columns:
        # Zeilen mit fehlenden Werten entfernen für den Plot
        plot_df = final_df.dropna(subset=['duration_ms', 'low_freq'])
        
        if not plot_df.empty and len(plot_df) > 0:
            plt.figure(figsize=(14, 8))
            
            # Scatter Plot
            sns.scatterplot(data=plot_df, 
                          x='duration_ms', 
                          y='low_freq', 
                          hue='Validation_Status', 
                          style='Validation_Status', 
                          s=100,
                          alpha=0.6)
            
            plt.title("NEXUS Validierung: Frequenz vs. Rufdauer", fontsize=14, fontweight='bold')
            plt.xlabel("Rufdauer (ms)", fontsize=12)
            plt.ylabel("Frequenz (Hz)", fontsize=12)
            plt.grid(True, linestyle='--', alpha=0.3)
            plt.tight_layout()
            
            plot_path = OUTPUT_DIR / "analyse_plot.png"
            plt.savefig(plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"✓ Visualisierung gespeichert: {plot_path}")
            
            # Zusätzliche Statistik-Grafik
            fig, axes = plt.subplots(1, 2, figsize=(14, 6))
            
            # Status-Verteilung
            status_counts = final_df['Validation_Status'].value_counts()
            axes[0].pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=90)
            axes[0].set_title('Validierungs-Status Verteilung')
            
            # Top Arten
            if 'class' in final_df.columns:
                top_species = final_df['class'].value_counts().head(10)
                axes[1].barh(range(len(top_species)), top_species.values)
                axes[1].set_yticks(range(len(top_species)))
                axes[1].set_yticklabels([s.replace('Pipistrellus ', 'P. ') for s in top_species.index])
                axes[1].set_xlabel('Anzahl Rufe')
                axes[1].set_title('Top 10 detektierte Arten')
                axes[1].invert_yaxis()
            
            plt.tight_layout()
            stats_path = OUTPUT_DIR / "statistik.png"
            plt.savefig(stats_path, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"✓ Statistik gespeichert: {stats_path}")
            
        else:
            print("⚠ Nicht genug Daten für Visualisierung vorhanden.")
    else:
        print("⚠ Spalten für Visualisierung fehlen (duration_ms und/oder low_freq).")
    
    # --- ABSCHLUSS-STATISTIK ---
    print(f"\n{'='*60}")
    print(f"✓ NEXUS BATCH VALIDATOR - ZUSAMMENFASSUNG")
    print(f"{'='*60}")
    print(f"Gesamtzahl geprüfter Rufe:     {len(final_df):>6}")
    print(f"NEXUS-verifiziert (OK):        {len(final_df[final_df['Validation_Status'] == 'NEXUS_Verified']):>6}")
    print(f"Review erforderlich:           {len(final_df[final_df['Validation_Status'] == 'Review_Required']):>6}")
    print(f"Unbekannte Arten:              {len(final_df[final_df['Validation_Status'] == 'Unknown_Species']):>6}")
    print(f"{'='*60}")
    
    # Top 5 Arten anzeigen
    if 'class' in final_df.columns:
        print("\nTop 5 detektierte Arten:")
        top5 = final_df['class'].value_counts().head(5)
        for species, count in top5.items():
            print(f"  • {species:<35} {count:>5} Rufe")
    
    print(f"\n✓ Ergebnisse in: {OUTPUT_DIR}")
    if len(final_df[final_df['Validation_Status'] != 'NEXUS_Verified']) > 0:
        print(f"⚠ Review-Dateien in: {REVIEW_DIR}")

if __name__ == "__main__":
    main()