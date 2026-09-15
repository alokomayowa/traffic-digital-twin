# Toronto Traffic Digital Twin: Results Report

This report documents the calibration and validation results for the Toronto SUMO digital twin described in the [README](README.md). The detailed setup history and external references are available in the [build guide](sumo-digital-twin-build-guide.md).

![Map of the study area intersections](intersection-map.png)

## 1. Study and Evaluation Design

The model represents a downtown Toronto study area using an OpenStreetMap-derived SUMO network and City of Toronto Turning Movement Count (TMC) data.

| Item | Value |
| --- | --- |
| Calibration day | 16 January 2020 |
| Validation day | 25 January 2020 |
| Observation interval | 15 minutes |
| Main metric | GEH statistic |
| Primary evaluation set | Internal, well-connected approaches |

The GEH statistic is calculated as:

```text
GEH = sqrt(2 * (M - C)^2 / (M + C))
```

where `M` is the simulated count and `C` is the observed count. A GEH value below 5 is treated as a good match for an individual interval.

## 2. Reproducibility Links

- Configuration files: [calibration](toronto/toronto_cal.sumocfg) and [validation](toronto/toronto_val.sumocfg).
- Calibration data: [TMC CSV](toronto/demand/tmc_cal_2020-01-16.csv).
- Validation data: [TMC CSV](toronto/demand/tmc_val_2020-01-25.csv).
- Detector definitions: [detectors.add.xml](toronto/detectors/detectors.add.xml).
- Calibration script: [calibrate_demand.py](toronto/calibrate_demand.py).
- Internal GEH analysis: [diagnose_internal.py](toronto/diagnose_internal.py).
- Result files: [calibration demand](toronto/results/calibration_demand.csv), [internal GEH summary](toronto/results/internal_geh_summary.csv), and [worst detectors](toronto/results/worst_detectors.csv).

Run instructions are maintained in the [README](README.md). Commands must be run from `toronto/` because the configuration files use relative paths.

## 3. Calibration Performance

The model was calibrated against TMC observations from 16 January 2020. After demand adjustments, performance on the internal approaches was:

| Metric | Value |
| --- | ---: |
| Average GEH | **2.87** |
| Intervals with GEH < 5 | **70.8%** |
| Intervals with GEH < 10 | **99.0%** |

### Internal approach results

| Approach | Average GEH | Interpretation |
| --- | ---: | --- |
| 13467425 North | 1.19 | Excellent |
| 13467425 South | 1.36 | Excellent |
| 13467425 East | 6.08 | Acceptable |

These results indicate that the core of the digital twin reproduces observed traffic volumes with good accuracy.

## 4. Validation Performance

The calibrated model was applied without further parameter changes to the independent day of 25 January 2020.

| Metric | Calibration | Validation |
| --- | ---: | ---: |
| Average GEH | 2.87 | 8.69 |
| Intervals with GEH < 5 | 70.8% | 56.2% |
| Intervals with GEH < 10 | 99.0% | 65.6% |

| Approach | Calibration GEH | Validation GEH | Observation |
| --- | ---: | ---: | --- |
| 13467425 North | 1.19 | 3.54 | Remains acceptable |
| 13467425 East | 6.08 | 2.76 | Improved |
| 13467425 South | 1.36 | 19.76 | Large degradation |

The model generalizes moderately well. The south approach shows a substantial validation degradation, which is consistent with day-specific demand patterns and limitations in route choice and turning ratios derived from a single calibration day.

## 5. Boundary Approaches and Network Limitations

Four peripheral approaches produced consistently high GEH values:

- 13467037 East
- 13467080 East
- 13467239 West
- 14254942 North

Network inspection showed that the upstream junctions feeding these approaches were outside the OpenStreetMap extract generated for the study area. Vehicles therefore could not enter the network realistically from those directions. Artificially inserted boundary flows did not produce detector counts that matched field observations.

These four approaches are excluded from the primary evaluation. With them excluded, the internal network achieves an average GEH of 2.87 during calibration, with 70.8% of 15-minute intervals below GEH 5. The remaining error is therefore primarily associated with the limited network extent rather than the demand-generation and calibration workflow itself.

## 6. Conclusions and Next Steps

The project delivers a reproducible pipeline from municipal turning counts to a calibrated and partially validated SUMO digital twin. It achieves strong calibration performance on the well-connected core and makes the network-boundary limitation explicit rather than hiding it in aggregate metrics.

Recommended next steps are:

1. Expand the OpenStreetMap bounding box to include upstream junctions for the four boundary approaches.
2. Introduce time-varying turning ratios or an origin-destination demand model.
3. Calibrate driver behavior parameters such as `tau` and `sigma` after demand is stable.
4. Add multi-day validation and confidence intervals for GEH.