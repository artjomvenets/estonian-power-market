import pandas as pd

from market_data import load_prices


# Keep these windows fixed, as selected in our original analysis.
AFTERNOON_HOURS = [13, 14, 15]       # 13:00–16:00
EVENING_HOURS = [19, 20, 21, 22]    # 19:00–23:00

PERIODS = [
    ("Original sample", "2026-08-11", "2026-09-07"),
    ("Earlier sample", "2026-07-14", "2026-08-10"),
]

results = []

for label, start_date, end_date in PERIODS:
    print(f"\n--- {label}: {start_date} to {end_date} ---")

    history = load_prices(start_date, end_date)

    history["delivery_date"] = history["time_estonia"].dt.date
    history["hour"] = history["time_estonia"].dt.hour

    # One row per day, one column per local hour.
    hourly = (
        history.groupby(["delivery_date", "hour"])["price_eur_mwh"]
        .mean()
        .unstack("hour")
    )

    comparison = pd.DataFrame({
        "afternoon": hourly[AFTERNOON_HOURS].mean(axis=1),
        "evening": hourly[EVENING_HOURS].mean(axis=1),
    })

    comparison["difference"] = (
        comparison["evening"] - comparison["afternoon"]
    )

    comparison["day_type"] = [
        "Weekend" if pd.Timestamp(date).dayofweek >= 5 else "Weekday"
        for date in comparison.index
    ]

    # Report the full period and its weekday/weekend subsets.
    for group_name in ["All days", "Weekday", "Weekend"]:
        if group_name == "All days":
            subset = comparison
        else:
            subset = comparison[comparison["day_type"] == group_name]

        difference = subset["difference"]

        results.append({
            "period": label,
            "group": group_name,
            "days": len(subset),
            "evening_higher_days": int((difference > 0).sum()),
            "evening_higher_pct": 100 * (difference > 0).mean(),
            "mean_difference": difference.mean(),
            "median_difference": difference.median(),
        })

    # Show exceptions instead of hiding them inside an average.
    exceptions = comparison[comparison["difference"] <= 0]

    print("\nDays evening was cheaper or equal:")
    if exceptions.empty:
        print("None")
    else:
        print(exceptions.round(2).to_string())

summary = pd.DataFrame(results)

print("\nPERIOD COMPARISON")
print("Differences are evening minus afternoon, in EUR/MWh.")
print(summary.round(2).to_string(index=False))