import argparse
import csv
import html
import json
import math
import zipfile
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_FILE = ROOT / "sources" / "Millionaire_Habits_Dataset.csv"
PNG_FILE = ROOT / "outcome" / "millionaire_habits_wealth_ladder.png"
HTML_FILE = ROOT / "project" / "millionaire_habits_wealth_ladder.html"

WEALTH_ORDER = [
    "negative_net_worth",
    "zero_to_10k",
    "10k_to_50k",
    "50k_to_100k",
    "100k_to_250k",
    "250k_to_500k",
    "500k_to_1m",
    "1m_to_2.5m",
    "2.5m_to_5m",
    "5m_to_10m",
    "10m_plus",
]
WEALTH_LABELS = {
    "negative_net_worth": "Negative",
    "zero_to_10k": "$0–10k",
    "10k_to_50k": "$10–50k",
    "50k_to_100k": "$50–100k",
    "100k_to_250k": "$100–250k",
    "250k_to_500k": "$250–500k",
    "500k_to_1m": "$500k–1m",
    "1m_to_2.5m": "$1–2.5m",
    "2.5m_to_5m": "$2.5–5m",
    "5m_to_10m": "$5–10m",
    "10m_plus": "$10m+",
}
METRICS = {
    "portfolio_diversification_score": {
        "label": "Portfolio diversification",
        "short": "Diversification",
        "unit": "score / 100",
        "format": "score",
        "color": "#16877B",
        "description": "Reported portfolio-diversification score.",
        "format_value": lambda value: f"{value:.1f}",
    },
    "passive_income_ratio": {
        "label": "Passive income share",
        "short": "Passive income",
        "unit": "% of income",
        "format": "percent",
        "color": "#5379A8",
        "description": "Passive income as a share of income.",
        "format_value": lambda value: f"{value:.1f}%",
    },
    "savings_rate": {
        "label": "Savings rate",
        "short": "Savings rate",
        "unit": "% of income",
        "format": "percent",
        "color": "#D58B42",
        "description": "Share of income saved.",
        "format_value": lambda value: f"{value:.1f}%",
    },
    "debt_stress_score": {
        "label": "Debt stress",
        "short": "Debt stress",
        "unit": "score / 100",
        "format": "score",
        "color": "#D56553",
        "description": "Reported debt-stress score; higher means more stress.",
        "format_value": lambda value: f"{value:.1f}",
    },
    "emergency_fund_months": {
        "label": "Emergency fund",
        "short": "Emergency fund",
        "unit": "months covered",
        "format": "months",
        "color": "#7C8F4B",
        "description": "Months of expenses covered by the emergency fund.",
        "format_value": lambda value: f"{value:.1f} mo",
    },
}

BACKGROUND = "#F5F7F2"
INK = "#18332E"
MUTED = "#61736D"
GRID = "#DCE3DC"
ACCENT = "#087F70"


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


