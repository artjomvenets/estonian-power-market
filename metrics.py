"""Shared calculations. All hours are Europe/Tallinn delivery hours."""
import pandas as pd

AFTERNOON_HOURS = [13, 14, 15]
EVENING_HOURS = [19, 20, 21, 22]
PERIODS = [
    ("Original sample", "2026-08-11", "2026-09-07"),
    ("Earlier sample", "2026-07-14", "2026-08-10"),
]


def hourly_table(history):
    local = history["time_estonia"]
    # Explicitly reject clock-change days rather than merge repeated hours.
    counts = history.groupby([local.dt.date, local.dt.hour]).size().unstack()
    if counts.shape[1] != 24 or not counts.eq(4).all().all():
        raise ValueError("Hourly profile requires 24 hours with four intervals each; DST days need separate handling.")
    return history.groupby([local.dt.date, local.dt.hour])["price_eur_mwh"].mean().unstack()


def compare_windows(hourly):
    result = pd.DataFrame({
        "afternoon_average": hourly[AFTERNOON_HOURS].mean(axis=1),
        "evening_average": hourly[EVENING_HOURS].mean(axis=1),
    })
    result.index.name = "delivery_date"
    result["difference"] = result["evening_average"] - result["afternoon_average"]
    result["day_type"] = ["Weekend" if pd.Timestamp(d).dayofweek >= 5 else "Weekday" for d in result.index]
    return result


def summarize(comparison, period):
    rows = []
    for group in ["All days", "Weekday", "Weekend"]:
        subset = comparison if group == "All days" else comparison[comparison.day_type == group]
        delta = subset["difference"]
        rows.append(dict(period=period, group=group, days=len(delta),
                         evening_higher_days=int((delta > 0).sum()),
                         evening_higher_pct=100 * (delta > 0).mean(),
                         mean_difference=delta.mean(), median_difference=delta.median()))
    return pd.DataFrame(rows)
