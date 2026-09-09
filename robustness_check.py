"""Apply the same time windows to the original and earlier periods."""
import pandas as pd
from charts import OUTPUT, difference_chart
from market_data import load_prices
from metrics import PERIODS, hourly_table, compare_windows, summarize


def main():
    summaries, comparisons = [], []
    for label, start, end in PERIODS:
        comparison = compare_windows(hourly_table(load_prices(start, end)))
        summaries.append(summarize(comparison, label))
        comparison["period"] = label
        comparisons.append(comparison)
    summary = pd.concat(summaries, ignore_index=True)
    daily = pd.concat(comparisons).sort_index()
    OUTPUT.mkdir(exist_ok=True)
    summary.to_csv(OUTPUT / "period_comparison.csv", index=False, float_format="%.6f")
    daily.to_csv(OUTPUT / "daily_price_difference.csv", float_format="%.6f")
    difference_chart(daily)
    print(summary.round(2).to_string(index=False))
    print("Chart and detailed tables saved in outputs/.")


if __name__ == "__main__":
    main()
