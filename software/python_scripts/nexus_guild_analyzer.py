#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NEXUS GUILD ANALYZER - Version 1.7 (Track Visualization Edition)
Part of the NEXUS Bat Research Project

SPDX-FileCopyrightText: 2026 Jochen Roth
SPDX-License-Identifier: CC-BY-NC-4.0
---------------------------------------------------------------------
Copyright (C) 2026 Jochen Roth

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
Purpose: Analysis of ecological guilds and GPS track visualization.
         / Analyse der ökologischen Gilden und Visualisierung des GPS-Pfads.
Version: 1.7.0
Date:    23.01.2026
---------------------------------------------------------------------
FEAT: Added Page 2 to PDF report showing the GPS track (Latitude/Longitude).
      / Seite 2 zum PDF-Bericht hinzugefügt, die den GPS-Pfad zeigt.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os
import glob

def calculate_alpha_iso(f, T_c, rh, pa_hpa):
    """
    Calculates attenuation in dB/m according to ISO 9613-1.
    Berechnet Schalldämpfung in dB/m nach ISO 9613-1.
    """
    if pa_hpa <= 0: pa_hpa = 1013.25
    pr, T, Tr = 1013.25, T_c + 273.15, 293.15
    p_sat_pr = 10**(-6.8346 * (273.16 / T)**1.261 + 4.6151)
    h = rh * p_sat_pr * (pa_hpa / pr)
    frO = (pa_hpa / pr) * (24.0 + 4.04e4 * h * (0.02 + h) / (0.391 + h))
    frN = (pa_hpa / pr) * (T / Tr)**-0.5 * (9.0 + 280.0 * h * np.exp(-4.170 * ((T / Tr)**(-1/3) - 1.0)))
    alpha = f**2 * (
        1.84e-11 * (pa_hpa / pr)**-1.0 * (T / Tr)**0.5 +
        (T / Tr)**-2.5 * (
            0.01275 * np.exp(-2239.1 / T) / (frO + f**2 / frO) +
            0.1068 * np.exp(-3352.0 / T) / (frN + f**2 / frN)
        )
    )
    return alpha * 20.0 * np.log10(np.exp(1))

