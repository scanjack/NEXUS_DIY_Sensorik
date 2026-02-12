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
Purpose: Pareto analysis of species distribution to identify ecological 
         dominance in the survey data.
         / Pareto-Analyse der Artenverteilung zur Identifizierung der 
         ökologischen Dominanz in den Erfassungsdaten.
Version: 1.1.0
Date:    15.01.2026
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path

# ---------------------------------------------------------
# Define paths (platform independent) /
# Pfade definieren (plattformunabhängig)
# ---------------------------------------------------------
BASE_DIR = Path(r"C:\Fledermaus")  # Fixed base folder / fester Basisordner
csv_pfad = BASE_DIR / "results" / "species_summary.csv"
output_path = BASE_DIR / "results" / "pareto_analysis.png"

# ---------------------------------------------------------
# Read CSV file / CSV-Datei einlesen
# ---------------------------------------------------------
print(f"Lese Daten ein von: {csv_pfad}")
try:
    df = pd.read_csv(csv_pfad, index_col=0)
    # If column names are missing, correct them (safeguard) /
    # Falls Spaltennamen fehlen, korrigieren (Sicherung)
    if df.shape[1] == 1 and df.columns[0] != 'Count':
        df.columns = ['Count']
except FileNotFoundError:
    print(f"❌ Fehler: Datei nicht gefunden unter:\n{csv_pfad}")
    print("Bitte überprüfe, ob bat_summary.py erfolgreich ausgeführt wurde und die Datei existiert.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Fehler beim Lesen der CSV-Datei: {e}")
    sys.exit(1)

# Check if data is present / Prüfen, ob Daten vorhanden sind
if df.empty or 'Count' not in df.columns:
    print("❌ Fehler: Die CSV-Datei ist leer oder enthält keine 'Count'-Spalte.")
    sys.exit(1)

# ---------------------------------------------------------
# Calculate Pareto analysis / Pareto-Analyse berechnen
# ---------------------------------------------------------
df = df.sort_values(by='Count', ascending=False)
df['Cumulative_Count'] = df['Count'].cumsum()
total_count = df['Count'].sum()

if total_count == 0:
    print("❌ Fehler: Die Gesamtzahl der Rufe ist Null. Keine Pareto-Analyse möglich.")
    sys.exit(1)
    
df['Cumulative_Percentage'] = (df['Cumulative_Count'] / total_count) * 100

# ---------------------------------------------------------
# Determine marker position for 80% limit /
# Marker-Position für 80%-Limit bestimmen
# ---------------------------------------------------------
# Find the index (species name) of the first species crossing the 80% mark /
# Finde den Index (Artennamen) der ersten Art, die die 80%-Marke überschreitet
try:
    pareto_limit_index = df[df['Cumulative_Percentage'] >= 80].index[0]
    # Determine numeric position (for the vertical line) /
    # Bestimme die numerische Position (für die vertikale Linie)
    pareto_limit_pos = df.index.get_loc(pareto_limit_index) + 0.5 
except:
    # If 80% is never reached (e.g. only 1 species), set marker to end /
    # Falls 80% nie erreicht wird (z.B. nur 1 Art), setzen wir den Marker ans Ende
    pareto_limit_pos = len(df.index)

# ---------------------------------------------------------
# Create Plot / Plot erstellen
# ---------------------------------------------------------
fig, ax1 = plt.subplots(figsize=(12, 7))

# Bar chart for absolute frequencies / Balkendiagramm für absolute Häufigkeiten
ax1.bar(df.index, df['Count'], color='skyblue')
ax1.set_xlabel('Fledermausart')
ax1.set_ylabel('Anzahl Rufe', color='skyblue')
ax1.tick_params(axis='y', labelcolor='skyblue')
plt.xticks(rotation=45, ha='right')

# Vertical line separating species (fulfilling 80%) /
# Vertikale Linie, die die Arten trennt (die 80% erfüllen)
if pareto_limit_pos <= len(df.index):
    # -0.5 because the bar is centered, we want the line between bars /
    # -0.5, da der Balken zentriert ist, wir wollen die Linie zwischen den Balken
    ax1.axvline(pareto_limit_pos - 0.5, color='darkgreen', linestyle=':', linewidth=2, label='80%-Limit (Arten)')
    
# Second y-axis for cumulative percentage /
# Zweite y-Achse für kumulierten Prozentanteil
ax2 = ax1.twinx()
ax2.plot(df.index, df['Cumulative_Percentage'], color='red', marker='o', zorder=10) # High Z-order for visibility / Z-Order hoch für Sichtbarkeit
ax2.set_ylabel('Kumulierter Anteil (%)', color='red')
ax2.tick_params(axis='y', labelcolor='red')
ax2.axhline(80, color='gray', linestyle='--', label='80%-Marke')
ax2.set_ylim(0, 105) # Set axis to 105% for better spacing / Achse auf 105% setzen für besseren Abstand

# Title, Legend & Layout / Titel, Legende & Layout
plt.title('Pareto-Analyse der Fledermausrufe', fontsize=14)
# Combined Legend / Kombinierte Legende
lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax2.legend(lines + lines2, labels + labels2, loc='upper left')

fig.tight_layout()

# ---------------------------------------------------------
# Save graphic / Grafik speichern
# ---------------------------------------------------------
output_path.parent.mkdir(exist_ok=True)
plt.savefig(output_path, dpi=300)
plt.close()

print(f"✅ Pareto-Analyse erfolgreich gespeichert unter:\n{output_path}")