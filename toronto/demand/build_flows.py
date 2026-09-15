import os
import sys
import pandas as pd
from lxml import etree
from datetime import datetime, timedelta

# -------------------------------------------------
# Paths
# -------------------------------------------------
EDGE_MAP = (
    r"C:\Users\danielshola\Desktop\traffic-digital-twin\toronto\demand\edge_map.csv"
)
TMC_CAL = r"C:\Users\danielshola\Desktop\traffic-digital-twin\toronto\demand\tmc_cal_2020-01-16.csv"
TMC_VAL = r"C:\Users\danielshola\Desktop\traffic-digital-twin\toronto\demand\tmc_val_2020-01-25.csv"
OUT_DIR = r"C:\Users\danielshola\Desktop\traffic-digital-twin\toronto\demand"

os.makedirs(OUT_DIR, exist_ok=True)


# -------------------------------------------------
# Helper: convert time string to seconds from midnight
# -------------------------------------------------
def time_to_seconds(t):
    if pd.isna(t):
        return 0
    if isinstance(t, str):
        t = pd.to_datetime(t)
    return t.hour * 3600 + t.minute * 60 + t.second


# -------------------------------------------------
# Main function
# -------------------------------------------------
def create_flows(tmc_file, edge_map_file, output_xml, label):
    print(f"\n=== Building flows for {label} ===")

    tmc = pd.read_csv(tmc_file)
    edges = pd.read_csv(edge_map_file, dtype=str)

    # Make sure centreline_id is string
    tmc["centreline_id"] = tmc["centreline_id"].astype(str)
    edges["centreline_id"] = edges["centreline_id"].astype(str)

    root = etree.Element("routes")

    # Vehicle type
    vtype = etree.SubElement(root, "vType")
    vtype.set("id", "car")
    vtype.set("accel", "2.6")
    vtype.set("decel", "4.5")
    vtype.set("sigma", "0.5")
    vtype.set("length", "5.0")
    vtype.set("maxSpeed", "50.0")
    vtype.set("guiShape", "passenger")

    flow_count = 0

    # Mapping from approach letter to column names
    approach_map = {
        "n": ("n_edge", "n_appr_cars_r", "n_appr_cars_t", "n_appr_cars_l"),
        "s": ("s_edge", "s_appr_cars_r", "s_appr_cars_t", "s_appr_cars_l"),
        "e": ("e_edge", "e_appr_cars_r", "e_appr_cars_t", "e_appr_cars_l"),
        "w": ("w_edge", "w_appr_cars_r", "w_appr_cars_t", "w_appr_cars_l"),
    }

    for _, row in tmc.iterrows():
        cid = str(row["centreline_id"])
        edge_row = edges[edges["centreline_id"] == cid]

        if edge_row.empty:
            continue

        edge_row = edge_row.iloc[0]
        begin = time_to_seconds(row["start_time"])
        end = time_to_seconds(row["end_time"])

        for direction, (edge_col, r_col, t_col, l_col) in approach_map.items():
            edge_id = edge_row.get(edge_col)
            if pd.isna(edge_id) or edge_id.strip() == "":
                continue

            # Total cars on this approach in this 15-min interval
            total = 0
            for col in [r_col, t_col, l_col]:
                if col in row and not pd.isna(row[col]):
                    total += int(row[col])

            if total <= 0:
                continue

            flow = etree.SubElement(root, "flow")
            flow.set("id", f"flow_{cid}_{direction}_{begin}")
            flow.set("type", "car")
            flow.set("from", edge_id.strip())
            flow.set("begin", str(begin))
            flow.set("end", str(end))
            flow.set("number", str(total))
            # We let JTRROUTER decide the exact turns using the network
            flow_count += 1

    tree = etree.ElementTree(root)
    tree.write(output_xml, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    print(f"Created {flow_count} flows → {output_xml}")


# -------------------------------------------------
# Run for both days
# -------------------------------------------------
if __name__ == "__main__":
    create_flows(
        TMC_CAL, EDGE_MAP, os.path.join(OUT_DIR, "flows_cal.xml"), "CALIBRATION"
    )
    create_flows(
        TMC_VAL, EDGE_MAP, os.path.join(OUT_DIR, "flows_val.xml"), "VALIDATION"
    )
    print("\nDone. Flow files are ready.")
