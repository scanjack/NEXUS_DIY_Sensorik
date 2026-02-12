#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NEXUS - Data Analysis & Visualization Tool
Part of the NEXUS Bat Research Project

SPDX-FileCopyrightText: 2025-2026 Jochen Roth
SPDX-License-Identifier: GPL-3.0-or-later
---------------------------------------------------------------------
Copyright (C) 2025-2026 Jochen Roth

Dieses Programm ist freie Software: Sie können es unter den Bedingungen 
der GNU General Public License, wie von der Free Software Foundation 
veröffentlicht, weitergeben und/oder modifizieren; entweder gemäß 
Version 3 der Lizenz oder (nach Ihrer Option) jeder späteren Version.

Dieses Programm wird in der Hoffnung verbreitet, dass es nützlich sein wird, 
aber OHNE JEDE GEWÄHRLEISTUNG; sogar ohne die implizite Gewährleistung der 
MARKTFÄHIGKEIT oder EIGNUNG FÜR EINEN BESTIMMTEN ZWECK. 
Siehe die GNU General Public License für weitere Details: 
<https://www.gnu.org/licenses/gpl-3.0.html>
---------------------------------------------------------------------
Projekt: NEXUS (Environmental Data & Bioacoustics)
Zweck:   Automatisierte Anomalie-Erkennung und Hinweis auf manuelle Prüfung.
Version: 2.8.0
Datum:   13.01.2026
"""

import os
import gc
import librosa
import librosa.display
import matplotlib.pyplot as plt
import noisereduce as nr 
from scipy import signal
import numpy as np
import pandas as pd
from pathlib import Path
from matplotlib.patches import Rectangle 
import soundfile as sf

# ---------------------------------------------------------
# 1) KONFIGURATION
# ---------------------------------------------------------
plt.style.use('dark_background') 

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "audio_work"
OUTPUT_DIR = BASE_DIR / "spektrogramme" / "nexus"
MASTER_DATA_FILE = BASE_DIR / "master_data_ALL_FINAL.csv"
FREQ_REF_FILE = BASE_DIR / "Frequenzen.csv" 

SR_TARGET = 384000 
N_FFT = 2048
HOP_LENGTH = 512

# ---------------------------------------------------------
# 2) ANALYSE-ROUTINEN
# ---------------------------------------------------------

def estimate_max_range(alpha_db_m):
    if alpha_db_m is None or pd.isna(alpha_db_m) or alpha_db_m <= 0:
        return "N/A"
    available_range = 80 
    for r in range(1, 150):
        tl = 20 * np.log10(r) + (alpha_db_m * r)
        if tl > available_range:
            return f"ca. {r}m"
    return "> 150m"

def get_peak_frequency(spec_db, sr):
    freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
    idx = np.unravel_index(np.argmax(spec_db, axis=None), spec_db.shape)
    return freqs[idx[0]] / 1000 # kHz

def load_resources():
    ref_db = None
    master_df = None
    if FREQ_REF_FILE.exists():
        ref_db = pd.read_csv(FREQ_REF_FILE).dropna(subset=['Art'])
    if MASTER_DATA_FILE.exists():
        master_df = pd.read_csv(MASTER_DATA_FILE).set_index('filename')
    return ref_db, master_df

def get_species_details(species_name, ref_db):
    if ref_db is None or pd.isna(species_name) or species_name == "Unklassifiziert":
        return None
    match = ref_db[ref_db['Art'].str.contains(species_name, case=False, na=False)]
    if not match.empty:
        row = match.iloc[0]
        return {
            'f_min': float(row['Hauptfrequenz_min kHz']),
            'f_max': float(row['Hauptfrequenz_max kHz']),
            'name_de': row['Art'].split('(')[0].strip(),
            'gilde': row.get('Umgebung', 'Nicht definiert')
        }
    return None

# ---------------------------------------------------------
# 3) VISUALISIERUNG & LOGIK-KNOTEN
# ---------------------------------------------------------

def create_nexus_visual(wav_path, ref_db, nexus_row):
    try:
        data, sr_orig = sf.read(wav_path)
        if len(data.shape) > 1: data = np.mean(data, axis=1)
        y = librosa.resample(data, orig_sr=sr_orig, target_sr=SR_TARGET) if sr_orig != SR_TARGET else data
        
        y_filt = signal.filtfilt(*signal.butter(4, 15000 / (0.5 * SR_TARGET), btype='high'), y)
        y_clean = nr.reduce_noise(y=y_filt, sr=SR_TARGET, stationary=False, prop_decrease=0.7, freq_mask_smooth_hz=1000)
        
        spec_db = librosa.amplitude_to_db(np.abs(librosa.stft(y_clean, n_fft=N_FFT, hop_length=HOP_LENGTH)), ref=np.max)
        measured_peak_khz = get_peak_frequency(spec_db, SR_TARGET)
        
        fig, ax = plt.subplots(figsize=(16, 9))
        img = librosa.display.specshow(spec_db, sr=SR_TARGET, x_axis='time', y_axis='linear', 
                                       cmap='magma', ax=ax, fmin=15000, fmax=135000)
        
        fig.colorbar(img, ax=ax, format="%+2.0f dB").set_label('Amplitude (dB)')

        species = nexus_row.get('species_classified', 'Unbekannt')
        details = get_species_details(species, ref_db)
        
        status_color = "yellow"
        manual_check_hint = ""
        
        if details:
            ax.axhspan(details['f_min']*1000, details['f_max']*1000, color='green', alpha=0.15)
            
            # Logik-Check: Liegt der Peak im Toleranzbereich?
            if details['f_min'] <= measured_peak_khz <= details['f_max']:
                status_color = "lime"
            else:
                status_color = "orange"
                # Änderung 2.8.0: Ergänzung des Hinweises bei Anomalien
                manual_check_hint = "\n>>> PLEASE CHECK MANUALLY <<<"

        alpha = nexus_row.get('a40k_Mid')
        range_est = estimate_max_range(alpha)

        # INFO-BOX AUFBAU
        nexus_info = (
            f"ID: {wav_path.name}\n"
            f"ART: {species}\n"
            f"PEAK: {measured_peak_khz:.2f} kHz\n"
            f"---------------------------\n"
            f"NEXUS TELEMETRIE:\n"
            f"Temp: {nexus_row.get('Temp')}°C | Hum: {nexus_row.get('Hum')}% rH\n"
            f"Absorption: {alpha} dB/m\n"
            f"Reichweite (40k): {range_est}\n"
            f"Mond: Elev. {nexus_row.get('moon_elevation', 0):.1f}°"
            f"{manual_check_hint}" # Wird nur bei Abweichung angezeigt
        )
        
        ax.text(0.02, 0.97, nexus_info, transform=ax.transAxes, color=status_color, 
                fontsize=10, verticalalignment='top', family='monospace',
                bbox=dict(facecolor='black', alpha=0.85, edgecolor=status_color, lw=1.5))

        plt.title(f"NEXUS Research Analysis V2.8.0", color='white', pad=20)
        plt.savefig(OUTPUT_DIR / f"{wav_path.stem}_v28.png", dpi=200, bbox_inches='tight')
        plt.close()
        
    except Exception as e:
        print(f"❌ Fehler bei {wav_path.name}: {e}")

def main():
    print("Vulkanische Logik initiiert. Anomalie-Detektor Version 2.8.0 aktiv.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ref_db, master_df = load_resources()
    wav_files = list(INPUT_DIR.glob("*.wav"))
    for wav_path in wav_files:
        if master_df is not None and wav_path.name in master_df.index:
            nexus_row = master_df.loc[wav_path.name]
            if isinstance(nexus_row, pd.DataFrame): nexus_row = nexus_row.iloc[0]
            create_nexus_visual(wav_path, ref_db, nexus_row)
        gc.collect()

if __name__ == "__main__":
    main()