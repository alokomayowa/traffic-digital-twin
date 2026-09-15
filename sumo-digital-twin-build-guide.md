# SUMO Digital Twin — Build Guide (InTAS → Toronto)

What you end up with: a calibrated SUMO traffic model, first proven on the InTAS (Ingolstadt) benchmark, then applied to a real downtown Toronto study area using the city's own open turning-movement-count data. Final deliverables: a one-command GitHub repo and a 4–6 page report with before/after calibration error tables.

Everything below is real — checked against the official docs, the actual GitHub repos, and the actual dataset pages. Where a link couldn't be verified directly, that's flagged so you don't waste time on a dead URL.

---

## Phase 0 — Install (do this before Week 1)

**Install SUMO.**
- Easiest cross-platform route: `pip install eclipse-sumo traci sumolib libsumo` — this is the official PyPI package. Note: on Windows, `eclipse-sumo` wheels are unreliable for the newest releases (known open issue); if `pip install eclipse-sumo` fails on Windows, use the Windows installer instead.
- Installer / binaries for Windows/macOS/Linux: the SUMO downloads page, linked from the documentation home: https://sumo.dlr.de/docs/index.html
- Source / latest dev version: `git clone --recursive https://github.com/eclipse-sumo/sumo` (this is the current org — it was renamed from `eclipse/sumo`)
- After installing, set the `SUMO_HOME` environment variable to your install directory (the Windows/Ubuntu installers usually do this for you — verify with `echo $SUMO_HOME` / `echo %SUMO_HOME%`).
- Verify: run `sumo --version` and `sumo-gui` in a terminal. Both should open/print without error.

**Python environment.**
```
python -m pip install eclipse-sumo traci sumolib libsumo numpy pandas scipy deap matplotlib
```
`traci` and `sumolib` are the Python interfaces you'll use constantly; `libsumo` is the fast headless version of TraCI you'll switch to for calibration runs; `deap` is only needed once you get to genetic-algorithm calibration (Week 8/9).

---

## Week 1 — SUMO fluency

Start here: the official tutorials index — this single page is your anchor for the whole week: **https://sumo.dlr.de/docs/Tutorials**

1. **Hello World** — build the simplest possible network and demand file by hand in `netedit`, then run it in `sumo-gui`. Direct link: https://sumo.dlr.de/docs/Tutorials/Hello_World.html
2. **OSMWebWizard** — generate a real scenario from OpenStreetMap in a few clicks using `osmWebWizard.py` (found in `<SUMO_HOME>/tools`). Linked from the Tutorials index above. Do this even though you'll build the Toronto network manually later — it's the fastest way to see a *real* city network running end-to-end and builds intuition for Week 6.
3. **Quick Start** — a more deliberate `netedit` tutorial (four origins/destinations, two unsignalized intersections). Also linked from the Tutorials index above.
4. Build one signalized 4-way intersection by hand in `netedit` and watch traffic flow through it in `sumo-gui`.

Done when: you can build and run a small network without the docs open.

---

## Week 2 — Python control via TraCI

1. **TraCI4Traffic Lights** tutorial — connect a Python script to a running simulation, read detector state, switch a traffic light. Direct link: https://sumo.dlr.de/docs/Tutorials/TraCI4Traffic_Lights.html
2. Write your own script that: starts a sim headless, steps through it, reads vehicle speeds/positions each step, and writes detector counts to a CSV.
3. Swap `import traci` for `import libsumo as traci` and rerun — same API, no GUI, much faster. This is what you'll use for every calibration run from Week 4 onward.

A minimal TraCI loop looks like this — this is the skeleton every later script in this project builds on:
```python
import traci

traci.start(["sumo", "-c", "my_scenario.sumocfg"])
step = 0
while step < 1000:
    traci.simulationStep()
    vehicle_ids = traci.vehicle.getIDList()
    step += 1
traci.close()
```

Done when: a script runs a sim headless and outputs a CSV of detector counts.

---

## Week 3 — Run InTAS

