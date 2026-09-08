# fmi-pv-forecast-runner

One-shot runner around the
[FMI open PV forecast](https://github.com/fmidev/fmi-open-pv-forecast-packaged)
package. Reads PV system parameters from the environment, fetches the
~66-hour hourly forecast from FMI MEPS, and prints the result as JSON to
stdout. Debug / progress logs go to stderr so the stdout stream stays a
clean JSON document.

## Required env vars

| Name         | Description                                        |
|--------------|----------------------------------------------------|
| `PV_LAT`     | Latitude (decimal degrees)                         |
| `PV_LON`     | Longitude (decimal degrees)                        |
| `PV_TILT`    | Panel tilt from horizontal (degrees)               |
| `PV_AZIMUTH` | Panel azimuth (degrees, 180 = south)               |
| `PV_KW`      | Nominal system power (kW)                          |

Geographic coverage: Finland, Scandinavia, Baltic states. See
[ilmatieteenlaitos.fi/numerical-weather-prediction](https://en.ilmatieteenlaitos.fi/numerical-weather-prediction)
for the full available area.

## Optional env vars

| Name          | Description                                              |
|---------------|------------------------------------------------------------|
| `PV_POST_URL` | URL to POST the forecast JSON to, in addition to stdout    |

A failed POST (a non-2xx response, or a transport error such as a refused
connection or a timeout) exits the process with a non-zero status and a
message on stderr, since a scheduled run has only the exit status to tell
success from failure.

## Local run with uv

```bash
uv sync                                   # fetches FMI PV wheel via the URL pinned in pyproject.toml
uv run --env-file .env python run.py > forecast.json
```

The `fmi-pv-forecast` dependency is referenced as a PEP 508 direct URL
pointing at a specific commit SHA in the upstream
[fmi-open-pv-forecast-packaged](https://github.com/fmidev/fmi-open-pv-forecast-packaged)
repository. Bumping the upstream version is a two-line edit in
`pyproject.toml` (SHA + filename) followed by `uv sync`.

## Status: reference implementation

The model this runner wraps has been ported to Rust and now runs inside
[halo](../halo), the only consumer, as `backend/src/pv/forecast/`. This repo is
kept as the reference the port is checked against — run both for the same site
and compare; `outputW` agrees to within a few parts in a million.

### Why the pin stays at 0.1.0

Upstream HEAD is not usable. `0.1.3` (`9919810a`) rewrote FMI retrieval and
regressed with it: solar zenith is computed at hardcoded coordinates `(64, 25)`
rather than the site's, the interval-midpoint `index -= 30min` shift was
dropped, the index became timezone-aware without updating the interpolation
helpers (which now return `None` for every input), and the request window is
built from local wall-clock time. `0.1.2` (`adaa1ddef8`) is sound but
behaviourally inert here — its bifacial and snow-sliding toggles default off,
and its lowered default albedo is unused because the FMI path supplies an
`albedo` column.

Two accuracy caveats are inherited from `0.1.0` itself, and the Rust port
reproduces them deliberately so that any divergence between the two means a
port bug rather than an improvement:

- `DNI = DirHI / cos(sza)` has no zenith cutoff, so sunrise and sunset rows can
  carry inflated output. pvlib's own decomposition models cut off near 87°.
- The Huld efficiency floor is 50% of the standard-conditions figure, which
  overestimates output in near-darkness. It is a local variable in the upstream
  package, so it cannot be tuned through the public API.

A third difference is not reproduced. Where an hour's radiation is missing from
the FMI response, this runner reports it as `0 W` — `add_output_to_df` ends with
`fillna(0.0)`, which turns the resulting NaN into a confident zero — while the
Rust port omits the hour instead.

## Docker

```bash
docker build -t fmi-pv-forecast-runner:local .
docker run --rm \
  -e PV_LAT=60.1576 \
  -e PV_LON=24.8762 \
  -e PV_TILT=25 \
  -e PV_AZIMUTH=180 \
  -e PV_KW=4 \
  fmi-pv-forecast-runner:local > forecast.json
```

## Output

```json
{
  "generatedAt": "2026-04-30T05:00:00Z",
  "points": [
    {
      "time": "2026-04-30T06:00:00Z",
      "outputW": 12.34,
      "temperature": -0.8,
      "wind": 0.79,
      "moduleTemp": -0.8
    }
  ]
}
```

## Deliver the forecast to a backend

Two ways to get the JSON to an HTTP endpoint:

Pipe it yourself — the runner still prints to stdout with nothing else set:

```bash
docker run --rm -e PV_LAT=... -e PV_LON=... -e PV_TILT=... -e PV_AZIMUTH=... -e PV_KW=... \
  fmi-pv-forecast-runner:local \
| curl -fsS -X POST -H 'Content-Type: application/json' \
       --data-binary @- http://localhost:3000/api/pv/forecast
```

Or let the runner POST it, which is what a scheduled deployment wants —
set `PV_POST_URL` and it POSTs the same document there itself, still
printing it to stdout too, so a run's logs always carry the full document
next to the delivery outcome:

```bash
docker run --rm -e PV_LAT=... -e PV_LON=... -e PV_TILT=... -e PV_AZIMUTH=... -e PV_KW=... \
  -e PV_POST_URL=http://localhost:3000/api/pv/forecast \
  fmi-pv-forecast-runner:local > forecast.json
```