def percentile(sorted_values, fraction):
    position = (len(sorted_values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def load_summary(dataset_path):
    observations = {
        wealth: {metric: [] for metric in METRICS}
        for wealth in WEALTH_ORDER
    }
    row_count = 0
    required_columns = {"wealth_category", *METRICS}

    with open_dataset(dataset_path) as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                f"Dataset is missing required columns: {', '.join(sorted(missing_columns))}"
            )

        for row_count, row in enumerate(reader, start=1):
            wealth = (row["wealth_category"] or "").strip()
            if wealth not in observations:
                raise ValueError(
                    f"Unexpected wealth_category in dataset row {row_count + 1}: {wealth!r}"
                )

            for metric in METRICS:
                raw_value = (row[metric] or "").strip()
                if not raw_value:
                    continue
                try:
                    value = float(raw_value)
                except ValueError as error:
                    raise ValueError(
                        f"Invalid {metric} in dataset row {row_count + 1}: {raw_value!r}"
                    ) from error
                if not math.isfinite(value):
                    raise ValueError(
                        f"Non-finite {metric} in dataset row {row_count + 1}."
                    )
                if METRICS[metric]["format"] == "percent":
                    value *= 100
                observations[wealth][metric].append(value)

    if row_count == 0:
        raise ValueError("The dataset contains no records.")

    summary = {}
    for wealth in WEALTH_ORDER:
        populated = [
            values for values in observations[wealth].values() if values
        ]
        if not populated:
            raise ValueError(f"No usable measurements for wealth category {wealth}.")

        record = {
            "label": WEALTH_LABELS[wealth],
            "n": len(populated[0]),
            "metrics": {},
        }
        for metric, values in observations[wealth].items():
            if not values:
                continue
            values.sort()
            record["metrics"][metric] = {
                "q1": percentile(values, 0.25),
                "median": percentile(values, 0.50),
                "q3": percentile(values, 0.75),
            }
        summary[wealth] = record

    return summary, row_count


def plot_static_summary(summary, row_count):
    fig, axes = plt.subplots(
        len(METRICS),
        1,
        figsize=(15, 12),
        sharex=True,
        facecolor=BACKGROUND,
    )
    fig.subplots_adjust(left=0.22, right=0.91, top=0.79, bottom=0.14, hspace=0.36)

    x = np.arange(len(WEALTH_ORDER))
    highlight = WEALTH_ORDER.index("1m_to_2.5m")
    for ax, (metric, details) in zip(axes, METRICS.items()):
        medians = [
            summary[wealth]["metrics"][metric]["median"] for wealth in WEALTH_ORDER
        ]
        lower = [
            summary[wealth]["metrics"][metric]["q1"] for wealth in WEALTH_ORDER
        ]
        upper = [
            summary[wealth]["metrics"][metric]["q3"] for wealth in WEALTH_ORDER
        ]
        ax.axvspan(highlight - 0.45, highlight + 0.45, color="#E6EEE8", zorder=0)
        ax.fill_between(x, lower, upper, color=details["color"], alpha=0.15, zorder=1)
        ax.plot(x, medians, color=details["color"], linewidth=2.2, zorder=2)
        ax.scatter(
            x,
            medians,
            color=details["color"],
            edgecolor=BACKGROUND,
            linewidth=1,
            s=34,
            zorder=3,
        )
        ax.set_ylabel(
            details["label"],
            rotation=0,
            ha="right",
            va="center",
            labelpad=15,
            fontsize=9,
            color=INK,
            fontweight="bold",
        )
        ax.grid(axis="y", color=GRID, linewidth=0.7)
        ax.tick_params(axis="y", labelsize=8, colors=MUTED, length=0, pad=5)
        ax.tick_params(axis="x", length=0, pad=9)
        ax.set_xlim(-0.5, len(WEALTH_ORDER) - 0.5)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        unit_label = {
            "score / 100": "/100",
            "% of income": "% income",
            "months covered": "months",
        }[details["unit"]]
        ax.text(
            1.015,
            0.5,
            unit_label,
            transform=ax.transAxes,
            va="center",
            fontsize=7.5,
            color=MUTED,
        )

    axes[-1].set_xticks(x, [WEALTH_LABELS[wealth] for wealth in WEALTH_ORDER])
    axes[-1].tick_params(axis="x", labelsize=8, colors=INK, labelrotation=0)

    fig.text(
        0.055,
        0.958,
        "MILLIONAIRE HABITS  /  THE WEALTH LADDER",
        color=ACCENT,
        fontsize=10,
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.914,
        "Financial profiles shift as net worth climbs",
        color=INK,
        fontsize=23,
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.878,
        "Typical value (median) and middle half of records (25th–75th percentile) in each wealth tier",
        color=MUTED,
        fontsize=10,
    )
    fig.text(
        0.945,
        0.958,
        f"{row_count:,} RECORDS",
        ha="right",
        color=MUTED,
        fontsize=9,
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.094,
        "The sharpest visible step is portfolio diversification around the $1m tier; the emergency-fund median barely shifts.",
        color=INK,
        fontsize=9.5,
        fontweight="bold",
    )
    fig.text(
        0.055,
        0.068,
        "Shaded band = middle 50% of records. $1m–$2.5m tier is highlighted. Small wealth tiers have fewer records.",
        color=MUTED,
        fontsize=8.5,
    )
    fig.text(
        0.055,
        0.039,
        "Synthetic data, not a representative survey. These are descriptive associations, not causal effects or financial advice.",
        color=MUTED,
        fontsize=8,
    )
    PNG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_FILE, dpi=180, facecolor=BACKGROUND)
    plt.close(fig)