**InTAS** (Ingolstadt Traffic Scenario) is a free, research-grade, real-city SUMO model published by Technische Hochschule Ingolstadt. It gives you: the full Ingolstadt road network with buildings and bus stops, 20 real traffic-light programs, ~333,700 daily trips generated from real demographic data, the full bus network (56 lines), and — the part that matters most for you — real vehicle counts from 24 measurement points, already used to validate the scenario.

- **Repo:** https://github.com/silaslobo/InTAS
- **Conference presentation (video):** https://www.youtube.com/watch?v=UgPeBxXzDHc (SUMO User Conference 2020)
- **Paper / how to cite:** S. Lobo, S. Neumeier, E. Fernandez, C. Facchi, "InTAS – The Ingolstadt Traffic Scenario for SUMO," *SUMO User Conference Proceedings*, 2020. DOI: 10.52825/scp.v1i.102. PDF mirror: https://eclipse.dev/sumo/documents/2020/SUMO2020_paper_24.pdf · arXiv version: https://arxiv.org/abs/2011.11995

Steps:
1. `git clone https://github.com/silaslobo/InTAS`
2. Launch it: `sumo-gui -c InTAS_full_poly.sumocfg` (fullest visualization) or `sumo -c InTAS_buildings.sumocfg` (buildings + bus stops + detectors + parking, no headless-unfriendly extras).
3. Confirm your SUMO version is compatible — the repo lists testing against 1.7.0–1.10.0; if you're on a much newer SUMO and hit errors, that's the first thing to check.
4. Open the `scenario/` folder and find: the demand files, the 20 traffic-light definitions, and the induction-loop (`E1`) detector definitions for the 24 measurement points. These detector files are what you'll compare simulated counts against.

One honest flag: the repo's public README doesn't spell out an October/November 2019 calibration-vs-validation date split in so many words — that level of detail lives in the scenario files themselves or the paper. Confirm the exact split by opening the demand/detector files in `scenario/` before you build your Week 5 validation step around it; don't assume the split without checking.

Done when: InTAS runs end-to-end on your machine and you can see live vehicle counts at the 24 measurement points via `sumo-gui`.

---

## Week 4 — Calibration loop v1 (on InTAS)

This is the core engineering piece of the whole project — you'll reuse this exact loop, unmodified in structure, for Toronto later.

The loop: adjust demand → run headless via `libsumo` → read simulated detector counts → score against real counts → adjust again.

Two error metrics are the transport-engineering standard here and belong in every table you produce:
- **GEH statistic:** `GEH = sqrt( 2*(M-C)^2 / (M+C) )` where M = modeled/simulated count, C = real/counted volume. Convention: a location "passes" if GEH < 5.
- **MAPE:** mean absolute percentage error across locations/intervals.

Start with the simplest possible search — grid or random search over 5–10 demand-multiplier parameters — before reaching for anything smarter. SUMO's own calibration tutorial (car-following parameters against a real observed dataset, not demand, but the same loop-with-a-control-script pattern) is a good reference for structuring this: https://sumo.dlr.de/wiki/Tutorials/Calibration/San_Pablo_Dam

Done when: the loop runs unattended and the error visibly drops run over run.

**Demand first, car-following second.** It's tempting to jump straight to tuning per-vehicle-type parameters like `maxSpeed`/`accel` (the Krauss model's `tau`/`sigma` are the usual targets) because TraCI makes that easy to script. Don't calibrate those before your demand volumes are roughly right — if the number of cars entering the network is wrong, no amount of car-following tuning will fix the resulting GEH/MAPE error. Get demand close first, using GEH/MAPE against real volume counts (what you actually have, from InTAS's 24 measurement points or Toronto's TMC data). Car-following parameters are a second, finer pass for matching speeds/travel times once volumes are in range — and that second pass needs real travel-time observations to calibrate against, not placeholder numbers.

---

## Week 5 — Validation: your first reportable result

