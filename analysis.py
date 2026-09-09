import requests
import pandas as pd
import matplotlib.pyplot as plt

# Download one completed delivery day.
delivery_date = "2026-09-07"
url = (
    "https://public-data.volton.energy/v1/day-ahead-spot/"
    f"{delivery_date}.json"
)

print("Downloading:", delivery_date)
response = requests.get(url, timeout=30)
response.raise_for_status()
data = response.json()

# Convert the records into a table.
df = pd.DataFrame(data["rows"])
df["mtu_start"] = pd.to_datetime(df["mtu_start"], utc=True)
df["time_estonia"] = df["mtu_start"].dt.tz_convert("Europe/Tallinn")
df["price_eur_mwh"] = pd.to_numeric(df["price_eur_mwh"], errors="raise")
df = df.sort_values("mtu_start").reset_index(drop=True)

# Check that the archive contains every expected interval.
start = pd.Timestamp(delivery_date, tz="Europe/Tallinn")
end = start + pd.DateOffset(days=1)

expected = pd.date_range(
    start=start,
    end=end,
    freq="15min",
    inclusive="left",
)

actual = pd.DatetimeIndex(df["time_estonia"])

if not actual.equals(expected):
    raise ValueError("The archive does not match the expected delivery intervals.")

if df["price_eur_mwh"].isna().any():
    raise ValueError("The archive contains missing prices.")

# Calculate summary statistics.
prices = df["price_eur_mwh"]

print("\nPRICE SUMMARY —", delivery_date)
print("Number of intervals:", len(df))
print(f"Average: {prices.mean():.2f} EUR/MWh")
print(f"Median:  {prices.median():.2f} EUR/MWh")
print(f"Minimum: {prices.min():.2f} EUR/MWh")
print(f"Maximum: {prices.max():.2f} EUR/MWh")
print(f"Range:   {prices.max() - prices.min():.2f} EUR/MWh")
print("Negative-price intervals:", (prices < 0).sum())

# Show all intervals tied for the lowest and highest prices.
print("\nCHEAPEST INTERVALS")
print(
    df.loc[
        prices == prices.min(),
        ["time_estonia", "price_eur_mwh"],
    ].to_string(index=False)
)

print("\nMOST EXPENSIVE INTERVALS")
print(
    df.loc[
        prices == prices.max(),
        ["time_estonia", "price_eur_mwh"],
    ].to_string(index=False)
)

# Convert local times to decimal hours, such as 01:15 = 1.25.
hours = (
    df["time_estonia"].dt.hour
    + df["time_estonia"].dt.minute / 60
)

# Extend the final interval to midnight.
edges = hours.tolist() + [24.0]

# Draw a step chart: each price applies for 15 minutes.
fig, ax = plt.subplots(figsize=(11, 5))

ax.stairs(
    prices.to_numpy(),
    edges,
    color="tab:blue",
    linewidth=1.5,
    label="15-minute price",
)

ax.axhline(
    prices.mean(),
    color="tab:orange",
    linestyle="--",
    label="Daily average",
)
ax.axhline(0, color="grey", linewidth=0.8)

ax.set(
    title=f"Estonian day-ahead electricity prices — {delivery_date}",
    xlabel="Estonian local time (hour)",
    ylabel="Price (EUR/MWh)",
    xlim=(0, 24),
)
ax.set_xticks(range(0, 25, 2))
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