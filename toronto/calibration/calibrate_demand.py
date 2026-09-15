import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import subprocess
import shutil
from pathlib import Path
import time
import os

# ============================================================
# Make sure we are in the toronto folder
# ============================================================
print("Current working directory:", os.getcwd())

FLOWS_ORIGINAL = Path("demand/flows_cal.xml")
FLOWS_TEMP = Path("demand/flows_cal_temp.xml")
ROUTES_OUTPUT = Path("demand/toronto_cal.rou.xml")
NET_FILE = Path("network/osm.net.xml")
SUMO_CFG = Path("toronto_cal.sumocfg")
DETECTOR_XML = Path("results/detector_output.xml")
TMC_CSV = Path("demand/tmc_cal_2020-01-16.csv")
RESULTS_CSV = Path("results/calibration_demand.csv")

MULTIPLIERS = [0.8, 1.0, 1.3, 1.6, 2.0]  # fewer values for faster testing


def scale_flows(multiplier):
    print(f"  Reading {FLOWS_ORIGINAL} ...")
    tree = ET.parse(FLOWS_ORIGINAL)
    root = tree.getroot()

    changed = 0
    for flow in root.findall("flow"):
        original = int(float(flow.get("number")))
        new_val = max(1, int(round(original * multiplier)))
        flow.set("number", str(new_val))
        changed += 1

    tree.write(FLOWS_TEMP, encoding="UTF-8", xml_declaration=True)
    print(f"  Scaled {changed} flows × {multiplier} → {FLOWS_TEMP}")
    print(f"  File exists now? {FLOWS_TEMP.exists()}")


def main():
    # Safety checks
    for f in [FLOWS_ORIGINAL, NET_FILE, SUMO_CFG, TMC_CSV]:
        if not f.exists():
            print(f"ERROR: {f} not found!")
            return

    # Backup
    shutil.copy(FLOWS_ORIGINAL, str(FLOWS_ORIGINAL) + ".backup")

    results = []

    for mult in MULTIPLIERS:
        print(f"\n===== Multiplier = {mult} =====")
        start = time.time()

        # 1. Scale
        scale_flows(mult)

        # 2. jtrrouter
        print("  Running jtrrouter...")
        jtr_cmd = [
            "jtrrouter",
            "-r",
            str(FLOWS_TEMP),
            "-n",
            str(NET_FILE),
            "-o",
            str(ROUTES_OUTPUT),
            "--accept-all-destinations",
            "true",
            "--ignore-errors",
            "true",
        ]
        result = subprocess.run(jtr_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("jtrrouter FAILED:")
            print(result.stderr)
            continue

        # Check how many vehicles were generated
        with open(ROUTES_OUTPUT) as f:
            vehicle_count = f.read().count("<vehicle")
        print(f"  Vehicles generated: {vehicle_count}")

        # 3. Run SUMO
        print("  Running SUMO...")
        sumo_cmd = ["sumo", "-c", str(SUMO_CFG), "--no-step-log", "true"]
        subprocess.run(sumo_cmd, check=True)

        elapsed = time.time() - start
        print(f"  Finished in {elapsed:.0f}s")

        results.append({"multiplier": mult, "vehicles": vehicle_count, "time": elapsed})

    # Restore
    shutil.copy(str(FLOWS_ORIGINAL) + ".backup", FLOWS_ORIGINAL)
    print("\nOriginal flows restored.")

    print("\n===== RESULTS =====")
    print(pd.DataFrame(results).to_string(index=False))


if __name__ == "__main__":
    main()
