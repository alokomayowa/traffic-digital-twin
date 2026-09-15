import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from pathlib import Path

DETECTOR_XML = Path("results/detector_output.xml")
TMC_CSV = Path("demand/tmc_cal_2020-01-16.csv")
OUTPUT_CSV = Path("results/worst_detectors.csv")


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


def main():
    print("Loading data...")
    sim = parse_sim(DETECTOR_XML)
    real = prepare_real(TMC_CSV)

    merged = pd.merge(
        sim, real, on=["centreline_id", "direction", "begin"], how="inner"
    )
    merged["geh"] = merged.apply(lambda r: geh(r["sim_count"], r["real_count"]), axis=1)
    merged["diff"] = merged["sim_count"] - merged["real_count"]

    print(f"Matched intervals: {len(merged)}")
    print(f"Average GEH: {merged['geh'].mean():.2f}")
    print(f"% GEH < 5: {(merged['geh'] < 5).mean() * 100:.1f}%\n")

    # Worst 25 intervals
    print("=" * 80)
    print("WORST 25 INTERVALS (highest GEH)")
    print("=" * 80)
    worst = merged.sort_values("geh", ascending=False).head(25)
    print(
        worst[
            ["detector_id", "begin", "sim_count", "real_count", "diff", "geh"]
        ].to_string(index=False)
    )

    # Summary by detector (average GEH per detector)
    print("\n" + "=" * 80)
    print("AVERAGE GEH BY DETECTOR (worst first)")
    print("=" * 80)
    by_det = (
        merged.groupby("detector_id")
        .agg(
            avg_geh=("geh", "mean"),
            avg_sim=("sim_count", "mean"),
            avg_real=("real_count", "mean"),
            intervals=("geh", "count"),
        )
        .sort_values("avg_geh", ascending=False)
    )

    print(by_det.head(20).to_string())

    # Summary by intersection + direction
    print("\n" + "=" * 80)
    print("PROBLEM APPROACHES (centreline_id + direction)")
    print("=" * 80)
    by_app = (
        merged.groupby(["centreline_id", "direction"])
        .agg(
            avg_geh=("geh", "mean"),
            avg_sim=("sim_count", "mean"),
            avg_real=("real_count", "mean"),
        )
        .sort_values("avg_geh", ascending=False)
    )

    print(by_app.head(15).to_string())

    # Save full results
    merged.to_csv(OUTPUT_CSV, index=False)
    print(f"\nFull data saved to → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
