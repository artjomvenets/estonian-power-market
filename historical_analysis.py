import pandas as pd
import matplotlib.pyplot as plt

from market_data import load_prices

# Load the same four-week period from our validated cache.
start_date = "2026-08-11"
end_date = "2026-09-07"

history = load_prices(start_date, end_date)

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
plt.show()