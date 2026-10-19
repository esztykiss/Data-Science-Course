# Millionaire Habits Visualization

Run from the repository root with Python and Matplotlib installed:

```bash
python "Homework 3/project/visualize_habits.py"
```

The script reads the supplied `correlations.csv` from `sources` and writes
`millionaire_habits_visualization.png` to `outcome`. It charts selected
financial-behavior and routine variables against millionaire status. The source
dataset is synthetic, and the correlations are descriptive rather than causal.

## Country savings-rate map

### What

`millionaire_habits_country_savings_rate.png` maps the average measured savings
rate in each of the 25 countries. The adjacent ranking names every country,
shows its rate, and highlights the highest country.

### Why

The original chart compares overall correlations with millionaire status.
This view makes the country comparison explicit and answers where the average
recorded savings rate is highest. The underlying dataset is synthetic, so the
result is an exploration of generated data, not a claim about real populations.

### How

The analysis uses all 100,000 records, groups them by country, and calculates
the mean of `savings_rate`. Values are stored as fractions of income, so they
are converted to percentages for the map and ranking. The United States has
the highest average in the supplied data (28.27%). The color scale and ranked
bars use the same percentage values; the bar axis is focused on 25.5–29% to
show the relatively small country-to-country differences clearly.

The full CSV is not included in this repository. Download the dataset from
[Kaggle](https://www.kaggle.com/datasets/datascikhan/millionaire-habits-dataset)
and run the script with either the CSV or the downloaded ZIP:

```bash
python "Homework 3/project/visualize_country_savings.py" \
  "Homework 3/sources/Millionaire_Habits_Dataset.csv"
```

The script also accepts the original Kaggle ZIP as its argument. It writes the
map to `Homework 3/outcome/millionaire_habits_country_savings_rate.png`. Country
boundaries are provided by Natural Earth at 1:110m scale; the map geometry is
public domain.

## Interactive wealth-tier explorer

`millionaire_habits_wealth_ladder.png` in `outcome/` and the interactive
`millionaire_habits_wealth_ladder.html` in `project/` add a view not covered by the
country map: how financial profiles differ across the dataset's 11 net-worth
tiers. The first chart reports correlations with millionaire status; this
explorer instead compares distributions across wealth tiers. The five measures
are portfolio diversification, passive income share, savings rate, debt stress,
and emergency-fund months. Each tier is summarized by its median and
interquartile range, so the chart shows both the typical record and variation
within the group.

In this generated dataset, the median diversification score rises from 55.5
in the $500k–$1m tier to 77.8 in the $1m–$2.5m tier, reaching the score ceiling
of 100 above $2.5m. Median debt stress trends down across wealth tiers, while
median emergency-fund coverage stays roughly between 2.1 and 2.8 months. The
smallest tiers have far fewer observations, and these patterns are descriptive,
not causal.

Open the HTML file in `project/` in a browser to switch measures, hover for tier
values and sample sizes, or click a point to pin a tier for comparison. The PNG
is a static overview of all five measures. The `outcome/` folder is reserved
for the three PNG visualizations.

```bash
python "Homework 3/project/visualize_wealth_ladder.py" \
  "Homework 3/sources/Millionaire_Habits_Dataset.csv"
```

The script also accepts the original Kaggle ZIP. All reported patterns are
descriptive of this synthetic dataset; they do not establish causation or
represent real populations.