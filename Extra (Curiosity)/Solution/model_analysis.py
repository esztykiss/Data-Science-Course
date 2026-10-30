import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import display
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
)
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier


SEED = 2026
TARGET = "target"

assert raw_df[TARGET].notna().all(), "Hiányzó célérték: kézi ellenőrzés szükséges."
assert set(raw_df[TARGET].unique()).issubset({0, 1}), "A célváltozó nem bináris."

analysis_df = raw_df.sort_values(["year", "quarter", "source_row"]).reset_index(drop=True)
observed_years = np.sort(analysis_df["year"].unique())
test_years = observed_years[-3:]
train_df = analysis_df.loc[~analysis_df["year"].isin(test_years)].reset_index(drop=True)
test_df = analysis_df.loc[analysis_df["year"].isin(test_years)].reset_index(drop=True)
assert train_df["year"].max() < test_df["year"].min()
assert test_df["year"].nunique() == 3

print(
    f"Időrendi split: tanító évek {train_df.year.min()}–{train_df.year.max()} "
    f"({len(train_df):,} sor); a zárolt tesztévek "
    f"{test_df.year.min()}–{test_df.year.max()} ({len(test_df):,} sor)."
)
print(
    f"A seed a véletlen komponensű modelleknél {SEED}; "
    "az időrendi vágás determinisztikus."
)

train_issue_df = issue_df.loc[issue_df["year"].isin(train_df["year"].unique())]
class_counts = train_df[TARGET].value_counts().reindex([0, 1], fill_value=0)
class_summary = pd.DataFrame(
    {"darab": class_counts, "arány": class_counts / len(train_df)}
)
class_summary.index = ["Negatív: kód 1–4", "Pozitív: bokáig/földig (5–6)"]

print(
    "Pozitív osztály: skirt-kód 5 vagy 6 (bokáig vagy földig érő szoknya); "
    "az arányt a tanítórészen mérjük."
)
print(
    "Kódjelentés a szakdolgozat alapján: 1=miniszoknya, 2=térd fölött, "
    "3=fedi a térdet, 4=térd alatt, 5=bokáig, 6=földig."
)
print(
    "Hirdetések: small_ads = megfizethetőbb luxus hirdetéseinek száma "
    "(pl. parfüm, kozmetikum, rúzs, testápoló); high_ads = nagyobb értékű "
    "luxus hirdetéseinek száma (pl. táska, óra, ékszer, utazás). "
    "Ezek darabszámok, nem árak."
)
print(
    f"Tanító megfigyelések: {len(train_df):,}; pozitívak: "
    f"{int(class_counts.loc[1]):,}; pozitív arány: "
    f"{class_counts.loc[1] / len(train_df):.1%}"
)
display(class_summary)

fig, axes = plt.subplots(1, 2, figsize=(13, 4))
axes[0].bar(class_summary.index, class_summary["darab"], color=["#6c8ebf", "#d98282"])
axes[0].set_title("Célosztályok darabszáma")
axes[0].set_ylabel("Megfigyelések")
axes[0].tick_params(axis="x", rotation=12)

yearly = train_df.groupby("year")[TARGET].agg(["size", "mean"])
axes[1].plot(yearly.index, yearly["mean"], marker="o", markersize=3)
axes[1].set_title("Pozitív osztály aránya évenként")
axes[1].set_xlabel("Év")
axes[1].set_ylabel("Pozitív arány")
axes[1].set_ylim(0, max(0.35, yearly["mean"].max() * 1.1))
axes[1].grid(alpha=0.25)
plt.tight_layout()
plt.show()

blank_columns = ["n_small_blank_cells", "n_high_blank_cells"]
blank_cells_total = int(train_issue_df[blank_columns].to_numpy().sum())
blank_cells_possible = len(train_issue_df) * 12
feature_columns_to_audit = ["year", "quarter", "small_ads", "high_ads"]
print(
    f"Üres hirdetési kategóriacellák: {blank_cells_total:,}/"
    f"{blank_cells_possible:,} ({blank_cells_total / blank_cells_possible:.1%}); "
    "a modell ezeket a cellaszámokat nem használja."
)
print(
    "Hiányzó érték a célban vagy a tervezett alapjellemzőkben:",
    int(train_df[[TARGET, *feature_columns_to_audit]].isna().sum().sum()),
)
print(
    "A nyers munkafüzet nem jelöli külön, hogy egy üres hirdetési cella nulla "
    "vagy hiányzó rögzítés; ezért a cellaszám csak audit, nem modellbemenet."
)

