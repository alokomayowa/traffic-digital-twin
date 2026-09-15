import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import subprocess
import shutil
from pathlib import Path
import time
import os

print("Current working directory:", os.getcwd())

FLOWS_ORIGINAL = Path("demand/flows_cal.xml")
FLOWS_TEMP = Path("demand/flows_cal_temp.xml")
ROUTES_OUTPUT = Path("demand/toronto_cal.rou.xml")
NET_FILE = Path("network/osm.net.xml")
SUMO_CFG = Path("toronto_cal.sumocfg")
DETECTOR_XML = Path("results/detector_output.xml")
TMC_CSV = Path("demand/tmc_cal_2020-01-16.csv")
RESULTS_CSV = Path("results/calibration_demand.csv")

MULTIPLIERS = [0.8, 1.0, 1.3, 1.6, 2.0]


def geh(m, c):
    if m + c == 0:
        return 0.0
    return np.sqrt(2 * (m - c) ** 2 / (m + c))


def parse_sim(xml_file):
    tree = ET.parse(xml_file)
    rows = []
    for interval in tree.getroot().findall("interval"):
        rows.append(
            {
                "detector_id": interval.get("id"),
                "begin": float(interval.get("begin")),
                "sim_count": int(interval.get("nVehContrib")),
            }
        )
    df = pd.DataFrame(rows)
    df["centreline_id"] = df["detector_id"].str.extract(r"det_(\d+)_")
    df["direction"] = df["detector_id"].str.extract(r"_([nsew])$")
    return df


def prepare_real(tmc_csv):
    real = pd.read_csv(tmc_csv)
    real["start_time"] = pd.to_datetime(real["start_time"])
    real["begin"] = (
        real["start_time"].dt.hour * 3600 + real["start_time"].dt.minute * 60
    )

    real["n_total"] = (
        real["n_appr_cars_r"] + real["n_appr_cars_t"] + real["n_appr_cars_l"]
    )
    real["s_total"] = (
        real["s_appr_cars_r"] + real["s_appr_cars_t"] + real["s_appr_cars_l"]
    )
    real["e_total"] = (
        real["e_appr_cars_r"] + real["e_appr_cars_t"] + real["e_appr_cars_l"]
    )
    real["w_total"] = (
        real["w_appr_cars_r"] + real["w_appr_cars_t"] + real["w_appr_cars_l"]
    )

    long = []
    for direction, col in [
        ("n", "n_total"),
        ("s", "s_total"),
        ("e", "e_total"),
        ("w", "w_total"),
    ]:
        temp = real[["centreline_id", "begin", col]].copy()
        temp = temp.rename(columns={col: "real_count"})
        temp["direction"] = direction
        long.append(temp)

    real_long = pd.concat(long, ignore_index=True)
    real_long["centreline_id"] = real_long["centreline_id"].astype(str)
    return real_long


def calculate_geh(sim, real):
    merged = pd.merge(
        sim, real, on=["centreline_id", "direction", "begin"], how="inner"
    )
    if len(merged) == 0:
        return None, 0, 0
    merged["geh"] = merged.apply(lambda r: geh(r["sim_count"], r["real_count"]), axis=1)
    return merged["geh"].mean(), (merged["geh"] < 5).mean() * 100, len(merged)


def scale_flows(multiplier):
    tree = ET.parse(FLOWS_ORIGINAL)
    root = tree.getroot()
    for flow in root.findall("flow"):
        original = int(float(flow.get("number")))
        new_val = max(1, int(round(original * multiplier)))
        flow.set("number", str(new_val))
    tree.write(FLOWS_TEMP, encoding="UTF-8", xml_declaration=True)
    print(f"  Scaled flows × {multiplier}")


def main():
    real = prepare_real(TMC_CSV)
    shutil.copy(FLOWS_ORIGINAL, str(FLOWS_ORIGINAL) + ".backup")
    results = []

    for mult in MULTIPLIERS:
        print(f"\n===== Multiplier = {mult} =====")
        start = time.time()

        scale_flows(mult)

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
        subprocess.run(jtr_cmd, check=True)

        with open(ROUTES_OUTPUT) as f:
            vehicle_count = f.read().count("<vehicle")
        print(f"  Vehicles: {vehicle_count}")

        print("  Running SUMO...")
        sumo_cmd = ["sumo", "-c", str(SUMO_CFG), "--no-step-log", "true"]
        subprocess.run(sumo_cmd, check=True)

        # Calculate GEH
        sim = parse_sim(DETECTOR_XML)
        avg_geh, pct_good, n_matched = calculate_geh(sim, real)

        elapsed = time.time() - start
        print(
            f"  → Avg GEH = {avg_geh:.2f} | % < 5 = {pct_good:.1f}% | Time = {elapsed:.0f}s"
        )

        results.append(
            {
                "multiplier": mult,
                "vehicles": vehicle_count,
                "avg_geh": avg_geh,
                "pct_geh_lt_5": pct_good,
                "matched": n_matched,
                "time": elapsed,
            }
        )

    shutil.copy(str(FLOWS_ORIGINAL) + ".backup", FLOWS_ORIGINAL)
    print("\nOriginal flows restored.")

    df = pd.DataFrame(results)
    df.to_csv(RESULTS_CSV, index=False)

    print("\n===== FINAL RESULTS =====")
    print(df.to_string(index=False))

    best = df.loc[df["avg_geh"].idxmin()]
    print(f"\nBest multiplier : {best['multiplier']}")
    print(f"Best average GEH: {best['avg_geh']:.2f}")
    print(f"% GEH < 5       : {best['pct_geh_lt_5']:.1f}%")


if __name__ == "__main__":
    main()
