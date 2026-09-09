"""Consistent, exportable figures for the repository README."""
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

OUTPUT = Path(__file__).resolve().parent / "outputs"
NAVY, TEAL, ORANGE = "#172D46", "#007F80", "#C75B39"


def canvas(title, subtitle):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.labelcolor": NAVY, "text.color": NAVY,
                         "xtick.color": NAVY, "ytick.color": NAVY,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(12, 6.3))
    fig.subplots_adjust(left=.09, right=.97, bottom=.20, top=.76)
    fig.text(.09, .93, "ESTONIAN POWER MARKET  /  RESEARCH NOTE", fontsize=9, color=TEAL, weight="bold")
    fig.text(.09, .87, title, fontsize=21, weight="bold")
    fig.text(.09, .81, subtitle, fontsize=10)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#E5EAF0")
    fig.text(.09, .055, "Source: Volton Technology · public-data.volton.energy · CC-BY-4.0", fontsize=8, color="#536579")
    return fig, ax


def save(fig, name):
    OUTPUT.mkdir(exist_ok=True)
    fig.savefig(OUTPUT / f"{name}.png", dpi=180, facecolor="white")
    plt.close(fig)


def profile_chart(profile):
    fig, ax = canvas("Evening prices lead the daily profile",
                     "11 Aug–7 Sep 2026 · 28 days · hourly averages in Estonian local time")
    ax.fill_between(profile.index, profile.p25, profile.p75, color=TEAL, alpha=.14, label="Middle 50% of days")
    ax.plot(profile.index, profile["mean"], color=TEAL, linewidth=2.4, label="Mean")
    ax.plot(profile.index, profile["median"], color=NAVY, linestyle="--", linewidth=1.7, label="Median")
    ax.set(xlim=(0, 23), ylim=(0, None), ylabel="Price (EUR/MWh)", xlabel="Local hour · 20 means 20:00–21:00")
    ax.set_xticks(range(0,24,2))
    ax.legend(frameon=False, loc="upper left")
    fig.text(.09,.115,"Shading describes observed dispersion; it is not a forecast or confidence interval.",fontsize=9)
    save(fig,"hourly_price_profile")


def difference_chart(comparison):
    dates = pd.to_datetime(comparison.index)
    delta = comparison["difference"]
    count = int((delta > 0).sum())
    fig, ax = canvas(f"Evening exceeded afternoon on {count} of {len(delta)} days",
                     "14 Jul–7 Sep 2026 · evening 19:00–23:00 minus afternoon 13:00–16:00")
    colors = [TEAL if x > 0 else ORANGE for x in delta]
    ax.bar(dates, delta, width=.75, color=colors)
    ax.axhline(0,color=NAVY,linewidth=.8)
    boundary=pd.Timestamp("2026-08-10 12:00")
    ax.axvline(boundary,color="#758496",linestyle="--",linewidth=1)
    ax.text(pd.Timestamp("2026-07-15"),.95,"Earlier check period",transform=ax.get_xaxis_transform(),va="top",fontsize=9)
    ax.text(pd.Timestamp("2026-08-12"),.95,"Original exploration period",transform=ax.get_xaxis_transform(),va="top",fontsize=9)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO,interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set(ylabel="Daily price difference (EUR/MWh)",ylim=(min(-35,delta.min()-15),delta.max()*1.23))
    ax.annotate("7 Sep: −11.55", xy=(dates[-1],delta.iloc[-1]),xytext=(-95,-20),textcoords="offset points",color=ORANGE,fontsize=9,arrowprops=dict(arrowstyle="-",color=ORANGE))
    fig.text(.09,.115,"Fixed windows selected from the original period. Historical differences are not trading profits.",fontsize=9)
    save(fig,"daily_price_difference")