print(
    "Az EDA, a jellemzőválasztás és a modellezés a zárolt teszt címkéit nem "
    "használja; a tesztet csak a végső értékelési blokk olvassa ki."
)


def make_features(frame, engineered=False):
    features = frame[["year", "quarter", "small_ads", "high_ads"]].copy()
    if engineered:
        features["ad_difference"] = frame["high_ads"] - frame["small_ads"]
    return features


def build_model(name, feature_columns, params=None):
    params = {} if params is None else {
        key.removeprefix("model__"): value for key, value in params.items()
    }

    def configured(defaults):
        return {**defaults, **params}

    numeric_columns = [column for column in feature_columns if column != "quarter"]
    prep = ColumnTransformer(
        [
            (
                "numeric",
                StandardScaler() if name == "Logistic regression" else "passthrough",
                numeric_columns,
            ),
            ("quarter", OneHotEncoder(handle_unknown="ignore"), ["quarter"]),
        ],
        sparse_threshold=0,
    )
    if name == "Dummy":
        classifier = DummyClassifier(strategy="prior")
    elif name == "Logistic regression":
        classifier = LogisticRegression(
            **configured(
                {"max_iter": 2000, "class_weight": "balanced", "random_state": SEED}
            )
        )
    elif name == "Decision tree":
        classifier = DecisionTreeClassifier(
            **configured({"class_weight": "balanced", "random_state": SEED})
        )
    elif name == "Random forest":
        classifier = RandomForestClassifier(
            **configured(
                {
                    "n_estimators": 300,
                    "min_samples_leaf": 2,
                    "class_weight": "balanced_subsample",
                    "n_jobs": 1,
                    "random_state": SEED,
                }
            )
        )
    elif name == "XGBoost":
        classifier = XGBClassifier(
            **configured(
                {
                    "n_estimators": 300,
                    "max_depth": 3,
                    "learning_rate": 0.05,
                    "subsample": 0.9,
                    "colsample_bytree": 0.9,
                    "reg_lambda": 1,
                    "eval_metric": "logloss",
                    "n_jobs": 1,
                    "random_state": SEED,
                    "verbosity": 0,
                }
            )
        )
    elif name == "HistGradientBoosting":
        classifier = HistGradientBoostingClassifier(
            **configured(
                {
                    "max_iter": 100,
                    "max_leaf_nodes": 7,
                    "learning_rate": 0.05,
                    "l2_regularization": 2,
                    "min_samples_leaf": 20,
                    "random_state": SEED,
                }
            )
        )
    else:
        raise ValueError(f"Ismeretlen modell: {name}")
    return Pipeline([("preprocess", prep), ("model", classifier)])


def chronological_splits(frame, n_splits, test_size):
    years = np.sort(frame["year"].unique())
    splitter = TimeSeriesSplit(n_splits=n_splits, test_size=test_size)
    splits = []
    for train_year_idx, valid_year_idx in splitter.split(years):
        train_years = years[train_year_idx]
        valid_years = years[valid_year_idx]
        train_rows = np.flatnonzero(frame["year"].isin(train_years).to_numpy())
        valid_rows = np.flatnonzero(frame["year"].isin(valid_years).to_numpy())
        splits.append((train_rows, valid_rows))
    return splits


def evaluate_cv(frame, model_name, engineered, splits, params=None):
    x = make_features(frame, engineered=engineered)
    y = frame[TARGET].to_numpy()
    oof_probability = np.full(len(frame), np.nan)
    rows = []
    for fold_number, (train_idx, valid_idx) in enumerate(splits, start=1):
        model = build_model(model_name, list(x.columns), params=params)
        model.fit(x.iloc[train_idx], y[train_idx])
        probability = model.predict_proba(x.iloc[valid_idx])[:, 1]
        oof_probability[valid_idx] = probability
        prediction = probability >= 0.5
        rows.append(
            {
                "fold": fold_number,
                "valid_years": (
                    f"{frame.iloc[valid_idx]['year'].min()}–"
                    f"{frame.iloc[valid_idx]['year'].max()}"
                ),
                "PR-AUC": average_precision_score(y[valid_idx], probability),
                "balanced_accuracy@0.5": balanced_accuracy_score(y[valid_idx], prediction),
            }
        )
    oof = pd.DataFrame(
        {
            "row_index": np.arange(len(frame)),
            "year": frame["year"].to_numpy(),
            "issue_id": frame["issue_id"].to_numpy(),
            "y_true": y,
            "y_probability": oof_probability,
        }
    ).dropna(subset=["y_probability"])
    return pd.DataFrame(rows), oof


