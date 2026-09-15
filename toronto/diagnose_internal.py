import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from pathlib import Path

DETECTOR_XML = Path("results/detector_output.xml")
TMC_CSV = Path("demand/tmc_cal_2020-01-16.csv")
OUTPUT_CSV = Path("results/internal_geh_summary.csv")

# Lane → (centreline_id, direction)
LANE_TO_APPROACH = {
    "25714347#0_0": ("13467037", "e"),
    "25714347#0_1": ("13467037", "e"),
    "25714347#0_2": ("13467037", "e"),
    "468563690#0_0": ("13467080", "e"),
    "468563690#0_1": ("13467080", "e"),
    "468563690#0_2": ("13467080", "e"),
    "189607534#0_0": ("13467239", "w"),
    "189607534#0_1": ("13467239", "w"),
    "189607534#0_2": ("13467239", "w"),
    "292603460#0_0": ("14254942", "n"),
    "292603460#0_1": ("14254942", "n"),
    "62207370_0": ("13467425", "s"),
    "62207370_1": ("13467425", "s"),
    "-407507555_0": ("13467425", "n"),
    "-407507555_1": ("13467425", "n"),
    "-407507555_2": ("13467425", "n"),
    "-62207369#2_0": ("13467425", "e"),
    "-62207369#2_1": ("13467425", "e"),
}

# Approaches to EXCLUDE (boundary problems)
EXCLUDE = {
    ("13467037", "e"),
    ("13467080", "e"),
    ("13467239", "w"),
    ("14254942", "n"),
}


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
    return pd.DataFrame(rows)


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
    sim = parse_sim(DETECTOR_XML)
    sim["centreline_id"] = sim["detector_id"].map(
        lambda x: LANE_TO_APPROACH.get(x, (None, None))[0]
    )
    sim["direction"] = sim["detector_id"].map(
        lambda x: LANE_TO_APPROACH.get(x, (None, None))[1]
    )

    mapped = sim.dropna(subset=["centreline_id"])
    approach_sim = (
        mapped.groupby(["centreline_id", "direction", "begin"])["sim_count"]
        .sum()
        .reset_index()
    )

    real = prepare_real(TMC_CSV)
    merged = pd.merge(
        approach_sim, real, on=["centreline_id", "direction", "begin"], how="inner"
    )

    # Exclude the 4 boundary approaches
    mask = ~merged.apply(
        lambda r: (r["centreline_id"], r["direction"]) in EXCLUDE, axis=1
    )
    internal = merged[mask].copy()

    internal["geh"] = internal.apply(
        lambda r: geh(r["sim_count"], r["real_count"]), axis=1
    )

    print("=== INTERNAL APPROACHES ONLY (4 boundary approaches excluded) ===")
    print(f"Matched intervals : {len(internal)}")
    print(f"Average GEH       : {internal['geh'].mean():.2f}")
    print(f"% GEH < 5         : {(internal['geh'] < 5).mean() * 100:.1f}%")
    print(f"% GEH < 10        : {(internal['geh'] < 10).mean() * 100:.1f}%")

    print("\n=== By Approach ===")
    by_app = (
        internal.groupby(["centreline_id", "direction"])
        .agg(
            avg_geh=("geh", "mean"),
            avg_sim=("sim_count", "mean"),
            avg_real=("real_count", "mean"),
            n=("geh", "count"),
        )
        .sort_values("avg_geh")
    )
    print(by_app.to_string())

    internal.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
