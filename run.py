"""One-shot FMI open PV forecast runner.

Reads system parameters from environment variables, fetches the FMI
PV forecast for the next ~66 hours, and prints the result as JSON to
stdout. All progress / debug output goes to stderr so the stdout stream
is a clean JSON document suitable for piping.

Required env vars:
  PV_LAT       Latitude (decimal degrees)
  PV_LON       Longitude (decimal degrees)
  PV_TILT      Panel tilt from horizontal (degrees)
  PV_AZIMUTH   Panel azimuth (degrees, 180 = south)
  PV_KW        Nominal system power (kW)

Output JSON shape:
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
"""

import contextlib
import json
import logging
import os
import sys
from datetime import datetime, timezone

import fmi_pv_forecaster as pvfc
import pandas as pd

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("fmi-pv-runner")


def env_float(name: str) -> float:
    value = os.environ.get(name)
    if value is None or value == "":
        sys.exit(f"missing required env: {name}")
    return float(value)


def to_iso_hour(ts) -> str:
    if isinstance(ts, pd.Timestamp):
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    else:
        ts = pd.Timestamp(ts).tz_localize("UTC")
    return ts.strftime("%Y-%m-%dT%H:00:00Z")


def main() -> int:
    lat = env_float("PV_LAT")
    lon = env_float("PV_LON")
    tilt = env_float("PV_TILT")
    azimuth = env_float("PV_AZIMUTH")
    kw = env_float("PV_KW")

    log.info(
        "requesting FMI PV forecast: lat=%s lon=%s tilt=%s azimuth=%s kw=%s",
        lat, lon, tilt, azimuth, kw,
    )

    # Redirect stdout to stderr while the upstream package runs — it uses
    # bare print() calls which would otherwise corrupt the JSON we emit.
    with contextlib.redirect_stdout(sys.stderr):
        pvfc.set_location(lat, lon)
        pvfc.set_angles(tilt, azimuth)
        pvfc.set_nominal_power_kw(kw)

        df = pvfc.get_default_fmi_forecast()

    log.info("forecast returned %d rows", len(df))

    points = []
    for ts, row in df.iterrows():
        output_w = row.get("output")
        if pd.isna(output_w):
            continue
        points.append({
            "time": to_iso_hour(ts),
            "outputW": float(output_w),
            "temperature": None if pd.isna(row.get("T")) else float(row.get("T")),
            "wind": None if pd.isna(row.get("wind")) else float(row.get("wind")),
            "moduleTemp": None if pd.isna(row.get("module_temp")) else float(row.get("module_temp")),
        })

    if not points:
        sys.exit("forecast returned no usable points")

    payload = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "points": points,
    }

    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    log.info("emitted %d forecast points", len(points))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