# A 1991–1993-as tesztet sem a modellek, sem az előfeldolgozás nem látja.
# A fejlesztési CV 1973–1984-es validációs blokkjai azonosak minden modellnél.
dev_df = train_df.loc[train_df["year"] <= 1984].reset_index(drop=True)
dev_splits = chronological_splits(dev_df, n_splits=4, test_size=3)
print(
    "\nFejlesztési CV validációs évek:",
    [
        row["valid_years"]
        for row in evaluate_cv(dev_df, "Dummy", False, dev_splits)[0].to_dict("records")
    ],
)

model_names = [
    "Dummy",
    "Logistic regression",
    "Decision tree",
    "Random forest",
    "XGBoost",
    "HistGradientBoosting",
]
benchmark = {}
benchmark_rows = []
for model_name in model_names:
    fold_scores, oof_predictions = evaluate_cv(
        dev_df, model_name, engineered=False, splits=dev_splits
    )
    benchmark[model_name] = {"folds": fold_scores, "oof": oof_predictions}
    benchmark_rows.append(
        {
            "modell": model_name,
            "PR-AUC átlag ± fold-szórás": (
                f"{fold_scores['PR-AUC'].mean():.3f} ± "
                f"{fold_scores['PR-AUC'].std(ddof=1):.3f}"
            ),
            "_PR-AUC átlag": fold_scores["PR-AUC"].mean(),
            "balanced accuracy @ 0.5, átlag": fold_scores[
                "balanced_accuracy@0.5"
            ].mean(),
        }
    )
benchmark_summary = pd.DataFrame(benchmark_rows).sort_values(
    "_PR-AUC átlag", ascending=False
).drop(columns="_PR-AUC átlag")
print(
    "\nAlapmodellek: a PR-AUC foldonkénti átlagát és szórását mutatjuk; "
    "a nyers pontosságot az osztály-aránytalanság miatt nem használjuk fő mutatónak."
)
display(benchmark_summary)

# Visszacsatolás: a különbségjellemzőt ugyanazokon az időrendi foldokon próbáljuk.
feature_comparisons = {}
for model_name in ["Logistic regression", "XGBoost", "HistGradientBoosting"]:
    base_folds = benchmark[model_name]["folds"]
    engineered_folds, engineered_oof = evaluate_cv(
        dev_df, model_name, engineered=True, splits=dev_splits
    )
    paired = base_folds.merge(
        engineered_folds, on=["fold", "valid_years"], suffixes=("_base", "_engineered")
    )
    paired["PR-AUC különbség"] = paired["PR-AUC_engineered"] - paired["PR-AUC_base"]
    feature_comparisons[model_name] = {
        "folds": engineered_folds,
        "oof": engineered_oof,
        "paired": paired,
    }
    delta = paired["PR-AUC különbség"]
    print(
        f"\n{model_name}: `high_ads - small_ads` páros PR-AUC-változás: "
        f"{delta.mean():+.3f} ± {delta.std(ddof=1):.3f}"
    )
    display(paired[["valid_years", "PR-AUC_base", "PR-AUC_engineered", "PR-AUC különbség"]])

hgb_oof = feature_comparisons["HistGradientBoosting"]["oof"].copy()
hgb_oof["hiba_0_5"] = np.where(
    (hgb_oof["y_true"] == 1) & (hgb_oof["y_probability"] < 0.5),
    "kihagyott pozitív",
    np.where(
        (hgb_oof["y_true"] == 0) & (hgb_oof["y_probability"] >= 0.5),
        "téves riasztás",
        "helyes",
    ),
)
top_count = max(1, math.ceil(0.10 * len(hgb_oof)))
top_oof = hgb_oof.nlargest(top_count, "y_probability")
print(
    "\nHisztogram-alapú boosting OOF-hibák a rögzített 0.5 küszöbnél:",
    hgb_oof["hiba_0_5"].value_counts().to_dict(),
)
print(
    f"OOF top 10% találati aránya: {top_oof['y_true'].mean():.1%}; "
    f"pozitív arány a teljes OOF-részben: {hgb_oof['y_true'].mean():.1%}."
)
print(
    "Hipotézis: a nagyobb és a megfizethetőbb luxushirdetések különbsége "
    "a fa-alapú modell számára egy közvetlenül felhasználható küszöböt adhat. "
    "A logisztikus regresszióban ez a jellemző a két eredeti oszlop lineáris "
    "kombinációja, ezért új lineáris információt nem ad; a boostingnál viszont "
    "nemlineáris felosztásként segíthet. A fold-szórás és a foldonkénti eltérések "
    "alapján a javulás bizonytalanságát is figyelembe vesszük."
)