def analyze_bat_range():
    data_dir = r"C:\fledermaus\nexus-data"
    report_dir = r"C:\fledermaus\nexus-reports"
    
    if not os.path.exists(report_dir): os.makedirs(report_dir)

    # Search for CSV files / Suche nach CSV-Dateien
    files = glob.glob(os.path.join(data_dir, "*.csv")) + glob.glob(os.path.join(data_dir, "*.CSV"))
    if not files: 
        print("Logikfehler: Keine Eingabedaten im Verzeichnis gefunden.")
        return
    
    # Select the newest file / Die zeitlich neueste Datei auswählen
    latest_file = max(files, key=os.path.getmtime)
    print(f"Analysiere Messreihe: {os.path.basename(latest_file)}")
    
    df = pd.read_csv(latest_file)
    if df.empty: return
    
    # --- PREPARE DATA FOR PAGE 1 (LATEST SNAPSHOT) ---
    latest_data = df.iloc[-1].to_dict()
    
    temp = latest_data.get('Temp', 20.0)
    hum = latest_data.get('Hum', 50.0)
    pres = latest_data.get('Pres', 1013.25)
    
    guild_freqs = {
        'Low (20kHz)': 20000.0, 'Mid (40kHz)': 40000.0,
        'High (55kHz)': 55000.0, 'FM-Spec (80kHz)': 80000.0,
        'CF-Spec (110kHz)': 110000.0
    }

    guild_values = {}
    mapping = {'Low (20kHz)': 'a20k_Low', 'Mid (40kHz)': 'a40k_Mid', 'High (55kHz)': 'a55k_High', 'FM-Spec (80kHz)': 'a80k_FM', 'CF-Spec (110kHz)': 'a110k_CF'}

    for name, freq in guild_freqs.items():
        col = mapping[name]
        if col in latest_data:
            guild_values[name] = latest_data[col]
        else:
            guild_values[name] = calculate_alpha_iso(freq, temp, hum, pres)

    # --- PREPARE DATA FOR PAGE 2 (GPS TRACK) ---
    # Filter out invalid GPS data (0.0 or NaN)
    # Filtere ungültige GPS-Daten heraus (0.0 oder NaN)
    gps_track = df.copy()
    if 'Lat' in gps_track.columns and 'Lon' in gps_track.columns:
        gps_track = gps_track[
            (gps_track['Lat'].notna()) & (gps_track['Lon'].notna()) &
            (gps_track['Lat'] != 0) & (gps_track['Lon'] != 0)
        ]
    else:
        gps_track = pd.DataFrame()

    # --- GENERATE PDF REPORT ---
    base_name = os.path.splitext(os.path.basename(latest_file))[0]
    pdf_filename = os.path.join(report_dir, f"Report_{base_name}.pdf")
    
    with PdfPages(pdf_filename) as pdf:
        
        # === PAGE 1: ATTENUATION / DÄMPFUNG ===
        fig1, ax1 = plt.subplots(figsize=(11.69, 8.27)) # A4 Landscape
        distances = np.linspace(1, 60, 120)
        
        for name, alpha in guild_values.items():
            total_att = 20 * np.log10(distances) + (alpha * distances)
            ax1.plot(distances, total_att, label=f"{name} (α={alpha:.3f} dB/m)", linewidth=2.5)

        ax1.axhline(y=55, color='r', linestyle='--', label='Detektionslimit (55dB)')
        ax1.invert_yaxis()
        ax1.set_title(f"NEXUS ATMOSPHERICS v1.7 - PAGE 1/2\nDatei: {os.path.basename(latest_file)}")
        ax1.set_xlabel("Distanz (m)")
        ax1.set_ylabel("Totale Dämpfung (dB)")
        ax1.legend(loc='upper right')
        ax1.grid(True, linestyle=':', alpha=0.6)
        
        info_text = (f"Metadaten (Endpunkt):\n"
                     f"Temp: {temp}°C | Hum: {hum}% | Pres: {pres} hPa\n"
                     f"GPS: {latest_data.get('Lat','0.0')}, {latest_data.get('Lon','0.0')}\n"
                     f"Modus: {latest_data.get('Modus','--')} | Cloud: {latest_data.get('Bewolkung','?')}/8")
        plt.figtext(0.15, 0.02, info_text, fontsize=10, bbox=dict(facecolor='white', alpha=0.5))
        
        pdf.savefig(fig1)
        plt.close(fig1)

        # === PAGE 2: GPS TRACK / GPS STRECKE ===
        if not gps_track.empty:
            fig2, ax2 = plt.subplots(figsize=(11.69, 8.27))
            
            # Plot the path line / Pfadlinie zeichnen
            ax2.plot(gps_track['Lon'], gps_track['Lat'], color='blue', alpha=0.6, linewidth=2, label='Track')
            
            # Mark Start (Green) and End (Red) / Start (Grün) und Ende (Rot) markieren
            start_pt = gps_track.iloc[0]
            end_pt = gps_track.iloc[-1]
            
            ax2.scatter(start_pt['Lon'], start_pt['Lat'], color='green', s=100, label='Start', zorder=5)
            ax2.scatter(end_pt['Lon'], end_pt['Lat'], color='red', s=100, label='Ende', zorder=5)
            
            # Formatting / Formatierung
            ax2.set_title(f"NEXUS GPS TRACK v1.7 - PAGE 2/2\n{os.path.basename(latest_file)}")
            ax2.set_xlabel("Longitude")
            ax2.set_ylabel("Latitude")
            ax2.legend()
            ax2.grid(True, linestyle='--', alpha=0.5)
            
            # Ensure map aspect ratio is not distorted / Sicherstellen, dass Kartenverhältnis nicht verzerrt ist
            ax2.set_aspect('equal', adjustable='datalim')

            # Add stats / Statistiken hinzufügen
            track_info = (f"Track Statistik:\n"
                          f"Punkte: {len(gps_track)}\n"
                          f"Startzeit: {gps_track.iloc[0].get('Time', 'N/A')}\n"
                          f"Endzeit:   {gps_track.iloc[-1].get('Time', 'N/A')}")
            plt.figtext(0.15, 0.02, track_info, fontsize=10, bbox=dict(facecolor='white', alpha=0.5))
            
            pdf.savefig(fig2)
            plt.close(fig2)
        else:
            print("Keine validen GPS-Daten für Seite 2 gefunden.")

    print(f"Analyse erfolgreich. PDF (2 Seiten) archiviert unter: {pdf_filename}")

if __name__ == "__main__":
    analyze_bat_range()