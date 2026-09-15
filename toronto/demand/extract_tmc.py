from pathlib import Path
import os
import pandas as pd

# Project root
PROJECT_ROOT = Path(r"C:\Users\danielshola\Desktop\traffic-digital-twin")

# Paths
RAW_CSV = PROJECT_ROOT / "toronto" / "data" / "tmc_raw_data_2020_2029.csv"
OUT_DIR = PROJECT_ROOT / "toronto" / "demand"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# Your exact 8 centreline_ids
MY_IDS = [
    "13467132",  # Front St E / Scott St / Berczy Park Trl
    "13467037",  # Wellington St E / Scott St / Berczy Park Trl
    "13467239",  # Yonge St / Front St E / Front St W
    "13467327",  # The Esplanade / Scott St
    "13467080",  # Yonge St / Wellington St E / Wellington St W
    "14254942",  # Front St E / Church St
    "13467425",  # Yonge St / The Esplanade
    "13467160",  # The Esplanade / Church St
]

CAL_DATE = "2020-01-16"
VAL_DATE = "2020-01-25"


def main():
    print("Loading raw TMC...")
    raw = pd.read_csv(RAW_CSV, low_memory=False, dtype={"centreline_id": str})

    # Force string IDs
    if "centreline_id" in raw.columns:
        raw["centreline_id"] = raw["centreline_id"].astype(str)
    else:
        # fallback if column name is different
        print("Columns found:", raw.columns.tolist())
        raise ValueError("centreline_id column not found – check the file")

    raw["count_date"] = pd.to_datetime(raw["count_date"]).dt.date

    # Filter
    mask = raw["centreline_id"].isin(MY_IDS) & raw["count_date"].isin(
        [pd.to_datetime(CAL_DATE).date(), pd.to_datetime(VAL_DATE).date()]
    )
    subset = raw[mask].copy()

    print(f"Rows kept: {len(subset)}")
    print(f"Intersections present: {subset['centreline_id'].nunique()}")
    print(f"Dates present: {sorted(subset['count_date'].unique())}")

    # Save two clean files
    cal = subset[subset["count_date"] == pd.to_datetime(CAL_DATE).date()]
    val = subset[subset["count_date"] == pd.to_datetime(VAL_DATE).date()]

    cal.to_csv(os.path.join(OUT_DIR, "tmc_cal_2020-01-16.csv"), index=False)
    val.to_csv(os.path.join(OUT_DIR, "tmc_val_2020-01-25.csv"), index=False)

    print("Saved:")
    print("  toronto/demand/tmc_cal_2020-01-16.csv")
    print("  toronto/demand/tmc_val_2020-01-25.csv")

    # Quick peek at the important columns
    car_cols = [c for c in subset.columns if "appr_cars" in c.lower()]
    print("\nCar movement columns found:")
    print(car_cols)


if __name__ == "__main__":
    main()
