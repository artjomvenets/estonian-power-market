"""Optional live pipeline consistency check."""

def main():
    import pandas as pd
    import requests

    from market_data import load_prices

    delivery_date = "2026-09-07"

    # Load the saved Volton data.
    volton = load_prices(delivery_date, delivery_date)
    volton = volton[["mtu_start", "price_eur_mwh"]].rename(
        columns={"price_eur_mwh": "volton_price"}
    )

    # Define the delivery day in Estonian local time.
    start = pd.Timestamp(delivery_date, tz="Europe/Tallinn")
    end = start + pd.DateOffset(days=1)

    params = {
        "start": start.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": (
            end.tz_convert("UTC") - pd.Timedelta(seconds=1)
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    response = requests.get(
        "https://dashboard.elering.ee/api/nps/price",
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("success") is not True:
        raise ValueError("Elering reported an unsuccessful request.")

    # Select Estonia and convert Unix seconds into UTC timestamps.
    elering = pd.DataFrame(payload["data"]["ee"])
    elering["mtu_start"] = pd.to_datetime(
        elering["timestamp"], unit="s", utc=True
    )
    elering["elering_price"] = pd.to_numeric(
        elering["price"], errors="raise"
    )
    elering = elering[["mtu_start", "elering_price"]]

    if elering["mtu_start"].isna().any():
        raise ValueError("Elering contains missing timestamps.")

    if elering["mtu_start"].duplicated().any():
        raise ValueError("Elering contains duplicate timestamps.")

    prices = elering["elering_price"]
    if prices.isna().any() or prices.isin([float("inf"), float("-inf")]).any():
        raise ValueError("Elering contains missing or non-finite prices.")

    # An outer join retains unmatched records from either source.
    comparison = volton.merge(
        elering,
        on="mtu_start",
        how="outer",
        validate="one_to_one",
        indicator=True,
    ).sort_values("mtu_start")

    unmatched = comparison[comparison["_merge"] != "both"]

    print("\nCOVERAGE CHECK")
    print("Volton intervals:", len(volton))
    print("Elering intervals:", len(elering))
    print("Unmatched timestamps:", len(unmatched))

    if not unmatched.empty:
        print(unmatched.to_string(index=False))
        raise SystemExit("Stopped: the sources have different timestamp coverage.")

    # Compare prices with a tiny tolerance for floating-point arithmetic.
    comparison["absolute_difference"] = (
        comparison["volton_price"] - comparison["elering_price"]
    ).abs()

    tolerance = 0.000001
    mismatches = comparison[
        comparison["absolute_difference"] > tolerance
    ]

    print("\nPRICE COMPARISON —", delivery_date)
    print("Intervals compared:", len(comparison))
    print("Price mismatches:", len(mismatches))
    print(
        "Largest absolute difference:",
        f"{comparison['absolute_difference'].max():.8f}",
    )

    if mismatches.empty:
        print("All prices match within the stated tolerance.")
    else:
        print("\nMISMATCHED RECORDS")
        print(mismatches.to_string(index=False))
        raise SystemExit("Price mismatches detected.")


if __name__ == "__main__":
    main()
