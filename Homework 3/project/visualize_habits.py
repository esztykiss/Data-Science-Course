import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "sources" / "correlations.csv"
OUTPUT_FILE = ROOT / "outcome" / "millionaire_habits_visualization.png"

FEATURES = {
    "savings_rate": ("Savings rate", "Financial behavior"),
    "investment_rate": ("Investment rate", "Financial behavior"),
    "financial_education_level": ("Financial education", "Financial behavior"),
    "large_purchase_planning": ("Plans large purchases", "Financial behavior"),
    "long_term_investing_score": ("Long-term investing", "Financial behavior"),
    "retirement_planning_score": ("Retirement planning", "Financial behavior"),
    "weekly_planning": ("Weekly planning", "Habits and routines"),
    "habit_tracking": ("Habit tracking", "Habits and routines"),
    "financial_literacy_score": ("Financial literacy", "Habits and routines"),
    "exercise_consistency_score": ("Exercise consistency", "Habits and routines"),
    "sleep_duration_hours": ("Sleep duration", "Habits and routines"),
    "overall_habit_consistency_score": ("Overall habit consistency", "Habits and routines"),
    "budget_consistency_score": ("Budget consistency", "Habits and routines"),
    "delayed_gratification_score": ("Delayed gratification", "Habits and routines"),
    "automatic_savings": ("Automatic savings", "Habits and routines"),
    "invests_regularly": ("Invests regularly", "Habits and routines"),
}

COLORS = {
    "Financial behavior": "#087F70",
    "Habits and routines": "#E56B4B",
}


def load_correlations():
    with SOURCE_FILE.open(newline="", encoding="utf-8") as csv_file:
        rows = {
            row["variable"]: float(row["correlation_with_millionaire_status"])
            for row in csv.DictReader(csv_file)
            if row["correlation_with_millionaire_status"].strip()
        }

    missing = set(FEATURES) - rows.keys()
    if missing:
        raise ValueError(f"Selected variables missing from source CSV: {sorted(missing)}")

    return sorted(FEATURES, key=lambda name: rows[name], reverse=True), rows


def make_chart():
    feature_order, correlations = load_correlations()
    values = [correlations[name] for name in feature_order]
    labels = [FEATURES[name][0] for name in feature_order]
    groups = [FEATURES[name][1] for name in feature_order]
    positions = np.arange(len(feature_order))

    fig = plt.figure(figsize=(15, 10), facecolor="#F5F7F2")
    ax = fig.add_axes([0.31, 0.19, 0.62, 0.50], facecolor="#F5F7F2")

    fig.text(0.075, 0.925, "MONEY, HABITS & THE DATA", color="#087F70", fontsize=11,
             fontweight="bold", family="DejaVu Sans")
    fig.text(0.075, 0.865, "Savings rate stands apart.", color="#18332E", fontsize=29,
             fontweight="bold", family="DejaVu Sans")
    fig.text(0.075, 0.823,
             "Most measured routines barely move with millionaire status in this dataset.",
             color="#4C625C", fontsize=13, family="DejaVu Sans")

    fig.text(0.075, 0.755, "CORRELATION WITH MILLIONAIRE STATUS", color="#18332E",
             fontsize=10, fontweight="bold", family="DejaVu Sans")
    fig.text(0.075, 0.723, "Pearson r  ·  teal: financial behavior  ·  coral: habits and routines",
             color="#64746F", fontsize=10, family="DejaVu Sans")

    ax.axvspan(-0.01, 0.01, color="#E6ECE6", zorder=0)
    ax.axvline(0, color="#8A9993", linewidth=1.2, zorder=1)
    ax.set_xlim(-0.045, 0.36)
    ax.set_ylim(-0.8, len(feature_order) - 0.2)
    ax.set_yticks(positions, labels, fontsize=11, color="#263D37")
    ax.invert_yaxis()
    ax.set_xticks([-0.02, 0, 0.1, 0.2, 0.3])
    ax.set_xticklabels(["−0.02", "0", ".10", ".20", ".30"], fontsize=10, color="#64746F")
    ax.xaxis.grid(True, color="#DCE3DC", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, pad=12)
    ax.tick_params(axis="x", length=0, pad=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("Correlation coefficient (r)", fontsize=10, color="#64746F", labelpad=12)

    for position, value, feature, group in zip(positions, values, feature_order, groups):
        color = COLORS[group]
        ax.hlines(position, 0, value, color=color, linewidth=3, alpha=0.78, zorder=2)
        ax.scatter(value, position, s=72, color=color, edgecolor="#F5F7F2", linewidth=1.5, zorder=3)
        ax.text(value + 0.009, position, f"{value:+.3f}", va="center", ha="left",
                fontsize=9, fontweight="bold", color="#263D37")

    for label, group in zip(ax.get_yticklabels(), groups):
        label.set_color(COLORS[group])

    fig.text(0.075, 0.164, "THE STANDOUT", color="#087F70", fontsize=9,
             fontweight="bold", family="DejaVu Sans")
    fig.text(0.075, 0.126, "Savings rate  +0.319", color="#18332E", fontsize=16,
             fontweight="bold", family="DejaVu Sans")
    fig.text(0.075, 0.095, "All 10 routine measures shown are within ±0.01 of zero.",
             color="#4C625C", fontsize=10, family="DejaVu Sans")

    fig.text(0.075, 0.050,
             "Synthetic data, not real people. Correlation is not causation; values are dataset-provided.",
             color="#64746F", fontsize=9, family="DejaVu Sans")
    fig.text(0.925, 0.050, "SOURCE  datascikhan · Kaggle", ha="right",
             color="#64746F", fontsize=9, family="DejaVu Sans")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FILE, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved {OUTPUT_FILE}")


if __name__ == "__main__":
    make_chart()