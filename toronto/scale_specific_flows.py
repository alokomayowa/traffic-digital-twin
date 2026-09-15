import xml.etree.ElementTree as ET
from pathlib import Path
import shutil

FLOWS = Path("demand/flows_cal.xml")
BACKUP = Path("demand/flows_cal.xml.backup2")

# Scale factors for specific approach prefixes
SCALES = {
    "flow_13467037_e_": 8.0,
    "flow_13467080_e_": 4.0,
    "flow_13467239_w_": 15.0,
    "flow_14254942_n_": 15.0,
    "flow_13467425_e_": 0.3,
    "flow_13467425_n_": 0.7,
}


def main():
    shutil.copy(FLOWS, BACKUP)
    print(f"Backup saved → {BACKUP}")

    tree = ET.parse(FLOWS)
    root = tree.getroot()

    changed = 0
    for flow in root.findall("flow"):
        fid = flow.get("id", "")
        for prefix, factor in SCALES.items():
            if fid.startswith(prefix):
                old = int(float(flow.get("number")))
                new = max(1, int(round(old * factor)))
                flow.set("number", str(new))
                changed += 1
                break

    tree.write(FLOWS, encoding="UTF-8", xml_declaration=True)
    print(f"Updated {changed} flows.")
    print("Done. Now re-run jtrrouter + simulation.")


if __name__ == "__main__":
    main()