# Csak az előre kijelölt CV-blokkokon rangsorolunk; a tesztet nem látjuk.
candidate_rows = [
    {
        "modell": name,
        "engineered": False,
        "PR-AUC átlag": values["folds"]["PR-AUC"].mean(),
    }
    for name, values in benchmark.items()
    if name != "Dummy"
]
for name, values in feature_comparisons.items():
    candidate_rows.append(
        {
            "modell": name,
            "engineered": True,
            "PR-AUC átlag": values["folds"]["PR-AUC"].mean(),
        }
    )
candidate_table = pd.DataFrame(candidate_rows).sort_values(
    "PR-AUC átlag", ascending=False
)
display(candidate_table)
best_candidate = candidate_table.iloc[0]
best_model_name = best_candidate["modell"]
selected_feature_mode = bool(best_candidate["engineered"])
print(
    f"Fejlesztési CV alapján választott jelölt: {best_model_name}; "
    f"új különbségjellemző: {selected_feature_mode}."
)

# A paraméterkeresés csak 1984-ig lát adatot; a későbbi tanítóévek ellenőrző blokkok.
if best_model_name == "HistGradientBoosting":
    parameter_grid = {
        "model__max_iter": [50, 100, 200],
        "model__max_leaf_nodes": [3, 7, 15],
        "model__learning_rate": [0.03, 0.05, 0.1],
        "model__l2_regularization": [0, 2, 10],
        "model__min_samples_leaf": [20, 50],
    }
elif best_model_name == "XGBoost":
    parameter_grid = {
        "model__n_estimators": [200, 400],
        "model__max_depth": [2, 3, 4],
        "model__learning_rate": [0.03, 0.07],
        "model__min_child_weight": [1, 5],
    }
elif best_model_name == "Random forest":
    parameter_grid = {
        "model__n_estimators": [200, 400],
        "model__max_features": ["sqrt", 0.8],
        "model__min_samples_leaf": [1, 3],
    }
elif best_model_name == "Decision tree":
    parameter_grid = {
        "model__max_depth": [2, 4, 8, None],
        "model__min_samples_leaf": [5, 15, 30],
    }
else:
    parameter_grid = {"model__C": [0.1, 1.0, 10.0]}

dev_x = make_features(dev_df, engineered=selected_feature_mode)
search = GridSearchCV(
    estimator=build_model(best_model_name, list(dev_x.columns)),
    param_grid=parameter_grid,
    scoring="average_precision",
    cv=dev_splits,
    n_jobs=1,
    refit=True,
    return_train_score=False,
)
search.fit(dev_x, dev_df[TARGET].to_numpy())
print(f"Keresés legjobb CV PR-AUC átlaga: {search.best_score_:.3f}")
print("Keresés során kiválasztott paraméterek:", search.best_params_)

verification_rows = []
for fold_number, (first_year, last_year) in enumerate(
    [(1985, 1987), (1988, 1990)], start=1
):
    prior = train_df.loc[train_df["year"] < first_year].reset_index(drop=True)
    valid = train_df.loc[
        train_df["year"].between(first_year, last_year)
    ].reset_index(drop=True)
    prior_x = make_features(prior, engineered=selected_feature_mode)
    valid_x = make_features(valid, engineered=selected_feature_mode)
    for version, params in [("alap", None), ("hangolt", search.best_params_)]:
        model = build_model(best_model_name, list(prior_x.columns), params=params)
        model.fit(prior_x, prior[TARGET].to_numpy())
        probability = model.predict_proba(valid_x)[:, 1]
        verification_rows.append(
            {
                "fold": fold_number,
                "valid_years": f"{first_year}–{last_year}",
                "modell": version,
                "PR-AUC": average_precision_score(valid[TARGET], probability),
            }
        )
verification = pd.DataFrame(verification_rows)
verification_wide = verification.pivot(
    index=["fold", "valid_years"], columns="modell", values="PR-AUC"
)
verification_wide["hangolt − alap"] = verification_wide["hangolt"] - verification_wide["alap"]
verification_delta = verification_wide["hangolt − alap"]
display(verification_wide)
print(
    f"Keresés által nem látott évek páros PR-AUC-változása: "
    f"{verification_delta.mean():+.3f} ± {verification_delta.std(ddof=1):.3f}."
)
use_tuned = verification_delta.mean() > 0
selected_params = search.best_params_ if use_tuned else None
print(
    "Döntés:",
    "a hangolt modell marad"
    if use_tuned
    else "az egyszerűbb alapbeállítás marad; a hangolás nem javított az ellenőrző foldokon.",
)