def build_html(summary, row_count):
    payload = json.dumps(
        {
            "order": WEALTH_ORDER,
            "labels": WEALTH_LABELS,
            "metrics": {
                key: {name: value for name, value in details.items() if name != "format_value"}
                for key, details in METRICS.items()
            },
            "summary": summary,
            "rowCount": row_count,
        },
        ensure_ascii=True,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    options = "\n".join(
        f'<button class="metric" data-key="{html.escape(key)}" '
        f'aria-pressed="{str(index == 0).lower()}">{html.escape(details["short"])}</button>'
        for index, (key, details) in enumerate(METRICS.items())
    )
    document = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Wealth Ladder · Millionaire Habits</title>
<style>
:root{color-scheme:light;--paper:#f5f7f2;--ink:#18332e;--muted:#61736d;--grid:#dce3dc;--accent:#087f70;--line:#e4eae3}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.shell{max-width:1320px;margin:auto;padding:30px clamp(18px,4vw,56px) 24px}
.eyebrow{font-size:.75rem;font-weight:800;letter-spacing:.13em;color:var(--accent)}
header{display:flex;justify-content:space-between;gap:24px;align-items:flex-start}
h1{font-size:clamp(2rem,4vw,3.4rem);letter-spacing:-.04em;line-height:1.02;margin:16px 0 10px}
.dek{color:var(--muted);font-size:1rem;margin:0;max-width:760px}
.record-count{font-size:.76rem;font-weight:800;color:var(--muted);white-space:nowrap;margin-top:4px}
.story{display:grid;grid-template-columns:1.2fr .8fr;gap:14px;margin:25px 0 22px}
.story-card,.chart-card,.detail{background:#fff;border:1px solid var(--line);border-radius:16px}
.story-card{padding:17px 19px}
.story-card strong{display:block;color:var(--accent);font-size:1rem;margin-bottom:5px}
.story-card p{color:var(--muted);font-size:.87rem;line-height:1.5;margin:0}
.chart-card{padding:18px 18px 12px}
.chart-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;flex-wrap:wrap}
h2{margin:0;font-size:1.04rem}
.unit{color:var(--muted);font-size:.78rem;margin-top:5px}
.controls{display:flex;gap:7px;flex-wrap:wrap;margin:15px 0 4px}
.metric{appearance:none;border:1px solid #d5dfd8;background:white;border-radius:999px;color:var(--muted);padding:8px 12px;font-family:inherit;font-size:.78rem;font-weight:600;cursor:pointer}
.metric:hover,.metric[aria-pressed=true]{background:#e6f1ed;border-color:#78afa4;color:#075e53}
.metric:focus-visible,.point:focus{outline:3px solid #e1b75c;outline-offset:2px}
#chart{display:block;width:100%;height:auto;overflow:visible}
.detail{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-top:6px;padding:15px 18px;min-height:76px}
.detail h3{margin:0 0 4px;font-size:1rem}
.detail p{margin:0;color:var(--muted);font-size:.82rem;line-height:1.45}
.detail-stat{font-size:1.15rem;font-weight:800;color:var(--accent);text-align:right;white-space:nowrap}
.hint{font-size:.77rem;color:var(--muted);margin:10px 2px 0}
.foot{border-top:1px solid var(--line);margin-top:22px;padding-top:13px;color:var(--muted);font-size:.76rem;line-height:1.55}
.tooltip{position:fixed;pointer-events:none;z-index:3;display:none;background:#18332e;color:white;padding:9px 11px;border-radius:8px;font-size:.76rem;line-height:1.5;box-shadow:0 5px 22px #18332e30}
.point{cursor:pointer}
@media(max-width:720px){.shell{padding:20px 14px}.record-count{font-size:.65rem}.story{grid-template-columns:1fr}.chart-card{padding:13px 8px}.metric{padding:7px 9px;font-size:.7rem}.detail{align-items:flex-start;flex-direction:column}.detail-stat{text-align:left}.foot{font-size:.7rem}}
</style>
</head>
<body>
<main class="shell">
<header><div><div class="eyebrow">MILLIONAIRE HABITS / THE WEALTH LADDER</div>
<h1>Financial profiles shift as net worth climbs</h1>
<p class="dek">Explore what changes—and what stays almost flat—across the dataset's wealth tiers.</p></div>
<div class="record-count">__ROW_COUNT__ RECORDS</div></header>
<section class="story" aria-label="Key findings">
<div class="story-card"><strong>A sudden step in diversification</strong><p>The median portfolio-diversification score rises from 55.5 in the $500k–$1m tier to 77.8 in the $1m–$2.5m tier, then reaches the score ceiling of 100 above $2.5m.</p></div>
<div class="story-card"><strong>One measure barely moves</strong><p>Median emergency-fund coverage stays between about 2.1 and 2.8 months across all wealth tiers.</p></div>
</section>
<section class="chart-card" aria-label="Interactive wealth profile chart">
<div class="chart-head"><div><h2 id="chart-title">Portfolio diversification by wealth tier</h2><div class="unit" id="chart-unit">Median and middle 50% of records · score / 100</div></div>
<div class="record-count">Click a point to pin a tier below</div></div>
<nav class="controls" aria-label="Choose financial measure">__OPTIONS__</nav>
<svg id="chart" viewBox="0 0 1080 440" role="img" aria-label="Median financial measure and interquartile ranges by wealth tier"></svg>
<div class="detail" aria-live="polite"><div><h3 id="detail-title">Select a wealth tier</h3><p id="detail-copy">Hover a point for its sample size and middle-half range; click to keep the tier selected.</p></div><div class="detail-stat" id="detail-stat"></div></div>
<p class="hint">Every dot is a tier's median; the vertical line spans its 25th–75th percentile range. The $1m threshold is marked.</p>
</section>
<footer class="foot">All observations are synthetic. Categories are based on net worth, so the chart describes financial characteristics within generated wealth tiers; it does not show that a habit causes wealth. Negative and zero-to-$10k groups are small. Scores and ratios may be generated or derived by the dataset. Not financial advice.</footer>
</main>
<div class="tooltip" id="tooltip" role="status"></div>
<script>
const DATA = __DATA__;
const svg = document.getElementById("chart");
const tooltip = document.getElementById("tooltip");
let activeMetric = Object.keys(DATA.metrics)[0];
let pinned = null;
const NS = "http://www.w3.org/2000/svg";
const make = (tag, attrs={}, text="") => {
  const element = document.createElementNS(NS, tag);
  for (const [key,value] of Object.entries(attrs)) element.setAttribute(key,value);
  if (text) element.textContent = text;
  return element;
};
const fmt = (value, metric) => metric.format === "percent" ? `${value.toFixed(1)}%` : metric.format === "months" ? `${value.toFixed(1)} mo` : value.toFixed(1);
function render(metricKey) {
  activeMetric = metricKey;
  const metric = DATA.metrics[metricKey];
  document.getElementById("chart-title").textContent = `${metric.label} by wealth tier`;
  document.getElementById("chart-unit").textContent = `Median and middle 50% of records · ${metric.unit}`;
  document.querySelectorAll(".metric").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.key === metricKey)));
  svg.replaceChildren();
  const W=1080,H=440,L=70,R=28,T=32,B=112, PW=W-L-R, PH=H-T-B;
  const values=DATA.order.flatMap(key => {
    const point=DATA.summary[key].metrics[metricKey];
    return point ? [point.q1,point.q3] : [];
  });
  let min=Math.min(...values), max=Math.max(...values);
  const pad=(max-min || 1)*.14; min=Math.max(metric.format==="percent"?0:0,min-pad); max+=pad;
  const x=i=>L+i*PW/(DATA.order.length-1);
  const y=v=>T+PH-(v-min)/(max-min)*PH;
  const defs=make("defs");
  const gradient=make("linearGradient",{id:"line-gradient",x1:"0",x2:"1",y1:"0",y2:"0"});
  gradient.append(make("stop",{offset:"0%","stop-color":metric.color,"stop-opacity":".45"}));
  gradient.append(make("stop",{offset:"100%","stop-color":metric.color}));
  defs.append(gradient); svg.append(defs);
  const millionaireX=(x(6)+x(7))/2;
  svg.append(make("rect",{x: millionaireX-1,y:T,width:2,height:PH,fill:"#d6a54b","stroke-dasharray":"4 5","opacity":".85"}));
  svg.append(make("text",{x: millionaireX+7,y:T+10,fill:"#92702e","font-size":"11","font-weight":"700"},"$1m net worth"));
  for(let i=0;i<=4;i++){
    const value=min+(max-min)*i/4, yy=y(value);
    svg.append(make("line",{x1:L,y1:yy,x2:W-R,y2:yy,stroke:"#dce3dc","stroke-width":"1"}));
    svg.append(make("text",{x:L-12,y:yy+4,"text-anchor":"end",fill:"#61736d","font-size":"11"},fmt(value,metric)));
  }
  const linePoints=[];
  DATA.order.forEach((wealth,index)=>{
    const stat=DATA.summary[wealth].metrics[metricKey];
    if(!stat) return;
    const xx=x(index), yy=y(stat.median);
    linePoints.push(`${xx},${yy}`);
    svg.append(make("line",{x1:xx,y1:y(stat.q1),x2:xx,y2:y(stat.q3),stroke:metric.color,"stroke-width":"4","stroke-linecap":"round",opacity:".5"}));
    svg.append(make("line",{x1:xx-6,y1:y(stat.q1),x2:xx+6,y2:y(stat.q1),stroke:metric.color,"stroke-width":"1.5",opacity:".7"}));
    svg.append(make("line",{x1:xx-6,y1:y(stat.q3),x2:xx+6,y2:y(stat.q3),stroke:metric.color,"stroke-width":"1.5",opacity:".7"}));
    const selected=pinned===wealth;
    const circle=make("circle",{cx:xx,cy:yy,r:selected?8:6,fill:metric.color,stroke:selected?"#18332e":"white","stroke-width":selected?3:2,class:"point",tabindex:"0",role:"button","aria-label":`${WEALTH_LABEL(wealth)}; median ${fmt(stat.median,metric)}; sample ${DATA.summary[wealth].n}`});
    circle.addEventListener("mouseenter",event=>showTooltip(event,wealth,stat,metric));
    circle.addEventListener("mousemove",positionTooltip);
    circle.addEventListener("mouseleave",()=>{tooltip.style.display="none"});
    circle.addEventListener("focus",()=>showPinned(wealth,metric));
    circle.addEventListener("click",()=>{pinned=wealth; render(metricKey); showPinned(wealth,metric)});
    circle.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();pinned=wealth;render(metricKey);showPinned(wealth,metric)}});
    svg.append(circle);
    const label=make("text",{x:xx,y:T+PH+25,"text-anchor":"middle",fill:"#344c45","font-size":"11","font-weight":wealth==="1m_to_2.5m"?"800":"500"});
    const [first,second]=DATA.summary[wealth].label.split(" ");
    label.append(make("tspan",{x:xx,dy:"0"},first));
    if(second) label.append(make("tspan",{x:xx,dy:"14"},second));
    svg.append(label);
  });
  svg.insertBefore(make("polyline",{points:linePoints.join(" "),fill:"none",stroke:"url(#line-gradient)","stroke-width":"3","stroke-linejoin":"round","stroke-linecap":"round"}),svg.children[1]||null);
  if(pinned) showPinned(pinned,metric);
  else {
    document.getElementById("detail-title").textContent="Select a wealth tier";
    document.getElementById("detail-copy").textContent="Hover a point for its sample size and middle-half range; click to keep the tier selected.";
    document.getElementById("detail-stat").textContent="";
  }
}
function WEALTH_LABEL(key){return DATA.summary[key].label.replace("–"," to ")}
function showTooltip(event,wealth,stat,metric){
  tooltip.innerHTML=`<strong>${WEALTH_LABEL(wealth)}</strong><br>Median: ${fmt(stat.median,metric)}<br>Middle half: ${fmt(stat.q1,metric)}–${fmt(stat.q3,metric)}<br>Records: ${DATA.summary[wealth].n.toLocaleString()}`;
  tooltip.style.display="block"; positionTooltip(event);
}
function positionTooltip(event){tooltip.style.left=`${Math.min(event.clientX+14,window.innerWidth-230)}px`;tooltip.style.top=`${Math.min(event.clientY+14,window.innerHeight-110)}px`}
function showPinned(wealth,metric){
  const stat=DATA.summary[wealth].metrics[activeMetric];
  const base=DATA.summary[DATA.order[0]].metrics[activeMetric];
  document.getElementById("detail-title").textContent=WEALTH_LABEL(wealth);
  document.getElementById("detail-copy").textContent=`Middle 50%: ${fmt(stat.q1,metric)}–${fmt(stat.q3,metric)} · ${DATA.summary[wealth].n.toLocaleString()} records. Compared with the lowest-net-worth tier: ${stat.median>=base.median?"+":""}${fmt(stat.median-base.median,metric)} at the median.`;
  document.getElementById("detail-stat").textContent=`${fmt(stat.median,metric)} median`;
}
document.querySelectorAll(".metric").forEach(button=>button.addEventListener("click",()=>render(button.dataset.key)));
render(activeMetric);
</script>
</body></html>"""
    document = document.replace("__ROW_COUNT__", f"{row_count:,}")
    document = document.replace("__OPTIONS__", options)
    document = document.replace("__DATA__", payload)
    HTML_FILE.parent.mkdir(parents=True, exist_ok=True)
    HTML_FILE.write_text(document, encoding="utf-8")


def make_visualizations(dataset_path):
    summary, row_count = load_summary(dataset_path)
    plot_static_summary(summary, row_count)
    build_html(summary, row_count)
    print(f"Saved {PNG_FILE}")
    print(f"Saved {HTML_FILE}")
    print(f"Summarized {row_count:,} records across {len(summary)} wealth tiers.")


def main():
    parser = argparse.ArgumentParser(
        description="Create interactive and static wealth-tier profile visualizations."
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
    make_visualizations(args.dataset)


if __name__ == "__main__":
    main()
