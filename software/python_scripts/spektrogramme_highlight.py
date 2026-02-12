#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NEXUS - Data Analysis & Visualization Tool
Teil des NEXUS Fledermaus-Forschungsprojekts

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
Projekt: NEXUS (Environmental Data & Bioacoustics)
Zweck:   Erzeugung wissenschaftlicher Spektrogramme mit BatDetect2-Overlays
         und Rauschreduzierung zur visuellen Analyse.
Version: 1.2.2 (Bugfix: Agg Backend)
Datum:   23.01.2026
"""

import os
import gc
import matplotlib
# WICHTIG: Agg-Backend setzen, bevor pyplot importiert/genutzt wird.
# Verhindert Abstürze ("_idat object has no attribute fileno") bei Batch-Verarbeitung.
matplotlib.use('Agg') 

import librosa
import librosa.display
import matplotlib.pyplot as plt
import noisereduce as nr 
from scipy import signal
import numpy as np
import pandas as pd
from pathlib import Path
from matplotlib.patches import Rectangle
from tqdm import tqdm  # Fortschrittsbalken

# ---------------------------------------------------------
# 1) KONFIGURATION UND PFADE
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = BASE_DIR / "audio"
OUTPUT_DIR = BASE_DIR / "spektrogramme"
BATDETECT_DIR = BASE_DIR / "results" / "individual_detections"

BATDETECT_MIN_CONFIDENCE = 0.8  
HIGHLIGHT_CONFIDENCE_MIN = 0.85
HIGHLIGHT_DIR = OUTPUT_DIR / "highlight"

LOW_FREQ_HZ = 15000     
HIGH_FREQ_HZ = 120000   

# Padding für die Highlight-Boxen
BOX_TIME_PADDING_S = 0.025 
BOX_FREQ_PADDING_HZ = 2000   

OUTPUT_DIR.mkdir(exist_ok=True)
HIGHLIGHT_DIR.mkdir(exist_ok=True) 

processed_files = 0
cleanup_interval = 10 

# ---------------------------------------------------------
# 2) HILFSFUNKTIONEN
# ---------------------------------------------------------

def load_batdetect_csv(filename: str) -> pd.DataFrame | None:
    """
    Lädt die BatDetect2-Ergebnisse (CSV) für eine bestimmte WAV-Datei.
    """
    csv_path = BATDETECT_DIR / (filename + ".csv")  
    if csv_path.exists():  
        try:
            df = pd.read_csv(csv_path)
            required_cols = ['start', 'end', 'low_freq', 'high_freq']
            if not all(col in df.columns for col in required_cols): 
                return None
            df = df.dropna(subset=required_cols).reset_index(drop=True)
            for col in required_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            if 'confidence' in df.columns:
                df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce')
            else:
                df['confidence'] = np.nan
            df = df.dropna(subset=required_cols)
            if df.empty: 
                return None
            return df
        except Exception as e:
            return None
    return None

def plot_and_save_spectrogram(ydata: np.ndarray, sr: int, spec_db: np.ndarray, hop_length: int,
                             output_filepath: Path, detections: pd.DataFrame | None = None,
                             fmin: int = LOW_FREQ_HZ, fmax: int = HIGH_FREQ_HZ, dpi: int = 300,
                             plot_detections: bool = True):
    """
    Erstellt und speichert ein Spektrogramm, optional mit BatDetect2-Detektionen.
    """
    # Neue Figure erstellen (durch Agg Backend sicher im Hintergrund)
    fig = plt.figure(figsize=(16, 6))
    
    librosa.display.specshow(spec_db, sr=sr, hop_length=hop_length, x_axis='time', y_axis='linear', cmap='magma', vmin=-120, vmax=-55)
    plt.ylim(fmin, fmax)
    ticks = np.arange(fmin, fmax + 1, 10000)
    plt.yticks(ticks, labels=[str(int(f/1000)) for f in ticks])
    plt.ylabel("Frequenz (kHz)")
    plt.colorbar(label='Amplitude (dB)')
    title_base = output_filepath.stem.replace('_spektrogramm_full', '').replace('_spektrogramm_zoom', '').replace('_spektrogramm_clean', '')
    plt.title(f"Spektrogramm: {title_base} (SR: {sr} Hz)")
    
    duration = len(ydata) / sr
    plt.xlim(0, duration)

    if plot_detections and detections is not None and not detections.empty:
        if 'confidence' in detections.columns:
            filtered_detections = detections[detections['confidence'] >= BATDETECT_MIN_CONFIDENCE]
            if not filtered_detections.empty:
                for index, row in filtered_detections.iterrows():
                    start = row["start"]; end = row["end"]; f_low = row["low_freq"]; f_high = row["high_freq"]
                    
                    if pd.notna(f_high) and pd.notna(f_low) and f_high >= fmin and f_low <= fmax and end >= plt.xlim()[0] and start <= plt.xlim()[1]:
                        species = row.get("species", "Unbekannt"); conf = row.get("confidence", np.nan)
                        edge_color = 'yellow' if pd.notna(conf) and conf >= HIGHLIGHT_CONFIDENCE_MIN else 'red'
                        
                        pad_f_low = max(fmin, f_low - BOX_FREQ_PADDING_HZ)
                        pad_f_high = min(fmax, f_high + BOX_FREQ_PADDING_HZ)
                        pad_time_start = max(0, start - BOX_TIME_PADDING_S)
                        pad_time_end = min(duration, end + BOX_TIME_PADDING_S)

                        pad_width = pad_time_end - pad_time_start
                        pad_height = pad_f_high - pad_f_low

                        rect = plt.Rectangle((pad_time_start, pad_f_low), pad_width, pad_height,
                                             linewidth=1.5, edgecolor=edge_color, facecolor='none', zorder=10)
                        plt.gca().add_patch(rect)
                        
                        if species != "Unbekannt":
                            text_conf = f" ({conf:.2f})" if pd.notna(conf) else ""; 
                            text_y_pos = min(pad_f_high + 2000, fmax - 1000) 
                            plt.text(pad_time_start, text_y_pos, f"{species}{text_conf}", 
                                     color=edge_color, fontsize=8, ha='left', va='bottom', rotation=45) 

    # Fix: Umwandlung in String erzwingen, um Path-Objekt Probleme mit PIL zu vermeiden
    plt.savefig(str(output_filepath), dpi=dpi, bbox_inches='tight')
    plt.close(fig) # Explizit die Figure schließen

# ---------------------------------------------------------
# 3) HAUPTPROGRAMM
# ---------------------------------------------------------
def main():
    global processed_files
    print(f"Starte Spektrogramm-Generierung. Eingangsverzeichnis: {INPUT_DIR}")
    print(f"Filter- und Plot-Bereich: {LOW_FREQ_HZ/1000:.0f} kHz bis {HIGH_FREQ_HZ/1000:.0f} kHz")
    print("!!! Rauschunterdrückung DEAKTIVIERT. NUR _full.png wird gespeichert. !!!")

    wav_files = list(INPUT_DIR.glob("*.wav"))
    
    for wav_path in tqdm(wav_files, desc="Fortschritt", unit="Datei"):
        filename = wav_path.name
        output_base = OUTPUT_DIR / wav_path.stem
        
        try:
            # tqdm.write für sauberen Output
            # tqdm.write(f"Verarbeite: {filename}") # Optional: Auskommentieren für weniger Text
            
            y, sr = librosa.load(wav_path, sr=None, mono=True)
            
            b, a = signal.butter(5, [LOW_FREQ_HZ, HIGH_FREQ_HZ], btype='bandpass', fs=sr)
            y_filtered = signal.filtfilt(b, a, y)
            y_reduced = y_filtered 
            
            ziel_frequenzaufloesung = 187.5 
            n_fft_float = sr / ziel_frequenzaufloesung
            n_fft = int(2**(np.ceil(np.log2(n_fft_float)))) 
            hop_length = n_fft // 4 
            
            spec = librosa.stft(y_reduced, n_fft=n_fft, hop_length=hop_length)
            spec_db = librosa.amplitude_to_db(np.abs(spec), ref=32768.0) 
            
            detections = load_batdetect_csv(filename)
            should_save_highlight = False
            
            if detections is not None and not detections.empty:
                filtered_detections = detections[detections['confidence'] >= BATDETECT_MIN_CONFIDENCE]
                highlight_detections = detections[detections['confidence'] >= HIGHLIGHT_CONFIDENCE_MIN]
                if not highlight_detections.empty:
                    should_save_highlight = True
                
                if not filtered_detections.empty:
                    output_path_full = output_base.with_name(f"{output_base.name}_spektrogramm_full.png")

                    plot_and_save_spectrogram(y_reduced, sr, spec_db, hop_length, output_path_full, detections, fmin=LOW_FREQ_HZ, fmax=HIGH_FREQ_HZ, plot_detections=True)
                    
                    if should_save_highlight:
                        highlight_base = HIGHLIGHT_DIR / wav_path.stem
                        highlight_path_full = highlight_base.with_name(f"{highlight_base.name}_spektrogramm_full.png")
                        plot_and_save_spectrogram(y_reduced, sr, spec_db, hop_length, highlight_path_full, detections, fmin=LOW_FREQ_HZ, fmax=HIGH_FREQ_HZ, plot_detections=True)
                        tqdm.write(f"-> {filename}: Full & Highlight gespeichert. 🏆")
                    else:
                        tqdm.write(f"-> {filename}: Full gespeichert.")

                else:
                    # Optional: Zeile auskommentieren, wenn "Übersprungen" nicht angezeigt werden soll
                    # tqdm.write(f"-> {filename}: Übersprungen (Konfidenz zu niedrig).")
                    pass
            else:
                # tqdm.write(f"-> {filename}: Übersprungen (keine Detektionen).")
                pass

            del y, y_filtered, y_reduced, spec, spec_db, b, a
            if detections is not None: del detections
            
            processed_files += 1
            if processed_files % cleanup_interval == 0:
                # tqdm.write("🧹 Cleanup...")
                gc.collect()

        except FileNotFoundError:
            tqdm.write(f"❌ Datei nicht gefunden: {wav_path}")
        except Exception as e:
            tqdm.write(f"❌ Fehler bei {filename}: {e}")

    print(f"\n✅ Fertig! Alle Spektrogramme wurden in {OUTPUT_DIR} gespeichert.")

if __name__ == "__main__":
    main()