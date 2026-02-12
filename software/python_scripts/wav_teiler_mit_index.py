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
Purpose: Segmentation of TeensyBat recordings (30s) into 2s blocks 
         for BatDetect2 including index generation.
         / Segmentierung von TeensyBat-Aufnahmen (30s) in 2s-Blöcke 
         für BatDetect2 inklusive Index-Generierung.
Version: 1.0.2 (Progress Bar Update)
Date:    15.01.2026
"""

import soundfile as sf
from pathlib import Path
import pandas as pd
import math
from tqdm import tqdm  # Progress bar library / Fortschrittsbalken-Bibliothek

# **********************************************************
# * PLATFORM INDEPENDENT DEFINITION OF ABSOLUTE PATHS /
# * PLATFORMUNABHÄNGIGE DEFINITION DER ABSOLUTEN PFADE
# **********************************************************
# The main directory where this script is located (e.g. C:\Fledermaus) /
# Das Hauptverzeichnis, in dem dieses Skript liegt (z.B. C:\Fledermaus)
BASE_DIR = Path(__file__).resolve().parent

# The input and output folders (now as Path objects) /
# Die Eingabe- und Ausgabe-Ordner (jetzt als Path-Objekte)
input_path_abs = BASE_DIR / "audio_work"
output_path_abs = BASE_DIR / "audio"

# --- CONFIGURATION / NEUE KONFIGURATION ---
SEGMENT_LENGTH_SEC = 2  # LENGTH OF WAVE PARTS / LÄNGE DER WAVE-TEILE
# -------------------------

# List to save the index data / Liste zum Speichern der Index-Daten
segment_list = []

# Create output directory, if it does not exist / 
# Ausgabe-Verzeichnis erstellen, falls es nicht existiert
output_path_abs.mkdir(parents=True, exist_ok=True)

# Generate list of files first to allow tqdm to show total progress /
# Dateiliste zuerst generieren, damit tqdm den Gesamtfortschritt anzeigen kann
wav_files = list(input_path_abs.glob("*.wav"))

print(f"Starte Segmentierung in {SEGMENT_LENGTH_SEC}s-Teile...")
print(f"Eingabe: {input_path_abs}")
print(f"Ausgabe: {output_path_abs}")
print(f"Gefundene Dateien: {len(wav_files)}\n")

if not wav_files:
    print("⚠️ Keine WAV-Dateien im Eingabeordner gefunden.")
else:
    # Iterate through all WAV files using tqdm for progress bar / 
    # Iteriere durch alle WAV-Dateien mit tqdm für den Fortschrittsbalken
    for input_file in tqdm(wav_files, desc="Segmentierung", unit="File", ncols=100):

        base_name = input_file.stem  # filename without .wav / dateiname ohne .wav

        try:
            # Load audio file / Audio-Datei laden
            y, sr = sf.read(input_file)
            duration = len(y) / sr
            
            # Calculate number of segments (round up) / 
            # Berechnung der Anzahl der Segmente (aufrunden)
            num_segments = math.ceil(duration / SEGMENT_LENGTH_SEC)

            # Use tqdm.write instead of print to not break the progress bar layout /
            # Nutze tqdm.write statt print, um das Layout des Balkens nicht zu zerstören
            # tqdm.write(f" -> {input_file.name} ({duration:.1f}s) -> {num_segments} Teile")

            # Split audio into segments / Audio in Segmente aufteilen
            for i in range(num_segments):
                # Use SEGMENT_LENGTH_SEC for correct calculation / 
                # Nutze SEGMENT_LENGTH_SEC für die korrekte Berechnung
                start_time_sec = i * SEGMENT_LENGTH_SEC
                start_sample = start_time_sec * sr
                end_sample = min((i + 1) * SEGMENT_LENGTH_SEC * sr, len(y))
                segment = y[int(start_sample):int(end_sample)]
                
                # Segment information / Segment-Informationen
                segment_duration = len(segment) / sr
                
                # Save segment / Segment speichern
                # The file format must be chosen so BatDetect2 can process it /
                # Das Dateiformat muss so gewählt werden, dass BatDetect2 es verarbeiten kann
                output_filename = f"{base_name}_seg{i+1:03d}.wav" 
                output_path = output_path_abs / output_filename
                
                sf.write(output_path, segment, sr)
                
                # Create index entry / Index-Eintrag erstellen
                segment_list.append({
                    "original_filename": input_file.name,
                    "segment_filename": output_filename,
                    "segment_number": i + 1,
                    "segment_start_sec": start_time_sec,
                    "segment_duration_sec": segment_duration
                })
                
        except Exception as e:
            tqdm.write(f"❌ [FEHLER] Fehler bei Verarbeitung von {input_file.name}: {e}")
            continue

    # --- CREATE SEGMENT INDEX / ERSTELLEN DES SEGMENT-INDEX ---
    if segment_list:
        df_index = pd.DataFrame(segment_list)
        output_index_path = BASE_DIR / "segment_index.csv"
        df_index.to_csv(output_index_path, index=False)
        print(f"\n✅ Segment-Index erfolgreich erstellt: {output_index_path.name}")
        print(f"Insgesamt {len(df_index)} Segmente erzeugt.")