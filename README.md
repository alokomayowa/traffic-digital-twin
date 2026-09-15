# Toronto Traffic Digital Twin (SUMO)

A calibrated microscopic traffic digital twin of a downtown Toronto study area, built with SUMO and real Turning Movement Count (TMC) data.

The project demonstrates a complete workflow from OpenStreetMap network extraction through demand generation, detector placement, calibration, and validation against municipal open data.

## Project Overview

| Item                    | Value                                      |
|-------------------------|--------------------------------------------|
| Study area              | Downtown Toronto (Financial District / St. Lawrence) |
| Simulation tool         | Eclipse SUMO 1.27                          |
| Real data               | City of Toronto TMC counts (2020)          |
| Calibration day         | 2020-01-16                                 |
| Validation day          | 2020-01-25                                 |
| Main metric             | GEH statistic                              |

## Key Results

### Internal Approaches (well-connected network)

| Metric                        | Calibration (16 Jan) | Validation (25 Jan) |
|-------------------------------|----------------------|---------------------|
| Average GEH                   | **2.87**             | **8.69**            |
| % intervals with GEH < 5      | **70.8%**            | **56.2%**           |
| % intervals with GEH < 10     | 99.0%                | 65.6%               |

The model achieves strong calibration on the core approaches. Validation performance is moderate; the main residual error occurs on one approach and is documented as a known limitation of the network extent.

### Boundary Approaches

Four approaches located on the edge of the extracted network show high GEH because their upstream junctions were not included in the OSM Web Wizard bounding box. These are excluded from the primary evaluation and discussed as a methodological limitation.

## Repository Structure
traffic-digital-twin/
├── toronto/
│   ├── toronto_cal.sumocfg      # Calibration configuration
│   ├── toronto_val.sumocfg      # Validation configuration
│   ├── network/
│   │   └── osm.net.xml          # Cleaned SUMO network
│   ├── demand/
│   │   ├── flows_cal.xml        # Calibration flows (from TMC)
│   │   ├── flows_val.xml        # Validation flows
│   │   ├── toronto_cal.rou.xml  # Routed vehicles (cal)
│   │   ├── toronto_val.rou.xml  # Routed vehicles (val)
│   │   ├── tmc_cal_2020-01-16.csv
│   │   └── tmc_val_2020-01-25.csv
│   ├── detectors/
│   │   └── detectors.add.xml    # Induction loop detectors
│   └── results/                 # GEH summaries & detector outputs
├── calibration/                 # Analysis scripts
└── intas/                       # Optional InTAS benchmark reference
text## How to Run

### Requirements
- Eclipse SUMO ≥ 1.20 (with `sumo`, `jtrrouter`, `netedit` in PATH)
- Python ≥ 3.10
- `pandas`, `numpy`

### Calibration run
```bash
cd toronto
sumo -c toronto_cal.sumocfg
python diagnose_internal.py
Validation run
Bashsumo -c toronto_val.sumocfg
# (point the diagnosis script to tmc_val_2020-01-25.csv)
python diagnose_internal.py


Methodology Summary

Network – Extracted via OSM Web Wizard, cleaned in netedit.
Demand – Turning Movement Counts converted to <flow> definitions and routed with jtrrouter.
Detectors – Induction loops placed on approach lanes (period = 900 s to match TMC intervals).
Calibration – Demand scaling and approach-specific adjustments; evaluated with GEH.
Validation – Same model applied to a second day without further parameter changes.
Limitations – Boundary approaches lack upstream junctions → documented and excluded from primary metrics.

Limitations

Four peripheral approaches suffer from missing upstream network connectivity (OSM extract boundary effect).
High number of teleports on the denser calibration day indicates residual congestion / lane-change issues.
Turning ratios are derived from a single day and do not fully capture day-to-day variability.

Future Improvements

Expand the OSM bounding box to include upstream junctions for the boundary approaches.
Introduce time-varying turning ratios or origin-destination matrices.
Calibrate driver behaviour parameters (tau, sigma) in addition to demand volumes.
Add multi-day validation and confidence intervals on GEH.

Licence
This project is released for educational and research purposes.

City of Toronto TMC data remains subject to the City’s open-data licence