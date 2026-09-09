"""Reproduce the original 28-day analysis from the included snapshot."""
import pandas as pd
from charts import OUTPUT, profile_chart
from market_data import load_prices
from metrics import hourly_table, compare_windows, summarize


def main():
    history = load_prices("2026-08-11", "2026-09-07")
    hourly = hourly_table(history)
    profile = pd.DataFrame({"mean": hourly.mean(), "median": hourly.median(),
                            "p25": hourly.quantile(.25), "p75": hourly.quantile(.75)})
    profile.index.name = "local_hour"
    comparison = compare_windows(hourly)
    OUTPUT.mkdir(exist_ok=True)
    profile.to_csv(OUTPUT / "hourly_profile.csv", float_format="%.6f")
    comparison.to_csv(OUTPUT / "original_daily_comparison.csv", float_format="%.6f")
    peaks = hourly.eq(hourly.max(axis=1), axis="index").sum()
    peaks.rename("peak_days_including_ties").to_csv(OUTPUT / "peak_hour_counts.csv")
    profile_chart(profile)
    print(f"Average price: {history.price_eur_mwh.mean():.2f} EUR/MWh")
    print(summarize(comparison, "Original sample").round(2).to_string(index=False))
    print("Chart and detailed tables saved in outputs/.")


if __name__ == "__main__":
    main()
