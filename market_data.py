import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# Locate the cache relative to this script, on either Mac or Windows.
PROJECT_DIR = Path(__file__).resolve().parent
CACHE_DIR = PROJECT_DIR / "data" / "raw"


def validate_day(payload, date_text):
    """Convert a daily response to a table and check its contents."""
    meta = payload["meta"]

    if meta.get("dataset") != "day-ahead-spot" or meta.get("spatial_coverage") != "EE bidding zone":
        raise ValueError(f"{date_text}: unexpected dataset or bidding zone")

    if meta.get("unit") != "EUR/MWh":
        raise ValueError(f"{date_text}: unexpected price unit")

    if meta.get("resolution_minutes") != 15:
        raise ValueError(f"{date_text}: unexpected interval length")

    df = pd.DataFrame(payload["rows"])
    df["mtu_start"] = pd.to_datetime(df["mtu_start"], utc=True)
    df["time_estonia"] = df["mtu_start"].dt.tz_convert("Europe/Tallinn")
    df["price_eur_mwh"] = pd.to_numeric(
        df["price_eur_mwh"], errors="raise"
    )
    df = df.sort_values("mtu_start").reset_index(drop=True)

    start = pd.Timestamp(date_text, tz="Europe/Tallinn")
    end = start + pd.DateOffset(days=1)

    expected = pd.date_range(
        start=start,
        end=end,
        freq="15min",
        inclusive="left",
    )

    if not pd.DatetimeIndex(df["time_estonia"]).equals(expected):
        raise ValueError(f"{date_text}: incorrect delivery intervals")

    prices = df["price_eur_mwh"]

    if prices.isna().any() or prices.isin([float("inf"), float("-inf")]).any():
        raise ValueError(f"{date_text}: missing or non-finite prices")

    return df


def load_prices(start_date, end_date, *, offline=True, verbose=False):
    """Load validated daily prices from saved files or the API."""
    dates = pd.date_range(start=start_date, end=end_date, freq="D")

    if len(dates) == 0:
        raise ValueError("The date range is empty.")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    tables = []
    downloaded = 0
    reused = 0

    for date in dates:
        date_text = date.strftime("%Y-%m-%d")
        cache_file = CACHE_DIR / f"{date_text}.json"

        if cache_file.exists():
            saved = json.loads(cache_file.read_text(encoding="utf-8"))
            df = validate_day(saved["payload"], date_text)
            reused += 1
            if verbose:
                print("Cached:    ", date_text)

        else:
            url = (
                "https://public-data.volton.energy/v1/day-ahead-spot/"
                f"{date_text}.json"
            )

            print("Downloading:", date_text, flush=True)
            if offline:
                raise FileNotFoundError(f"Missing snapshot: {cache_file}. No download attempted.")
            import requests

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            payload = response.json()

            # Validate before saving a new response.
            df = validate_day(payload, date_text)

            saved = {
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_url": url,
                "payload": payload,
            }

            # Write to a temporary file first, then rename it.
            temporary = cache_file.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(saved, indent=2, ensure_ascii=False, allow_nan=False),
                encoding="utf-8",
            )
            temporary.replace(cache_file)
            downloaded += 1

        tables.append(df)

    history = pd.concat(tables, ignore_index=True)
    history = history.sort_values("mtu_start").reset_index(drop=True)

    print("\nDownloaded days:", downloaded)
    print("Reused cached days:", reused)
    print("Total intervals:", len(history))

    return history


# Run this check only when this file is executed directly.
if __name__ == "__main__":
    history = load_prices("2026-08-11", "2026-09-07")
    print(
        f"Average price: {history['price_eur_mwh'].mean():.2f} EUR/MWh"
    )
