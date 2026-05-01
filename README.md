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

## Pipe to a backend

```bash
docker run --rm -e PV_LAT=... -e PV_LON=... -e PV_TILT=... -e PV_AZIMUTH=... -e PV_KW=... \
  fmi-pv-forecast-runner:local \
| curl -fsS -X POST -H 'Content-Type: application/json' \
       --data-binary @- http://localhost:3000/api/pv/forecast
```