def test_metrics(y_true, probability, threshold=0.5):
    prediction = probability >= threshold
    cm = confusion_matrix(y_true, prediction, labels=[0, 1])
    top_n = max(1, math.ceil(0.10 * len(y_true)))
    top_indices = np.argsort(-probability, kind="stable")[:top_n]
    has_ranking = np.unique(probability).size > 1
    return {
        "PR-AUC": average_precision_score(y_true, probability),
        "balanced accuracy": balanced_accuracy_score(y_true, prediction),
        "küszöb": threshold,
        "konfúziós mátrix [[TN, FP], [FN, TP]]": cm.tolist(),
        "precision@10%": float(np.mean(y_true[top_indices])) if has_ranking else np.nan,
        "recall@10%": float(np.sum(y_true[top_indices]) / np.sum(y_true))
        if has_ranking and np.sum(y_true)
        else np.nan,
    }


# A küszöböt előre rögzítjük 0.5-re; a zárolt teszteredmény nem vezet vissza választáshoz.
final_train_x = make_features(train_df, engineered=selected_feature_mode)
final_test_x = make_features(test_df, engineered=selected_feature_mode)
final_model = build_model(
    best_model_name, list(final_train_x.columns), params=selected_params
)
final_model.fit(final_train_x, train_df[TARGET].to_numpy())
final_test_probability = final_model.predict_proba(final_test_x)[:, 1]

base_train_x = make_features(train_df, engineered=False)
base_test_x = make_features(test_df, engineered=False)
base_model = build_model(best_model_name, list(base_train_x.columns), params=None)
base_model.fit(base_train_x, train_df[TARGET].to_numpy())
base_test_probability = base_model.predict_proba(base_test_x)[:, 1]

logistic_model = build_model("Logistic regression", list(base_train_x.columns))
logistic_model.fit(base_train_x, train_df[TARGET].to_numpy())
logistic_test_probability = logistic_model.predict_proba(base_test_x)[:, 1]

dummy_model = build_model("Dummy", list(base_train_x.columns))
dummy_model.fit(base_train_x, train_df[TARGET].to_numpy())
dummy_test_probability = dummy_model.predict_proba(base_test_x)[:, 1]

test_results = pd.DataFrame(
    [
        {
            "modell": f"Végső {best_model_name} "
            f"({'különbségjellemző' if selected_feature_mode else 'alapjellemzők'})",
            **test_metrics(test_df[TARGET].to_numpy(), final_test_probability),
        },
        {
            "modell": f"Alap {best_model_name}",
            **test_metrics(test_df[TARGET].to_numpy(), base_test_probability),
        },
        {
            "modell": "Logisztikus regresszió (alapmodell)",
            **test_metrics(test_df[TARGET].to_numpy(), logistic_test_probability),
        },
        {
            "modell": "Dummy",
            **test_metrics(test_df[TARGET].to_numpy(), dummy_test_probability),
        },
    ]
)
print(
    "\nEgyszeri, zárolt tesztértékelés. A küszöb előre rögzített 0.5; "
    "a precision@10% a legmagasabb becsült kockázatú tesztsorok pozitív aránya."
)
display(test_results)

# Csoportos bootstrap: teljes lapszámokat mintázunk, mert ugyanazon lapszám sorai nem függetlenek.
test_groups = test_df["issue_id"].to_numpy()
unique_groups = np.unique(test_groups)
group_rows = {group: np.flatnonzero(test_groups == group) for group in unique_groups}
rng = np.random.default_rng(SEED)
bootstrap_pr_auc = []
for _ in range(2000):
    sampled_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
    sampled_indices = np.concatenate([group_rows[group] for group in sampled_groups])
    sampled_y = test_df[TARGET].to_numpy()[sampled_indices]
    sampled_probability = final_test_probability[sampled_indices]
    bootstrap_pr_auc.append(
        0.0
        if sampled_y.sum() == 0
        else average_precision_score(sampled_y, sampled_probability)
    )
ci_low, ci_high = np.percentile(bootstrap_pr_auc, [2.5, 97.5])
print(
    f"Végső modell teszt PR-AUC: "
    f"{average_precision_score(test_df[TARGET], final_test_probability):.3f}; "
    f"95%-os lapszám-klaszter bootstrap CI: [{ci_low:.3f}, {ci_high:.3f}] "
    f"(2000 újramintázás, {len(unique_groups)} tesztlapszám)."
)