Upgrade the search to `scipy.optimize` (e.g. `differential_evolution` or `minimize` with a bounded method) or a small genetic algorithm via `deap`. Calibrate against one InTAS dataset/time period, then run the *same* calibrated parameters against a different time period without re-tuning, and report how well it generalizes.

Write this up now, even briefly — 2 pages, before/after GEH and MAPE tables. This is already a complete, reportable result and your fallback if Toronto (Weeks 6–10) runs into trouble.

Done when: you have a short "calibrating InTAS" write-up with before/after tables.

---

## Week 6 — Toronto: data and network

**Datasets (verified, City of Toronto Open Data Portal):**

- **Traffic Volumes at Intersections for All Modes** (turning-movement counts — this is your main dataset): https://open.toronto.ca/dataset/traffic-volumes-at-intersections-for-all-modes/
  This dataset covers Turning Movement Counts (TMCs) across the city from 1984 onward, in 8-hour, 15-minute-interval sessions, broken down by mode (car/truck/bus/pedestrian/cyclist) and by turning movement at each approach. It's published as three pieces: count metadata (one row per TMC session), count locations, and raw 15-minute data grouped into zip files by decade.
- The city also publishes a companion **Motor Vehicle Speed, Volume and Classification Counts** dataset (segment-level, not intersection-level, going back to 1993) and **RESCU** permanent-loop data on the Gardiner/DVP/Lakeshore. I couldn't pin down their exact catalogue-page slugs — search for them directly in the catalogue: https://open.toronto.ca/catalogue/
- Background on the Jan 2025 dataset refresh (useful context for your report's data section): https://www.toronto.ca/news/city-of-toronto-publishes-new-transportation-datasets-that-highlight-travel-trends-and-support-traffic-management-actions

**Download programmatically instead of clicking through the portal.** Toronto's Open Data Portal runs on CKAN, and the API is simple and confirmed working:
```python
import requests

base_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
params = {"id": "traffic-volumes-at-intersections-for-all-modes"}
package = requests.get(f"{base_url}/api/3/action/package_show", params=params).json()

for resource in package["result"]["resources"]:
    print(resource["name"], resource["url"])
```
Run this first and print the resource list — resource names/filenames get renamed when the city updates the dataset (it happened in Jan 2025), so don't hardcode a filename you saw in someone else's writeup. Pick your study area from whichever "count locations" / "summary" resource comes back, filtering for a cluster of nearby intersections counted in the same recent year — let the data pick the area, not the other way around.

**Build the network.** Extract OSM for your chosen downtown grid (JOSM, the Overpass API, or `osmWebWizard.py`'s built-in downloader all work), then:
```
netconvert --osm-files toronto_area.osm.xml -o toronto.net.xml \
  --geometry.remove --ramps.guess --junctions.join \
  --tls.guess-signals --tls.discard-simple --tls.join \
  --tls.default-type actuated
```
These are SUMO's own recommended OSM-import options (docs: https://sumo.dlr.de/wiki/Networks/Import/OpenStreetMap). Clean up broken connections and verify traffic-light placement afterward in `netedit`.

Done when: you have a network file plus a folder of count CSVs for 6–10 real intersections.

---

## Week 7 — Demand seeding

Build initial demand directly from the TMC turning counts you downloaded — 15-minute flows entering at network edges with real turning ratios — rather than `randomTrips.py`. This starts your simulation "reality-shaped" instead of random, which matters a lot for how fast calibration converges. `duarouter` is what turns flow definitions into actual vehicle routes on your network.

Done when: a runnable Toronto sim that plausibly resembles a real peak hour.

---

## Week 8 — Baseline measurement

Place `inductionLoop` detectors at the exact same locations as your real TMC count points. Run the sim, extract simulated 15-minute counts, and compute GEH/MAPE against the real data — same formulas as Week 4. Report this baseline error honestly; the "before" picture is half your report's value.

Done when: a baseline error table, one row per count location.

---

## Week 9 — Calibration

Point your Week 4/5 optimizer at the Toronto network: tune edge-level demand flows, turning ratios, and car-following parameters (Krauss model's `tau` and `sigma`). This is compute time, not thinking time — run it overnight in batches.

Done when: most locations hit GEH < 5.

---

## Week 10 — Validation

Calibrate on one period (e.g. AM peak or one count date), validate on a different period/date at the same intersections without re-tuning. Write the InTAS-vs-Toronto comparison — what transferred cleanly, what didn't. This comparison section is usually the most original part of the whole report.

Done when: a validation table plus comparison notes against your Week 5 InTAS result.

---

## Week 11 — Repo polish

One-command pipeline (e.g. `python run_calibration.py --scenario toronto` / `--scenario intas`), a README with `sumo-gui` GIFs, `requirements.txt`, sample data included, and both scenarios running through the same code path via config. That dual-scenario support (one calibration engine, two cities) is the strongest software-engineering signal in the whole project.

---

## Week 12 — Report

4–6 pages: problem → data (cite both the InTAS paper above and the Toronto Open Data source) → methodology → InTAS calibration results → Toronto baseline → Toronto calibrated results → validation → limitations. A CV line this earns you: *"Built and validated a calibrated SUMO traffic digital twin of downtown Toronto against municipal open data, using a calibration framework first validated on the Ingolstadt (InTAS) benchmark."*

---

## Advanced calibration tools (optional — graduate to these later, don't start here)

Once your own grid-search loop from Week 4 works, three real, verified third-party tools exist if you want more than a hand-rolled optimizer:

- **actrys** (https://github.com/vishalmhjn/actrys) — a Python platform built specifically for this problem: sequential SUMO calibration, demand/OD first via SPSA + Bayesian optimization, then supply/car-following parameters second, scored against link counts. Small research repo, real and citable (TUM preprint), closest fit to this project if you outgrow the custom loop.
- **sumo-cf-calibration** (UnivOfAlabama-BittleResearchGroup) — real code behind a published paper, but built around proprietary roadside-radar vehicle trajectories (available "on request," pulled via `git lfs`) and Ray-based parallelization. Not a fit here — you don't have trajectory data, only turning-movement counts.
- **demandify** (PyPI) — real and actively maintained, but calibrates demand against *live* TomTom congestion/speed data via a paid-tier API key, not historical count data, and is still early/beta (a recent release was yanked for a non-convergent fitness bug). Not a fit for calibrating against InTAS or Toronto's historical TMC data.

## Key links, all in one place

| What | Link |
|---|---|
| SUMO docs home | https://sumo.dlr.de/docs/index.html |
| SUMO GitHub (current org) | https://github.com/eclipse-sumo/sumo |
| Tutorials index (start here) | https://sumo.dlr.de/docs/Tutorials |
| Hello World tutorial | https://sumo.dlr.de/docs/Tutorials/Hello_World.html |
| TraCI4Traffic Lights tutorial | https://sumo.dlr.de/docs/Tutorials/TraCI4Traffic_Lights.html |
| Calibration tutorial (San Pablo Dam) | https://sumo.dlr.de/wiki/Tutorials/Calibration/San_Pablo_Dam |
| OSM import docs | https://sumo.dlr.de/wiki/Networks/Import/OpenStreetMap |
| InTAS repo | https://github.com/silaslobo/InTAS |
| InTAS conference video | https://www.youtube.com/watch?v=UgPeBxXzDHc |
| InTAS paper (PDF) | https://eclipse.dev/sumo/documents/2020/SUMO2020_paper_24.pdf |
| Toronto Open Data catalogue | https://open.toronto.ca/catalogue/ |
| Toronto TMC dataset page | https://open.toronto.ca/dataset/traffic-volumes-at-intersections-for-all-modes/ |
| Toronto CKAN API base | https://ckan0.cf.opendata.inter.prod-toronto.ca |

Two risk flags worth remembering: Week 3's exact InTAS calibration/validation date split needs confirming from the scenario files themselves (not just the README), and Week 9 is the point most likely to slip — if calibration stalls, your documented fallback is "InTAS fully calibrated + Toronto baseline with partial calibration," which is still a complete, honest report.
