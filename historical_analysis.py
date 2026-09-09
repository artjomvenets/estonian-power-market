import requests
import pandas as pd

# Four complete weeks, ending on the day we already inspected.
start_date = "2026-08-11"
end_date = "2026-09-07"

dates = pd.date_range(start=start_date, end=end_date, freq="D")

# Collect valid daily tables and record unavailable archives separately.
daily_tables = []
missing_dates = []

with requests.Session() as session:
    for date in dates:
        date_text = date.strftime("%Y-%m-%d")
        url = (
            "https://public-data.volton.energy/v1/day-ahead-spot/"
            f"{date_text}.json"
        )

        print("Downloading:", date_text, flush=True)
        response = session.get(url, timeout=30)

        # A missing archive is recorded, never replaced with invented prices.
        if response.status_code == 404:
            missing_dates.append(date_text)
            print("  Archive unavailable")
            continue

        # Stop for other HTTP errors instead of treating them as missing data.
        response.raise_for_status()
        data = response.json()

        # Verify that the archive describes the expected dataset.
        meta = data["meta"]

        if meta.get("unit") != "EUR/MWh":
            raise ValueError(f"{date_text}: unexpected price unit")

        if meta.get("resolution_minutes") != 15:
            raise ValueError(f"{date_text}: unexpected interval length")

        # Build and prepare the daily table.
        df = pd.DataFrame(data["rows"])
        df["mtu_start"] = pd.to_datetime(df["mtu_start"], utc=True)
        df["time_estonia"] = df["mtu_start"].dt.tz_convert("Europe/Tallinn")
        df["price_eur_mwh"] = pd.to_numeric(
            df["price_eur_mwh"], errors="raise"
        )
        df = df.sort_values("mtu_start").reset_index(drop=True)

        # Require every expected interval, exactly once.
        day_start = pd.Timestamp(date_text, tz="Europe/Tallinn")
        day_end = day_start + pd.DateOffset(days=1)

        expected = pd.date_range(
            start=day_start,
            end=day_end,
            freq="15min",
            inclusive="left",
        )

        actual = pd.DatetimeIndex(df["time_estonia"])

        if not actual.equals(expected):
            raise ValueError(f"{date_text}: missing, extra, or duplicate intervals")

        if df["price_eur_mwh"].isna().any():
            raise ValueError(f"{date_text}: missing prices")

        daily_tables.append(df)

# Report coverage before calculating anything.
print("\nCOVERAGE")
print("Requested days:", len(dates))
print("Valid days:", len(daily_tables))
print("Unavailable archives:", len(missing_dates))

if missing_dates:
    print("Unavailable dates:", ", ".join(missing_dates))
    raise SystemExit(
        "Stopped: the requested period is incomplete. "
        "Review coverage before drawing conclusions."
    )

# Stack the daily tables into one chronological table.
history = pd.concat(daily_tables, ignore_index=True)
history = history.sort_values("mtu_start").reset_index(drop=True)

# Add labels that will help us compare days.
history["delivery_date"] = history["time_estonia"].dt.date
history["hour"] = history["time_estonia"].dt.hour
history["weekday"] = history["time_estonia"].dt.day_name()

# Calculate a separate summary for each delivery date.
daily_summary = history.groupby("delivery_date").agg(
    intervals=("price_eur_mwh", "size"),
    average=("price_eur_mwh", "mean"),
    minimum=("price_eur_mwh", "min"),
    maximum=("price_eur_mwh", "max"),
)

print("\nDAILY SUMMARY — prices in EUR/MWh")
print(daily_summary.round(2).to_string())

print("\nFULL PERIOD")
print("Total intervals:", len(history))
print(f"Average price: {history['price_eur_mwh'].mean():.2f} EUR/MWh")
print("Negative-price intervals:", (history["price_eur_mwh"] < 0).sum())
# Calculate one average price per local hour for each day.
hourly_by_day = (
    history.groupby(["delivery_date", "hour"])["price_eur_mwh"]
    .mean()
    .unstack("hour")
)

# Each row is a day; each column is an hour from 0 to 23.
hourly_profile = pd.DataFrame({
    "mean": hourly_by_day.mean(),
    "median": hourly_by_day.median(),
    "p25": hourly_by_day.quantile(0.25),
    "p75": hourly_by_day.quantile(0.75),
})

print("\nPRICE PROFILE BY LOCAL HOUR — EUR/MWh")
print(hourly_profile.round(2).to_string())

# Count all hours tied for each day's highest hourly average.
daily_maximum = hourly_by_day.max(axis=1)
peak_hours = hourly_by_day.eq(daily_maximum, axis="index")
peak_counts = peak_hours.sum(axis=0)

print("\nDAYS EACH HOUR HAD THE HIGHEST HOURLY AVERAGE")
print(peak_counts.to_string())
print("Ties are counted, so the total may exceed 28.")

# Plot the typical profile and its variation across days.
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(11, 5))

ax.fill_between(
    hourly_profile.index,
    hourly_profile["p25"],
    hourly_profile["p75"],
    color="tab:blue",
    alpha=0.18,
    label="Middle 50% of daily hourly averages",
)

ax.plot(
    hourly_profile.index,
    hourly_profile["mean"],
    color="tab:blue",
    marker="o",
    markersize=3,
    label="Mean",
)

ax.plot(
    hourly_profile.index,
    hourly_profile["median"],
    color="tab:orange",
    linestyle="--",
    label="Median",
)

ax.set(
    title=f"Estonian electricity price profile — {start_date} to {end_date}",
    xlabel="Estonian local hour (0 = 00:00–01:00)",
    ylabel="Hourly average price (EUR/MWh)",
    xlim=(0, 23),
)
ax.set_xticks(range(24))
ax.grid(axis="y", alpha=0.25)
ax.legend()

fig.text(
    0.01,
    0.01,
    "Source: Volton Technology, public-data.volton.energy, CC-BY-4.0",
    fontsize=8,
)
fig.tight_layout(rect=(0, 0.04, 1, 1))

plt.show()
# Compare evening and afternoon prices within each individual day.
# Each selected number is the START of a one-hour interval.
afternoon_hours = [13, 14, 15]       # 13:00–16:00
evening_hours = [19, 20, 21, 22]    # 19:00–23:00

comparison = pd.DataFrame({
    "afternoon_average": hourly_by_day[afternoon_hours].mean(axis=1),
    "evening_average": hourly_by_day[evening_hours].mean(axis=1),
})

comparison["evening_minus_afternoon"] = (
    comparison["evening_average"] - comparison["afternoon_average"]
)

# Separate weekdays and weekends using each delivery date.
comparison["day_type"] = [
    "Weekend" if pd.Timestamp(date).dayofweek >= 5 else "Weekday"
    for date in comparison.index
]

print("\nEVENING VERSUS AFTERNOON — EUR/MWh")
print(comparison.round(2).to_string())

difference = comparison["evening_minus_afternoon"]

print("\nWITHIN-DAY COMPARISON")
print("Days evening was more expensive:", (difference > 0).sum())
print("Days evening was cheaper:", (difference < 0).sum())
print("Days with equal averages:", (difference == 0).sum())
print(f"Mean difference: {difference.mean():.2f} EUR/MWh")
print(f"Median difference: {difference.median():.2f} EUR/MWh")

print("\nCOMPARISON BY DAY TYPE")
summary = comparison.groupby("day_type").agg(
    days=("evening_minus_afternoon", "size"),
    mean_difference=("evening_minus_afternoon", "mean"),
    median_difference=("evening_minus_afternoon", "median"),
)
print(summary.round(2).to_string())