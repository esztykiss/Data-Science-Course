import argparse
import csv
import json
import math
import zipfile
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.cm import ScalarMappable


ROOT = Path(__file__).resolve().parents[1]
BOUNDARIES_FILE = ROOT / "sources" / "ne_110m_admin_0_countries.geojson"
OUTPUT_FILE = ROOT / "outcome" / "millionaire_habits_country_savings_rate.png"
DEFAULT_DATA_FILE = ROOT / "sources" / "Millionaire_Habits_Dataset.csv"

COUNTRY_ALIASES = {
    "United States": "United States of America",
}
SINGAPORE_COORDINATES = (103.82, 1.35)

BACKGROUND = "#F5F7F2"
INK = "#18332E"
MUTED = "#61736D"
LAND = "#E7ECE7"
GRID = "#D6DED8"
LOW_RATE = 25.5
HIGH_RATE = 29.0
PALETTE = "YlGnBu"


@contextmanager
def open_dataset(path):
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            member_name = "Millionaire_Habits_Dataset.csv"
            if member_name not in archive.namelist():
                raise ValueError(
                    f"{path} does not contain {member_name}; use the full Kaggle dataset archive."
                )
            with archive.open(member_name) as binary_file:
                import io

                with io.TextIOWrapper(
                    binary_file, encoding="utf-8-sig", newline=""
                ) as text_file:
                    yield text_file
        return

    with path.open(newline="", encoding="utf-8-sig") as text_file:
        yield text_file


def load_country_means(dataset_path):
    savings_totals = defaultdict(float)
    savings_counts = defaultdict(int)
    row_count = 0

    with open_dataset(dataset_path) as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {"country", "savings_rate"}
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                f"Dataset is missing required columns: {', '.join(sorted(missing_columns))}"
            )

        for row_count, row in enumerate(reader, start=1):
            country = (row["country"] or "").strip()
            if not country:
                raise ValueError(f"Missing country value in dataset row {row_count + 1}.")

            raw_value = (row["savings_rate"] or "").strip()
            if not raw_value:
                continue
            try:
                value = float(raw_value)
            except ValueError as error:
                raise ValueError(
                    f"Invalid savings_rate in dataset row {row_count + 1}: {raw_value!r}"
                ) from error

            if not math.isfinite(value) or not -0.20 <= value <= 0.75:
                raise ValueError(
                    f"savings_rate out of expected range in dataset row "
                    f"{row_count + 1}: {value}"
                )

            savings_totals[country] += value * 100
            savings_counts[country] += 1

    if row_count == 0:
        raise ValueError("The dataset contains no records.")
    if not savings_counts:
        raise ValueError("The dataset contains no usable savings_rate values.")

    country_means = {
        country: savings_totals[country] / savings_counts[country]
        for country in savings_totals
    }
    return country_means, savings_counts, row_count


def mollweide(longitude, latitude):
    lam = math.radians(longitude)
    phi = math.radians(max(-89.999999, min(89.999999, latitude)))
    if abs(abs(phi) - math.pi / 2) < 1e-8:
        theta = math.copysign(math.pi / 2, phi)
    else:
        theta = phi
        target = math.pi * math.sin(phi)
        for _ in range(12):
            residual = 2 * theta + math.sin(2 * theta) - target
            derivative = 2 + 2 * math.cos(2 * theta)
            if abs(derivative) < 1e-12:
                break
            step = residual / derivative
            theta -= step
            if abs(step) < 1e-10:
                break

    return (
        (2 * math.sqrt(2) / math.pi) * lam * math.cos(theta),
        math.sqrt(2) * math.sin(theta),
    )


def draw_ring(ax, ring, facecolor):
    points = [mollweide(longitude, latitude) for longitude, latitude, *_ in ring]
    xs, ys = zip(*points)
    ax.fill(
        xs,
        ys,
        facecolor=facecolor,
        edgecolor="#FFFFFF",
        linewidth=0.45,
        zorder=2,
        clip_on=True,
    )


def feature_polygons(geometry):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    return []


def draw_grid(ax):
    for latitude in (-60, -30, 0, 30, 60):
        points = [mollweide(longitude, latitude) for longitude in range(-180, 181, 2)]
        xs, ys = zip(*points)
        ax.plot(xs, ys, color=GRID, linewidth=0.55, zorder=1)

    for longitude in (-120, -60, 0, 60, 120):
        points = [mollweide(longitude, latitude) for latitude in range(-88, 89, 2)]
        xs, ys = zip(*points)
        ax.plot(xs, ys, color=GRID, linewidth=0.55, zorder=1)


def draw_map(ax, country_means):
    with BOUNDARIES_FILE.open(encoding="utf-8") as geojson_file:
        features = json.load(geojson_file)["features"]

    normalization = colors.Normalize(vmin=LOW_RATE, vmax=HIGH_RATE, clip=True)
    colormap = plt.get_cmap(PALETTE)
    found_countries = set()

    draw_grid(ax)
    for feature in features:
        natural_earth_name = feature["properties"]["ADMIN"]
        if natural_earth_name == "Antarctica":
            continue
        country = next(
            (
                name
                for name, alias in COUNTRY_ALIASES.items()
                if alias == natural_earth_name
            ),
            natural_earth_name,
        )
        mean = country_means.get(country)
        if mean is None:
            facecolor = LAND
        else:
            found_countries.add(country)
            facecolor = colormap(normalization(mean))

        for polygon in feature_polygons(feature["geometry"]):
            if not polygon:
                continue
            draw_ring(ax, polygon[0], facecolor)
            for hole in polygon[1:]:
                draw_ring(ax, hole, BACKGROUND)

    missing_countries = set(country_means) - found_countries - {"Singapore"}
    if missing_countries:
        raise ValueError(
            "No Natural Earth boundary found for: "
            + ", ".join(sorted(missing_countries))
        )

    if "Singapore" in country_means:
        x, y = mollweide(*SINGAPORE_COORDINATES)
        ax.scatter(
            [x],
            [y],
            s=70,
            color=colormap(normalization(country_means["Singapore"])),
            edgecolor="#FFFFFF",
            linewidth=1.1,
            zorder=4,
        )

    ax.set_xlim(-2.78, 2.78)
    ax.set_ylim(-1.46, 1.46)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    return ScalarMappable(norm=normalization, cmap=colormap)


