import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# PATHS
# ============================================================
DETECTOR_XML = "../results/detector_output.xml"
TMC_CSV = "../demand/tmc_cal_2020-01-16.csv"  # change if needed
OUTPUT_CSV = "../results/baseline_geh.csv"


# ============================================================
# 1. Parse simulated detector output
# ============================================================
def parse_sim(xml_file):
    tree = ET.parse(xml_file)
    rows = []
    for interval in tree.getroot().findall("interval"):
        rows.append(
            {
                "detector_id": interval.get("id"),
                "begin": float(interval.get("begin")),
                "end": float(interval.get("end")),
                "sim_count": int(interval.get("nVehContrib")),
            }
        )
    df = pd.DataFrame(rows)

    # Extract centreline_id and direction from detector_id
    # Example: det_13467425_n → centreline_id=13467425, direction=n
    df["centreline_id"] = df["detector_id"].str.extract(r"det_(\d+)_")
    df["direction"] = df["detector_id"].str.extract(r"_([nsew])$")
    return df


# ============================================================
# 2. Prepare real TMC data
# ============================================================
def prepare_real(tmc_csv):
    real = pd.read_csv(tmc_csv)

    # Convert time columns
    real["start_time"] = pd.to_datetime(real["start_time"])
    real["begin"] = (
        real["start_time"].dt.hour * 3600
        + real["start_time"].dt.minute * 60
        + real["start_time"].dt.second
    )

    # Sum the three movements for each approach
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

    # Melt into long format so we can match with detectors
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


# ============================================================
# 3. GEH
# ============================================================
def geh(m, c):
    if m + c == 0:
        return 0.0
    return np.sqrt(2 * (m - c) ** 2 / (m + c))


# ============================================================
# 4. Main
# ============================================================
def main():
    print("Loading simulated detector data...")
    sim = parse_sim(DETECTOR_XML)
    print(f"  Simulated intervals: {len(sim)}")
    print(f"  Unique detectors: {sim['detector_id'].nunique()}")

    print("\nLoading real TMC data...")
    real = prepare_real(TMC_CSV)
    print(f"  Real intervals: {len(real)}")

    # Merge on centreline_id + direction + begin time
    merged = pd.merge(
        sim, real, on=["centreline_id", "direction", "begin"], how="inner"
    )

    print(f"\nMatched intervals: {len(merged)}")

    if len(merged) == 0:
        print("\nNo matches found. Possible reasons:")
        print("  - centreline_id format mismatch")
        print("  - time alignment issue")
        print("  - detector naming different from expected")
        print("\nSample simulated detector_ids:")
        print(sim["detector_id"].unique()[:10])
        print("\nSample real centreline_ids:")
        print(real["centreline_id"].unique()[:10])
        return

    # Calculate GEH
    merged["geh"] = merged.apply(lambda r: geh(r["sim_count"], r["real_count"]), axis=1)

    # Summary
    print("\n=== BASELINE GEH SUMMARY ===")
    print(f"Average GEH          : {merged['geh'].mean():.2f}")
    print(f"% of intervals GEH < 5: {(merged['geh'] < 5).mean() * 100:.1f}%")
    print(f"% of intervals GEH < 10: {(merged['geh'] < 10).mean() * 100:.1f}%")

    print("\n=== Top 15 worst GEH ===")
    worst = merged.sort_values("geh", ascending=False).head(15)
    print(
        worst[["detector_id", "begin", "sim_count", "real_count", "geh"]].to_string(
            index=False
        )
    )

    print("\n=== Best 10 GEH ===")
    best = merged.sort_values("geh").head(10)
    print(
        best[["detector_id", "begin", "sim_count", "real_count", "geh"]].to_string(
            index=False
        )
    )

    # Save full results
    merged.to_csv(OUTPUT_CSV, index=False)
    print(f"\nFull results saved to → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
