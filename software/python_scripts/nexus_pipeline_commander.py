#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NEXUS - Master Pipeline Commander (Full Visual Suite)
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
Purpose: Fully automated orchestration of ALL 13 analysis modules
         incl. dynamic threshold and power management.
         / Vollautomatische Orchestrierung ALLER 13 Analyse-Module
         inkl. dynamischem Threshold und Power-Management.
Version: 2.5.1
Date:    15.01.2026
"""

import subprocess
import sys
import time
from pathlib import Path

# **********************************************************
# * CONFIGURATION / KONFIGURATION
# **********************************************************
BASE_DIR = Path(r"C:\Fledermaus")

# CENTRAL VARIABLE FOR YOUR RESEARCH / ZENTRALE VARIABLE FÜR DEINE FORSCHUNG
# Change value here - automatically applied to code and display. /
# Hier den Wert ändern – er wird automatisch in Code und Anzeige übernommen.
BAT_THRESHOLD = "0.8" 

# Windows Power Plan GUIDs (Standard Microsoft IDs) /
# Windows Energie-Plan GUIDs (Standard-IDs von Microsoft)
PLAN_HIGH_PERFORMANCE = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
PLAN_BALANCED         = "381b4222-f694-41f0-9685-ff5bb260df2e"

# The complete, logical sequence of the research pipeline /
# Die vollständige, logische Sequenz der Forschungspipeline
PIPELINE_SEQUENCE = [
    ("wav_teiler_mit_index.py",           "Segmentierung der TeensyBat-Aufnahmen"),
    ("BATDETECT2_CLI",                    "BatDetect2: KI-Klassifizierung (Threshold {BAT_THRESHOLD})"),  
    ("batch-validator.py",                "Physikalische Frequenz-Validierung & Cluster-Grafiken"),
    ("bat_autostart_final.py",            "Zeitstempel-Rekonstruktion & Astro-Daten"),
    ("bat_summary.py",                    "Statistische Aggregation der Ergebnisse"),
    ("bat_activity.py",                   "Erstellung der Aktivitätsdiagramme"),
    ("create_bat_graphics_path_fixed.py", "Qualitätssicherung & Statistik-Grafiken"),
    ("pareto_fledermaus.py",              "Pareto-Analyse der Artenverteilung"),
    ("nexus_guild_analyzer.py",           "Nexus: Atmosphärische Reichweiten-Analyse (ISO)"),
    ("final_3way_merge.py",               "Finaler Daten-Merge (Umwelt & Akustik)"),
    ("spektrogramme_highlight.py",        "Erzeugung der Highlight-Spektrogramme (Overlays)"),
    ("spektrogramme_nexus.py",            "Erzeugung der Nexus-Umwelt-Spektrogramme"),  
    ("create_kml_filtered.py",            "Geografische Visualisierung (KML-Export)")
]

def set_power_plan(plan_guid):
    """
    Switches the Windows power plan via powercfg.
    Schaltet den Windows-Energiesparplan via powercfg um.
    """
    try:
        subprocess.run(["powercfg", "/setactive", plan_guid], check=True, capture_output=True)
        mode = "HÖCHSTLEISTUNG" if plan_guid == PLAN_HIGH_PERFORMANCE else "AUSBALANCIERT"
        print(f"--> [POWER] System-Modus auf {mode} gesetzt.")
    except Exception as e:
        print(f"⚠️  [WARNUNG] Konnte Energieplan nicht ändern: {e}")

def run_batdetect2_cli():
    """
    Starts BatDetect2 with the centrally configured threshold.
    Startet BatDetect2 mit dem zentral konfigurierten Threshold.
    """
    print(f"--> [EXEC] Starte BatDetect2 (KI-Engine) mit Threshold {BAT_THRESHOLD}...")
    cmd = [
        sys.executable, "-m", "batdetect2.cli", "detect",
        str(BASE_DIR / "audio"),
        str(BASE_DIR / "anns"),
        BAT_THRESHOLD
    ]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def run_python_script(script_name, description):
    """
    Executes a Python module from the NEXUS directory.
    Führt ein Python-Modul aus dem NEXUS-Verzeichnis aus.
    """
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        print(f"⚠️  [ÜBERSPRUNGEN] Skript nicht im Verzeichnis: {script_name}")
        return True 
    
    print(f"--> [EXEC] {description}...")
    try:
        subprocess.run([sys.executable, str(script_path)], check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"🛑 [FEHLER] Abbruch in Modul: {script_name}")
        return False

def main():
    print("========================================================")
    print("   NEXUS MASTER PIPELINE COMMANDER - v2.5.1")
    print("========================================================")
    print(f"Startzeit: {time.strftime('%H:%M:%S')} | Threshold: {BAT_THRESHOLD}")
    
    # 1. Power to maximum for computational load /
    # 1. Energie auf Maximum für die Rechenlast
    set_power_plan(PLAN_HIGH_PERFORMANCE)
    
    start_total = time.time()
    
    try:
        for i, (script, desc) in enumerate(PIPELINE_SEQUENCE, 1):
            print(f"\n[SCHRITT {i}/{len(PIPELINE_SEQUENCE)}]")
            
            success = False
            if script == "BATDETECT2_CLI":
                success = run_batdetect2_cli()
            else:
                success = run_python_script(script, desc)
                
            if not success:
                print("\n❌ Pipeline-Abbruch. Überprüfen Sie die Log-Dateien.")
                sys.exit(1)

        duration = time.time() - start_total
        print("\n========================================================")
        print("✅ MISSION ERFOLGREICH: Gesamte Suite wurde ausgeführt.")
        print(f"Gesamtdauer: {duration:.2f} Sekunden")
        print("========================================================")

    except Exception as e:
        print(f"\n💥 Unerwarteter Systemfehler: {e}")
        
    finally:
        # 2. ALWAYS back to standard mode (even on error/abort) /
        # 2. IMMER zurück in den Standard-Modus (auch bei Abbruch/Fehler)
        set_power_plan(PLAN_BALANCED)
        print("Live long and prosper")

if __name__ == "__main__":
    main()