def draw_ranked_rates(ax, country_means):
    ranked = sorted(country_means.items(), key=lambda item: item[1], reverse=True)
    countries = [country for country, _ in ranked]
    rates = [rate for _, rate in ranked]
    positions = list(range(len(ranked)))
    highest_country, highest_rate = ranked[0]

    ax.set_facecolor(BACKGROUND)
    ax.barh(
        positions,
        [rate - LOW_RATE for rate in rates],
        left=LOW_RATE,
        color=["#087F70" if index == 0 else "#78AFA4" for index in positions],
        height=0.67,
        zorder=3,
    )
    ax.set_yticks(positions, countries, fontsize=8.4, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(LOW_RATE, HIGH_RATE)
    ax.set_xticks([26, 27, 28, 29], [f"{tick}%" for tick in (26, 27, 28, 29)])
    ax.tick_params(axis="x", labelsize=8, colors=MUTED, length=0, pad=7)
    ax.tick_params(axis="y", length=0, pad=7)
    ax.grid(axis="x", color=GRID, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for position, rate in zip(positions, rates):
        ax.text(
            rate + 0.06,
            position,
            f"{rate:.1f}%",
            va="center",
            fontsize=8,
            color=INK,
            fontweight="bold" if position == 0 else "normal",
        )

    return highest_country, highest_rate, min(rates), max(rates)


def make_chart(dataset_path):
    country_means, country_counts, row_count = load_country_means(dataset_path)
    fig = plt.figure(figsize=(19, 11), facecolor=BACKGROUND)
    map_ax = fig.add_axes([0.035, 0.19, 0.60, 0.67], facecolor=BACKGROUND)
    ranked_ax = fig.add_axes([0.69, 0.19, 0.27, 0.67], facecolor=BACKGROUND)

    mappable = draw_map(map_ax, country_means)
    highest_country, highest_rate, lowest_rate, upper_rate = draw_ranked_rates(
        ranked_ax, country_means
    )

    fig.text(
        0.055,
        0.948,
        "MILLIONAIRE HABITS  /  COUNTRY SAVINGS",
        color="#087F70",
        fontsize=10,
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.895,
        "Where is the average savings rate highest?",
        color=INK,
        fontsize=24,
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.861,
        "Country average savings rate · percent of income saved",
        color=MUTED,
        fontsize=11,
    )
    fig.text(
        0.945,
        0.948,
        f"{row_count:,} RECORDS  ·  {len(country_means)} COUNTRIES",
        ha="right",
        color=MUTED,
        fontsize=9,
        fontweight="bold",
    )

    ranked_ax.set_title(
        "COUNTRY RANKING",
        loc="left",
        fontsize=10,
        color=INK,
        fontweight="bold",
        pad=13,
    )
    fig.text(
        0.69,
        0.838,
        f"Highest: {highest_country}  ·  {highest_rate:.2f}%",
        color="#087F70",
        fontsize=10,
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.132,
        f"Country means range from {lowest_rate:.1f}% to {upper_rate:.1f}% "
        f"({upper_rate - lowest_rate:.1f} pp spread); bars use a zoomed 25.5–29% axis.",
        color=INK,
        fontsize=10,
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.101,
        "Colors show the same rate scale as the country ranking.",
        color=MUTED,
        fontsize=9,
    )

    colorbar_ax = fig.add_axes([0.14, 0.065, 0.34, 0.018])
    colorbar = fig.colorbar(mappable, cax=colorbar_ax, orientation="horizontal")
    colorbar.set_ticks([26, 27, 28, 29])
    colorbar.set_ticklabels(["26%", "27%", "28%", "29%"])
    colorbar.ax.tick_params(labelsize=8, colors=MUTED, length=0, pad=4)
    colorbar.outline.set_visible(False)

    fig.text(
        0.055,
        0.027,
        "Synthetic data, not a representative survey. Country means summarize records in this dataset, not real national populations.",
        color=MUTED,
        fontsize=8.3,
    )
    fig.text(
        0.945,
        0.027,
        f"Source: datascikhan · Kaggle  |  {sum(country_counts.values()):,} valid savings-rate values",
        ha="right",
        color=MUTED,
        fontsize=8.3,
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FILE, dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved {OUTPUT_FILE}")
    print(
        f"Analyzed {row_count:,} rows across {len(country_means)} countries. "
        f"Highest average: {highest_country} ({highest_rate:.2f}%)."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Create a country map of average savings rates."
    )
    parser.add_argument(
        "dataset",
        nargs="?",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help=(
            "Full Millionaire_Habits_Dataset.csv file or the original Kaggle ZIP "
            f"(default: {DEFAULT_DATA_FILE})"
        ),
    )
    args = parser.parse_args()

    if not args.dataset.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {args.dataset}. Download the full Millionaire Habits "
            "dataset from https://www.kaggle.com/datasets/datascikhan/"
            "millionaire-habits-dataset and pass the CSV or ZIP path."
        )
    make_chart(args.dataset)


if __name__ == "__main__":
    main()
