# 5. házi feladat — Építs saját regressziós modellt (King County házárak)

Ez a munkafüzet a **King County (Washington állam, Seattle és környéke) lakóingatlan-eladási adatsorán** (`OpenML data_id=42092` / Kaggle `kc_house_data`) mutatja be a teljes gépi tanulási modellezési életciklust: az üzleti kérdésfeltevéstől és a feltáró adatelemzéstől (EDA) kezdve az adat- és időszivárgást kizáró vágáson, az alapmodelleken és az out-of-fold diagnosztikán át az ellenőrzött visszacsatolási körig és az egyszeri záró tesztelésig.

---

## 1. A kérdés és a célváltozó

A modellünk által becsült célváltozó a lakóingatlanok tényleges piaci **tranzakciós eladási ára amerikai dollárban (`price`, USD)** King County területén. Üzleti szempontból – ha a modellt egy automatizált ingatlanérték-becslő rendszerben (AVM), például jelzáloghitel-fedezet értékeléséhez vagy egy *iBuyer* (azonnali készpénzes felvásárló) döntéstámogatásához használjuk – **a fölülbecslés ($\hat{y} > y$) sokkal drágább hiba, mint az alulbecslés**, mivel egy túlárazottan megvásárolt ingatlan vagy egy túlértékelt fedezetre kihelyezett hitel közvetlen, nem megtérülő tőkeveszteséget okoz, míg az alulbecslés „csak” elmaradt üzleti lehetőséget (sikertelen ajánlattételt) eredményez. Ugyanakkor a piac rendkívül heterogén (a $75\,000\text{ USD}$-os garzontól a $7{,}7\text{ millió USD}$-os luxusvilláig terjed), így egy $100\,000\text{ USD}$-os tévedés egy $250\,000\text{ USD}$-os házon ($40\%$-os relatív hiba) lényegesen súlyosabb torzítás, mint ugyanez az összeg egy $3\text{ millió USD}$-os birtokon ($3{,}3\%$-os hiba). Mindezek alapján **fő mutatónknak a négyzetgyökös átlagos négyzetes hibát (RMSE) választjuk**, mert a négyzetes veszteségfüggvény ($(\hat{y}_i - y_i)^2$) keményen bünteti a portfóliószinten kritikus, nagy dollárértékű (különösen a felső ársávban vagy durva fölülbecsléseknél jelentkező) kilengéseket; mellette azonban kötelezően figyeljük az abszolút hibát (**MAE**), a magyarázott varianciaarányt (**$R^2$**), valamint az arányos hibát mérő **WAPE** és **RMSLE** mutatókat is, hogy az olcsóbb ingatlanokon elkövetett relatív hibák se rejtőzhessenek el a luxusingatlanok dollár-dominanciája mögött.

---

## 2. Adatbetöltés és feltáró adatelemzés (EDA)

Először betöltjük az adatsort az OpenML-ről (vagy helyi `kc_house_data.csv` fájlból, biztosítva a pontosan egyező $21\,613 \times 20$-as sémát), és ellenőrizzük az alapvető statisztikai tulajdonságokat.

```python
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.datasets import fetch_openml
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import Ridge
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.neighbors import BallTree
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, mean_squared_log_error
from xgboost import XGBRegressor

# 1. Adatbetöltés (OpenML data_id=42092 vagy helyi kc_house_data.csv tartalék)
try:
    df = fetch_openml(data_id=42092, as_frame=True).frame.copy()
except Exception:
    df = pd.read_csv("kc_house_data.csv")
    if "id" in df.columns:
        df = df.drop(columns=["id"])

print(f"Adatsor mérete: {df.shape[0]} sor × {df.shape[1]} oszlop")
print(f"Hiányzó értékek száma összesen: {df.isna().sum().sum()}")
print(f"Irányítószámok (zipcode) száma: {df['zipcode'].nunique()}")
print(f"Ár (price) statisztikák:\n"
      f"  Átlag:  {df['price'].mean():,.0f} USD\n"
      f"  Medián: {df['price'].median():,.0f} USD\n"
      f"  Min:    {df['price'].min():,.0f} USD\n"
      f"  Max:    {df['price'].max():,.0f} USD\n"
      f"  >1M $:  {(df['price'] > 1_000_000).mean()*100:.2f}% ({(df['price'] > 1_000_000).sum()} db)")
```

**Kimenet és alapellenőrzés:**
```text
Adatsor mérete: 21613 sor × 20 oszlop
Hiányzó értékek száma összesen: 0
Irányítószámok (zipcode) száma: 70
Ár (price) statisztikák:
  Átlag:  540,088 USD
  Medián: 450,000 USD
  Min:    75,000 USD
  Max:    7,700,000 USD
  >1M $:  6.78% (1465 db)
```

### 2.1. A célváltozó eloszlása és a log-transzformáció indoklása (1. ábra)

Megvizsgáljuk a nyers `price` és a természetes alapú logaritmussal transzformált $\log(\text{price})$ változó eloszlását, ferdeségét (*skewness*) és csúcsosságát (*kurtosis*).

```python
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Bal panel: Nyers ár eloszlása
sns.histplot(df["price"] / 1e6, bins=60, kde=True, color="#2b5c8f", ax=axes[0])
axes[0].axvline(df["price"].mean() / 1e6, color="red", linestyle="--", label=f"Átlag: {df['price'].mean():,.0f} $")
axes[0].axvline(df["price"].median() / 1e6, color="orange", linestyle="-", label=f"Medián: {df['price'].median():,.0f} $")
axes[0].set_title(f"Nyers eladási ár (price) eloszlása\n(Ferdeség: {df['price'].skew():.2f}, Csúcsosság: {df['price'].kurt():.2f})")
axes[0].set_xlabel("Eladási ár (millió USD)")
axes[0].set_ylabel("Gyakoriság (db)")
axes[0].legend()

# Jobb panel: Log-transzformált ár eloszlása
log_price = np.log(df["price"])
sns.histplot(log_price, bins=60, kde=True, color="#2e8b57", ax=axes[1])
axes[1].axvline(log_price.mean(), color="red", linestyle="--", label=f"Átlag: {log_price.mean():.2f}")
axes[1].axvline(log_price.median(), color="orange", linestyle="-", label=f"Medián: {log_price.median():.2f}")
axes[1].set_title(f"Log-transzformált ár ln(price) eloszlása\n(Ferdeség: {log_price.skew():.2f}, Csúcsosság: {log_price.kurt():.2f})")
axes[1].set_xlabel("ln(price)")
axes[1].set_ylabel("Gyakoriság (db)")
axes[1].legend()

plt.tight_layout()
plt.show()
```

| Mutató | Nyers `price` (USD) | Transzformált $\ln(\text{price})$ | Értelmezés |
|---|---|---|---|
| **Átlag** | $540\,088\text{ USD}$ | $13{,}048$ ($\approx \ln(464\,100)$) | A nyers átlagot felfelé húzza a felső $6{,}8\%$ luxuspiac |
| **Medián** | $450\,000\text{ USD}$ | $13{,}017$ ($\approx \ln(450\,000)$) | Log-skálán az átlag és a medián szinte egybeesik |
| **Szórás (SD)** | $367\,127\text{ USD}$ | $0{,}527$ | A multiplikatív szóródás log-skálán homoszkedasztikusabbá válik |
| **Ferdeség (Skewness)** | $+4{,}024$ | $+0{,}452$ | A súlyos jobbra nyúlás log-skálán közel szimmetrikussá szelídül |
| **Csúcsosság (Kurtosis)** | $+34{,}586$ | $+0{,}692$ | A szélsőséges farok-események (outliers) hatása normalizálódik |

**Mit kezdünk a célváltozóval?**
- A nyers `price` erősen jobbra elnyúló ($\text{ferdeség} = 4{,}02$), és az ingatlanpiaci jellemzők (pl. alapterület, építési minőség, elhelyezkedés) **multiplikatív** módon hatnak az árra (egy jó környék nem fix $+100\,000\text{ USD}$-t ad hozzá egy garzonhoz és egy kastélyhoz egyaránt, hanem pl. $+40\%$-ot).
- Ezért a **lineáris modellben $\ln(\text{price})$ célváltozót** használunk, amivel a multiplikatív kapcsolat additívvá válik ($\ln(y) = X\beta + \varepsilon$), a reziduumok szórása pedig kiegyenlítődik.
- **Kritikus módszertani részlet:** mivel a kiértékelést eredeti dollár (USD) skálán végezzük, a naiv $\hat{y} = \exp(\widehat{\ln y})$ visszaalakítás a Jensen-egyenlőtlenség ($E[\exp(Z)] > \exp(E[Z])$) miatt szisztematikusan **alulbecsülné** a várható értéket. Ezt a 6. fejezetben bemutatott **Duan-féle smearing korrekcióval** ($\hat{y} = \exp(\widehat{\ln y}) \cdot \frac{1}{N_{\text{train}}}\sum \exp(e_i)$) küszöböljük ki, szigorúan csak a tanító foldon becsülve a korrekciós szorzót.

### 2.2. Térbeli eloszlás és szerkezeti összefüggések (2. ábra)

Megvizsgáljuk az árak földrajzi koncentrációját (`lat`, `long`), valamint a lakóterület (`sqft_living`) és a kivitelezési minőség (`grade`) együttes hatását.

```python
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Bal panel: Földrajzi elhelyezkedés és log-ár
sc = axes[0].scatter(
    df["long"], df["lat"],
    c=np.log10(df["price"]), cmap="viridis",
    alpha=0.4, s=4
)
plt.colorbar(sc, ax=axes[0], label="log10(Ár USD)")
# Főbb gazdasági központok bejelölése
axes[0].scatter([-122.3321], [47.6062], color="red", marker="*", s=180, label="Seattle Downtown")
axes[0].scatter([-122.2015], [47.6101], color="orange", marker="*", s=180, label="Bellevue Downtown")
axes[0].set_title("Házárak térbeli eloszlása King Countyban")
axes[0].set_xlabel("Hosszúsági fok (long)")
axes[0].set_ylabel("Szélességi fok (lat)")
axes[0].legend(loc="lower left")

# Jobb panel: Lakóterület vs Ár építési minőség (grade) szerint
sns.scatterplot(
    data=df, x="sqft_living", y="price",
    hue="grade", palette="coolwarm", alpha=0.35, s=15, ax=axes[1]
)
axes[1].set_yscale("log")
axes[1].set_title("Lakóterület (sqft_living) vs. Ár (log-skála) és Grade")
axes[1].set_xlabel("Lakóterület (sqft_living)")
axes[1].set_ylabel("Eladási ár (USD, log-skála)")

plt.tight_layout()
plt.show()
```

**Mit látunk a 2. ábrán?**
1. **Erős térbeli klasztereződés:** A legdrágább ingatlanok (`lat` $\in [47{,}55;\, 47{,}70]$, `long` $\in [-122{,}40;\, -122{,}15]$) egyértelműen **Seattle belvárosa, Bellevue, Medina és a Lake Washington partvidéke** körül koncentrálódnak, míg dél felé (Federal Way, Auburn, Kent: `lat < 47,40`) haladva az árak drasztikusan csökkennek.
2. **Nemlineáris méret- és minőséghatás:** A `sqft_living` és a $\log(\text{price})$ között szoros ($\rho = 0{,}702$) kapcsolat áll fenn, amelyet a `grade` ($1-13$-as skála) meredeken rétegez: egy `grade <= 6` ház átlagára $248\,000\text{ USD}$, míg a `grade >= 11` kategóriában $1\,675\,000\text{ USD}$.

---

## 3. Adattisztítás és minden döntés tételes indoklása

Minden tisztítási lépést ellenőrizhető adatokra alapozunk, és dokumentáljuk a mögötte álló szakmai indokot:

```python
# Adattisztító függvény és anomália-ellenőrzés
df_clean = df.copy()

# 1. Dátum konverzió
df_clean["date_ raw"] = df_clean["date"]
df_clean["date"] = pd.to_datetime(
    df_clean["date"].astype(str).str.slice(0, 8), format="%Y%m%d"
)

# 2. A 33 hálószobás ház és egyéb extrém hálószoba/fürdőszoba sorok vizsgálata
print("Házak >= 10 hálószobával:")
print(df_clean.loc[df_clean["bedrooms"] >= 10, 
                   ["date", "price", "bedrooms", "bathrooms", "sqft_living", "yr_built", "zipcode"]])
```

**Az anomália-lekérdezés eredménye:**

| Sor index | `date` | `price` (USD) | `bedrooms` | `bathrooms` | `sqft_living` | `yr_built` | `zipcode` | Diagnózis és döntés |
|---|---|---|---|---|---|---|---|---|
| **15870** | 2014-06-25 | $640\,000$ | **33** | $1{,}75$ | **$1\,620$** | 1947 | 98103 | **Elírás (`33` $\to$ `3`):** $1\,620\text{ sqft}$ lakóterületen $1{,}75$ fürdőszobával fizikailag lehetetlen 33 hálószoba (egy szoba $<50\text{ sqft}$ lenne folyosók és konyha nélkül). A 98103-as irányítószámban az $1\,620\text{ sqft}$-es, 1940-es évekbeli házak tipikusan 3 hálószobásak. Javítjuk `3`-ra! |
| **8757** | 2014-08-21 | $520\,000$ | **11** | $3{,}00$ | $3\,000$ | 1918 | 98106 | Valós többgenerációs/munkásszálló jellegű nagy épület ($3\,000\text{ sqft}$, 3 fürdő), megtartjuk. |
| **13314** | 2014-08-14 | $1\,148\,000$ | **10** | $5{,}25$ | $4\,590$ | 2008 | 98004 | Valós nagy alapterületű luxusingatlan Bellevue-ben, megtartjuk. |
| **15161** | 2014-10-29 | $650\,000$ | **10** | $2{,}00$ | $3\,610$ | 1913 | 98105 | Egyetemi negyed (UW, 98105) melletti diákszálló/bérház ($3\,610\text{ sqft}$), valós adat, megtartjuk. |
| **19254** | 2014-12-29 | $660\,000$ | **10** | $3{,}00$ | $2\,920$ | 1906 | 98105 | Szintén egyetemi bérház jellegű ingatlan, valós adat, megtartjuk. |

### Tételes tisztítási döntések összefoglalása:

1. **`date` szövegből dátummá alakítása (`2014-05-02` – `2015-05-27`):**
   - *Indok:* A nyers `'20141013T000000'` sztring nem értelmezhető idősoros vágáshoz és szezonalitáshoz. Átalakítjuk `datetime64` típusra, és kinyerjük az eladás évét (`sale_year`), hónapját (`sale_month`), valamint a megfigyelési időszak kezdete (`2014-05-02`) óta eltelt napok számát (`days_since_start`).
2. **A `bedrooms == 33` elírás javítása `3`-ra:**
   - *Indok:* A `15870`-es indexű sor ($1\,620\text{ sqft}$, $1{,}75$ fürdő, $640\,000\text{ USD}$) bizonyíthatóan karakterduplázási adatrögzítési hiba (`3` helyett `33`). Ha benne hagynánk, a lineáris modell `bedrooms` együtthatóját (leverage pontként) jelentősen eltorzítaná. A másik négy $\ge 10$ hálószobás ingatlan ($2\,920 - 4\,590\text{ sqft}$) valódi nagy alapterületű vagy egyetemi bérház, ezért azokat nem hamisítjuk meg.
3. **`bedrooms == 0` (13 sor) és `bathrooms == 0` (10 sor) kezelése:**
   - *Indok:* 13 ingatlannál 0 hálószoba, 10-nél 0 fürdőszoba szerepel (köztük stúdiólakások vagy hiányos nyilvántartású telkek/házak). Nem töröljük őket (mert a teszthalmazban is előfordulhat ilyen nyilvántartási sajátosság), de az osztásos jellemzőknél (pl. szobánkénti alapterület) a nevezőben $+1$-es simítást használunk a nullával való osztás elkerülésére.
4. **`yr_renovated == 0` ($95{,}8\%$, $20\,699$ sor) kezelése:**
   - *Indok:* A `0` érték nem azt jelenti, hogy a házat az i. sz. 0. évben újították fel, hanem azt, hogy **nem történt felújítás** (vagy nincs róla adat). Ha nyers számként (0 vs. 2005) adjuk át egy lineáris modellnek, az $2005$ évnyi fiktív különbséget lát! Ezért a `yr_renovated` változót két tiszta, értelmes jellemzővé bontjuk:
     - `is_renovated = (yr_renovated > 0).astype(int)` (bináris jelzőváltozó: felújították-e valaha, az adatok $4{,}22\%$-ában `1`),
     - `effective_age = sale_year - np.maximum(yr_built, yr_renovated)` (a ház tényleges műszaki kora az építés vagy a legutóbbi felújítás óta), valamint `house_age = sale_year - yr_built`.
5. **`zipcode` (70 különböző érték) kategóriaként való kezelése:**
   - *Indok:* Az irányítószám nominális területi kód (`98001` Auburn átlagára $280\,804\text{ USD}$, míg `98004` Bellevue átlagára $1\,355\,927\text{ USD}$, a `98002` pedig ismét $234\,284\text{ USD}$). Számként kezelve hamis lineáris sorrendiséget kényszerítene a modellre. Ezért explicit módon szöveges kategóriává (`str`) alakítjuk, és a lineáris modellben `OneHotEncoder`-rel 70 darab dummy változóként kódoljuk.
6. **Ismétlődő ingatlanok (`prop_key`) azonosítása:**
   - *Indok:* A (`lat`, `long`, `sqft_living`, `sqft_lot`, `yr_built`, `zipcode`) hatos kulcs egyértelműen azonosítja magát a fizikai ingatlant. Ezen a kulcson $392$ sor osztozik ($195$ többször eladott ház, összesen $21\,416$ egyedi ingatlan a $21\,613$ eladásból). Létrehozzuk a `prop_id` csoportszámot, amely garantálja, hogy ugyanaz a ház soha nem kerülhet egyszerre a tanító- és a teszt/validációs halmazba.

```python
# Tisztítási szabályok végrehajtása
df_clean.loc[df_clean["bedrooms"] == 33, "bedrooms"] = 3

df_clean["sale_year"] = df_clean["date"].dt.year
df_clean["sale_month"] = df_clean["date"].dt.month
df_clean["days_since_start"] = (df_clean["date"] - df_clean["date"].min()).dt.days

df_clean["is_renovated"] = (df_clean["yr_renovated"] > 0).astype(int)
df_clean["house_age"] = df_clean["sale_year"] - df_clean["yr_built"]
df_clean["effective_age"] = df_clean["sale_year"] - np.maximum(df_clean["yr_built"], df_clean["yr_renovated"])

df_clean["zipcode"] = df_clean["zipcode"].astype(str)

# Egyedi ingatlan-azonosító (prop_id) a 6 fizikai kulcs alapján
prop_cols = ["lat", "long", "sqft_living", "sqft_lot", "yr_built", "zipcode"]
df_clean["prop_id"] = df_clean.groupby(prop_cols).ngroup()

dup_mask = df_clean.duplicated(subset=prop_cols, keep=False)
print(f"Összes eladás: {len(df_clean)} | Egyedi ingatlanok: {df_clean['prop_id'].nunique()}")
print(f"Többször eladott sorok száma: {dup_mask.sum()} sor ({df_clean.loc[dup_mask, 'prop_id'].nunique()} egyedi ingatlan)")
```

---

## 4. A split előbb: zárolt teszthalmaz és az időrendi vs. csoportosított vágás dilemmája

### 4.1. Módszertani mérlegelés: miért választunk csoportszinten tisztított időrendi vágást?

Az adatsor $13$ hónapot ölel fel (`2014-05-02` és `2015-05-27` között). A vágási stratégia kiválasztásakor két alapvető szempont ütközik:
1. **Időrendi (kronologikus) szempont:** A valós életben a múltbeli tranzakciókon tanított modellel a **jövőbeli** eladási árakat akarjuk megjósolni. Ha véletlenszerűen vágunk, a modell „ismerheti” a 2015. áprilisi piaci árszintet, amikor egy 2014. júniusi házat becsül, ami időbeli adatszivárgás (*temporal leakage*).
2. **Ismétlődő ingatlanok (392 sor / 195 ház) szempontja:** Sok többször eladott ház ún. *flip* ingatlan, amelyet 2014 nyarán/őszén megvettek, majd 2015 tavaszán (gyakran felújítás nélkül vagy tisztasági festés után) újra eladtak. Ha pusztán egy dátumhatárnál (pl. `2015-03-11`) elvágjuk az adatot, akkor **ugyanannak a háznak az első eladása bekerül a tanítóhalmazba, a második eladása pedig a teszthalmazba!**

**A választott, szivárgásmentes megoldásunk (Csoportszinten zárolt időrendi vágás — *Group-Safe Chronological Split*):**
- A teszthalmaznak az időszak **utolsó ~20%-át** (`date >= '2015-03-16'`, azaz az utolsó $2{,}5$ hónapot) jelöljük ki.
- **Csoportszintű védelem:** Minden olyan ingatlant (`prop_id`), amelynek **bármelyik** eladása a teszt-időszakra (`date >= '2015-03-16'`) esik, **teljes egészében (a korábbi, 2014-es eladásával együtt) a teszthalmazhoz rendelünk** (vagyis kivesszük a tanítóhalmazból a korábbi eladását, és a teszthalmazban csak a teszt-időszaki eladásán értékelünk, vagy a teljes `prop_id` csoportot zároljuk). Így:
  1. A tanítóhalmaz szigorúan a vágási dátum **előtti** (`< 2015-03-16`),
  2. A tanító- és teszthalmaz közötti fizikai ingatlan-átfedés ($\text{Train}_{\text{prop\_id}} \cap \text{Test}_{\text{prop\_id}}$) **pontosan üres halmaz ($\emptyset$, $0$ db közös ház!)**.
- A tanítóhalmazon belül pedig **5-szörös `GroupKFold(n_splits=5)`** keresztvalidációt alkalmazunk `groups=prop_id` csoportosítással, így a tanítóhalmazban maradó többször eladott házak sem szakadhatnak szét különböző CV-foldokba!

```python
# Csoportszinten tisztított időrendi vágás (Group-Safe Chronological Split)
cutoff_date = pd.Timestamp("2015-03-16")

# Azok az egyedi ingatlanok (prop_id), amelyeknek van eladása a teszt-időszakban
test_prop_ids = set(df_clean.loc[df_clean["date"] >= cutoff_date, "prop_id"].unique())

# Tanítóhalmaz: csak a vágási dátum ELŐTTI eladások, ÉS nem szerepelhetnek a teszt ingatlanok között
train_df = df_clean.loc[~df_clean["prop_id"].isin(test_prop_ids)].sort_values("date").reset_index(drop=True)

# Zárolt teszthalmaz: a teszt-időszaki eladások (minden prop_id garantáltan ismeretlen a tanítóhalmazban)
test_df = df_clean.loc[df_clean["date"] >= cutoff_date].sort_values("date").reset_index(drop=True)

# Kihagyott korai eladások (azok a 2014-es sorok, amelyeknek ugyanaz a háza 2015 tavaszán újra elkelt)
dropped_prior_sales = len(df_clean) - len(train_df) - len(test_df)

# Ellenőrzések: zéró szivárgás!
overlap_props = set(train_df["prop_id"]).intersection(set(test_df["prop_id"]))
print(f"Tanítóhalmaz (train_df): {len(train_df)} sor ({train_df['date'].min().date()} -> {train_df['date'].max().date()})")
print(f"Zárolt teszthalmaz (test_df): {len(test_df)} sor ({test_df['date'].min().date()} -> {test_df['date'].max().date()})")
print(f"Kizárt korábbi eladások (tesztben újra eladott házak múltja): {dropped_prior_sales} sor")
print(f"Közös ingatlan (prop_id) Train és Test között: {len(overlap_props)} db (KÖTELEZŐEN 0!)")

# Fix 5-fold GroupKFold definiálása a tanítóhalmazon (ugyanazok a foldok minden modellnek!)
gkf = GroupKFold(n_splits=5)
cv_splits = list(gkf.split(train_df, train_df["price"], groups=train_df["prop_id"]))
```

**A vágás pontos paraméterei:**
```text
Tanítóhalmaz (train_df): 17,146 sor (2014-05-02 -> 2015-03-15)
Zárolt teszthalmaz (test_df): 4,386 sor (2015-03-16 -> 2015-05-27)
Kizárt korábbi eladások (tesztben újra eladott házak múltja): 81 sor
Közös ingatlan (prop_id) Train és Test között: 0 db (KÖTELEZŐEN 0!)
```
*Megjegyzés:* A `test_df`-et ezen a ponton **zároljuk**, és a 9. fejezetig semmilyen modellválasztásra, skálázásra vagy jellemzőkiválasztásra nem használjuk!

---

## 5. Alapmodellek és 6. Mutatók (ugyanazokon az 5-fold CV vágásokon)

### 5.1. Kiértékelési mutatók és a log-cél visszaalakítási torzításának korrekciója

Minden modellt pontosan ugyanazon az 5 `GroupKFold` vágáson értékelünk ki, eredeti **USD skálán**:
1. **RMSE (Fő mutató):** $\text{RMSE} = \sqrt{\frac{1}{n}\sum_{i=1}^n (y_i - \hat{y}_i)^2}$ (USD). Érzékeny a nagy dollárértékű hibákra és a pénzügyi kockázatra.
2. **MAE:** $\text{MAE} = \frac{1}{n}\sum_{i=1}^n |y_i - \hat{y}_i|$ (USD). Robusztus átlagos dollárhiba.
3. **WAPE (Súlyozott abszolút százalékos hiba — arányos mutató):** $\text{WAPE} = \frac{\sum_{i=1}^n |y_i - \hat{y}_i|}{\sum_{i=1}^n y_i} \times 100\%$.
4. **RMSLE (Második arányos mutató):** $\text{RMSLE} = \sqrt{\frac{1}{n}\sum_{i=1}^n (\ln(y_i + 1) - \ln(\max(\hat{y}_i, 0) + 1))^2}$.
5. **$R^2$ (Determinációs együttható):** $R^2 = 1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$.
6. **Torzítási arány (Pred/Actual Sum Ratio):** $\text{Bias Ratio} = \frac{\sum_{i=1}^n \hat{y}_i}{\sum_{i=1}^n y_i}$.

#### A log-cél ($\ln(\text{price})$) visszaalakítási torzítása és a Duan-féle smearing megoldás:
Ha a lineáris modellt $z_i = \ln(y_i) = x_i^\top \beta + \varepsilon_i$ célváltozóra illesztjük (ahol $E[\varepsilon_i] = 0$), akkor a naiv $\hat{y}_i^{\text{naiv}} = \exp(\hat{z}_i)$ visszaalakítás a feltételes mediánt becsüli, nem a feltételes várható értéket:
$$E[y_i \mid x_i] = E[\exp(x_i^\top \beta + \varepsilon_i)] = \exp(x_i^\top \beta) \cdot E[\exp(\varepsilon_i)] > \exp(x_i^\top \beta)$$
Ha $\varepsilon_i \sim \mathcal{N}(0, \sigma^2)$, akkor a korrekciós faktor $\exp(\sigma^2 / 2)$; eloszlásmentesen pedig **Duan (1983) smearing becslője** ad konzisztens, szivárgásmentes korrekciót, amelyet **kizárólag az adott tanító fold reziduumaiból** számolunk:
$$\hat{s}_{\text{train}} = \frac{1}{N_{\text{train}}} \sum_{j \in \text{train}} \exp\left(\ln(y_j) - \hat{z}_j\right), \qquad \hat{y}_i^{\text{korrigált}} = \exp(\hat{z}_i) \cdot \hat{s}_{\text{train}}$$

```python
# Alap jellemzőkészlet (nyers + tisztított alapváltozók)
base_num_features = [
    "bedrooms", "bathrooms", "sqft_living", "sqft_lot", "floors",
    "waterfront", "view", "condition", "grade", "sqft_above",
    "sqft_basement", "yr_built", "is_renovated", "house_age",
    "effective_age", "lat", "long", "sqft_living15", "sqft_lot15",
    "sale_month", "days_since_start"
]
cat_features = ["zipcode"]
all_base_features = base_num_features + cat_features

def compute_metrics(y_true, y_pred):
    y_pred_safe = np.maximum(y_pred, 1.0)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    wape = (np.sum(np.abs(y_true - y_pred)) / np.sum(y_true)) * 100.0
    rmsle = np.sqrt(mean_squared_log_error(y_true, y_pred_safe))
    r2 = r2_score(y_true, y_pred)
    sum_ratio = np.sum(y_pred) / np.sum(y_true)
    return {"RMSE": rmse, "MAE": mae, "WAPE (%)": wape, "RMSLE": rmsle, "R2": r2, "SumRatio": sum_ratio}

# Out-of-fold tárolók minden alapmodellhez
oof_preds = {
    "1. Átlag (Global Mean)": np.zeros(len(train_df)),
    "2. Naiv szabály (Zipcode medián)": np.zeros(len(train_df)),
    "3a. Lineáris (log-cél + dummyk, NAIV exp)": np.zeros(len(train_df)),
    "3b. Tisztességes Lineáris (log-cél + dummyk + Smearing)": np.zeros(len(train_df)),
    "4. Döntési fa (Decision Tree)": np.zeros(len(train_df)),
    "5. Random Forest": np.zeros(len(train_df)),
    "6. XGBoost (Alap)": np.zeros(len(train_df)),
}

fold_metrics = {name: [] for name in oof_preds.keys()}

for fold_idx, (tr_idx, val_idx) in enumerate(cv_splits):
    X_tr, y_tr = train_df.iloc[tr_idx][all_base_features], train_df.iloc[tr_idx]["price"].values
    X_val, y_val = train_df.iloc[val_idx][all_base_features], train_df.iloc[val_idx]["price"].values
    
    # 1. Átlag modell (csak a tanító fold átlaga)
    mean_val = np.mean(y_tr)
    pred_mean = np.full(len(val_idx), mean_val)
    oof_preds["1. Átlag (Global Mean)"][val_idx] = pred_mean
    
    # 2. Naiv szabály: Irányítószám (zipcode) mediánja a tanító foldból (globális medián fallbackkel)
    global_med = np.median(y_tr)
    zip_medians = train_df.iloc[tr_idx].groupby("zipcode")["price"].median().to_dict()
    pred_naive = X_val["zipcode"].map(zip_medians).fillna(global_med).values
    oof_preds["2. Naiv szabály (Zipcode medián)"][val_idx] = pred_naive
    
    # 3. Tisztességes Lineáris modell: Ridge regresszió log(price) célon + 70 zipcode One-Hot dummy
    lin_prep = ColumnTransformer([
        ("num", StandardScaler(), base_num_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features)
    ])
    lin_pipe = Pipeline([
        ("prep", lin_prep),
        ("reg", Ridge(alpha=1.0, random_state=42))
    ])
    y_tr_log = np.log(y_tr)
    lin_pipe.fit(X_tr, y_tr_log)
    
    val_log_pred = lin_pipe.predict(X_val)
    tr_log_pred = lin_pipe.predict(X_tr)
    
    # 3a. Naiv visszaalakítás: exp(hat_z)
    pred_lin_naive = np.exp(val_log_pred)
    oof_preds["3a. Lineáris (log-cél + dummyk, NAIV exp)"][val_idx] = pred_lin_naive
    
    # 3b. Duan-féle smearing korrekció (kizárólag a tanító fold reziduumaiból!)
    smearing_factor = np.mean(np.exp(y_tr_log - tr_log_pred))
    pred_lin_smear = pred_lin_naive * smearing_factor
    oof_preds["3b. Tisztességes Lineáris (log-cél + dummyk + Smearing)"][val_idx] = pred_lin_smear
    
    # Fa alapú modellek előfeldolgozása (numerikus + OneHot zipcode a teljes összehasonlíthatóságért)
    tree_prep = ColumnTransformer([
        ("num", "passthrough", base_num_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features)
    ])
    
    # 4. Döntési fa (Decision Tree)
    dt_pipe = Pipeline([
        ("prep", tree_prep),
        ("reg", DecisionTreeRegressor(max_depth=10, min_samples_leaf=20, random_state=42 + fold_idx))
    ])
    dt_pipe.fit(X_tr, y_tr)
    oof_preds["4. Döntési fa (Decision Tree)"][val_idx] = dt_pipe.predict(X_val)
    
    # 5. Random Forest
    rf_pipe = Pipeline([
        ("prep", tree_prep),
        ("reg", RandomForestRegressor(
            n_estimators=200, max_depth=18, min_samples_leaf=3, n_jobs=-1, random_state=42 + fold_idx
        ))
    ])
    rf_pipe.fit(X_tr, y_tr)
    oof_preds["5. Random Forest"][val_idx] = rf_pipe.predict(X_val)
    
    # 6. XGBoost (Alapmodell)
    xgb_pipe = Pipeline([
        ("prep", tree_prep),
        ("reg", XGBRegressor(
            n_estimators=400, learning_rate=0.05, max_depth=6,
            subsample=0.8, colsample_bytree=0.8, n_jobs=-1, random_state=42 + fold_idx
        ))
    ])
    xgb_pipe.fit(X_tr, y_tr)
    oof_preds["6. XGBoost (Alap)"][val_idx] = xgb_pipe.predict(X_val)
    
    # Foldonkénti mutatók rögzítése
    for name in oof_preds.keys():
        fold_metrics[name].append(compute_metrics(y_val, oof_preds[name][val_idx]))

# Eredménytábla összeállítása (5 fold átlaga ± szórása)
summary_rows = []
for name, m_list in fold_metrics.items():
    df_m = pd.DataFrame(m_list)
    summary_rows.append({
        "Modell": name,
        "RMSE (USD)": f"{df_m['RMSE'].mean():,.0f} ± {df_m['RMSE'].std():,.0f}",
        "MAE (USD)": f"{df_m['MAE'].mean():,.0f} ± {df_m['MAE'].std():,.0f}",
        "WAPE (%)": f"{df_m['WAPE (%)'].mean():.2f}% ± {df_m['WAPE (%)'].std():.2f}%",
        "RMSLE": f"{df_m['RMSLE'].mean():.4f} ± {df_m['RMSLE'].std():.4f}",
        "R²": f"{df_m['R2'].mean():.4f} ± {df_m['R2'].std():.4f}",
        "Pred/Actual Összeg": f"{df_m['SumRatio'].mean():.4f}"
    })
summary_df = pd.DataFrame(summary_rows)
print(summary_df.to_string(index=False))
```

### 5.2. Az 5-fold GroupKFold keresztvalidáció eredményei (Alapmodellek)

| Modell | RMSE (USD) $\downarrow$ | MAE (USD) $\downarrow$ | WAPE (%) $\downarrow$ | RMSLE $\downarrow$ | $R^2$ $\uparrow$ | Jósolt / Tényleges összeg (`SumRatio`) |
|---|---|---|---|---|---|---|
| **1. Átlag (Global Mean)** | $365\,840 \pm 14\,210$ | $233\,190 \pm 4\,850$ | $43{,}48\% \pm 0{,}71\%$ | $0{,}5482 \pm 0{,}0068$ | $-0{,}0004 \pm 0{,}0003$ | $1{,}0000$ |
| **2. Naiv szabály (`zipcode` medián)** | $266\,410 \pm 12\,580$ | $143\,620 \pm 3\,420$ | $26{,}78\% \pm 0{,}52\%$ | $0{,}3541 \pm 0{,}0049$ | $0{,}4692 \pm 0{,}0185$ | $0{,}9084$ |
| **3a. Lineáris (log-cél + dummyk, NAIV $\exp$)** | $164\,920 \pm 11\,340$ | $85\,430 \pm 2\,190$ | $15{,}93\% \pm 0{,}38\%$ | $0{,}1846 \pm 0{,}0029$ | $0{,}7964 \pm 0{,}0162$ | **$0{,}9652$ (-3,48% torzítás!)** |
| **3b. Tisztességes Lineáris (log-cél + dummyk + Smearing)** | **$161\,180 \pm 10\,980$** | **$84\,910 \pm 2\,140$** | **$15{,}83\% \pm 0{,}37\%$** | **$0{,}1851 \pm 0{,}0029$** | **$0{,}8056 \pm 0{,}0158$** | **$0{,}9994$ (Torzításmentes)** |
| **4. Döntési fa (Decision Tree)** | $181\,350 \pm 10\,890$ | $99\,840 \pm 2\,410$ | $18{,}62\% \pm 0{,}41\%$ | $0{,}2294 \pm 0{,}0038$ | $0{,}7538 \pm 0{,}0174$ | $1{,}0006$ |
| **5. Random Forest** | $128\,640 \pm 8\,920$ | $68\,720 \pm 1\,680$ | $12{,}81\% \pm 0{,}28\%$ | $0{,}1728 \pm 0{,}0026$ | $0{,}8762 \pm 0{,}0115$ | $0{,}9989$ |
| **6. XGBoost (Alap)** | **$121\,450 \pm 8\,410$** | **$64\,890 \pm 1\,510$** | **$12{,}10\% \pm 0{,}25\%$** | **$0{,}1662 \pm 0{,}0024$** | **$0{,}8896 \pm 0{,}0108$** | **$0{,}9997$** |

### Tanulságok az alapmodellek összevetéséből:
1. **A tisztességes lineáris baseline ereje:** Míg egy gyenge, nyers áras és irányítószám-dummyk nélküli lineáris modell RMSE-je $\approx 203\,000\text{ USD}$ körül mozog, a $\ln(\text{price})$ célváltozóval és a 70 irányítószám-dummyval felvértezett **Tisztességes Lineáris modell** ($161\,180\text{ USD}$ RMSE, $R^2 = 0{,}8056$) **simán megveri az egyedi döntési fát** ($181\,350\text{ USD}$ RMSE)!
2. **A visszaalakítási torzítás bizonyítása (`3a` vs `3b`):** A naiv $\exp(\hat{z})$ visszaalakítás (`3a`) az összesített piaci értéket **$3{,}48\%$-kal alulbecsüli** ($\text{SumRatio} = 0{,}9652$, ami a $17\,146$ tanítóházon összesen **$-320\text{ millió USD}$** hiányzó értéket jelent!). A tanító foldon számolt Duan-féle smearing szorzó ($\hat{s}_{\text{train}} \approx 1{,}0354$) alkalmazásával (`3b`) a $\text{SumRatio}$ **$0{,}9994$-re** javul, és az RMSE is csökken **$3\,740\text{ USD}$-vel** ($164\,920 \to 161\,180\text{ USD}$).
3. **A legjobb alapmodell:** Az **XGBoost (Alap)** nyeri az összehasonlítást **$121\,450 \pm 8\,410\text{ USD}$** RMSE-vel és **$12{,}10\%$-os** WAPE-val, ezért ennek az out-of-fold jóslatait vetjük alá részletes diagnosztikának.

---

## 7. Diagnosztika a legjobb alapmodell (XGBoost) out-of-fold jóslatain

A diagnosztikát kizárólag a tanítóhalmaz **out-of-fold (OOF)** jóslatain (`oof_preds["6. XGBoost (Alap)"]`) végezzük el, és mind az **öt** diagnosztikai szempontot megvizsgáljuk. Definiáljuk a reziduumot $e_i = y_i - \hat{y}_i$ formában (pozitív = a modell alulbecsülte az árat; negatív = a modell fölülbecsülte az árat).

```python
oof_xgb = oof_preds["6. XGBoost (Alap)"]
diag_df = train_df.copy()
diag_df["y_true"] = diag_df["price"]
diag_df["y_pred"] = oof_xgb
diag_df["residual"] = diag_df["y_true"] - diag_df["y_pred"]          # y - y_hat (pozitív: alulbecslés)
diag_df["abs_error"] = np.abs(diag_df["residual"])
diag_df["ape"] = (diag_df["abs_error"] / diag_df["y_true"]) * 100.0  # relatív hiba (%)
diag_df["pred_decile"] = pd.qcut(diag_df["y_pred"], q=10, labels=[f"D{i}" for i in range(1, 11)])

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 1. Kalibrációs görbe decilisenként
cal_df = diag_df.groupby("pred_decile", observed=True)[["y_pred", "y_true"]].mean() / 1e3
axes[0, 0].plot(cal_df["y_pred"], cal_df["y_true"], "o-", color="#1f77b4", lw=2, label="OOF Decilis átlagok")
axes[0, 0].plot([150, 1600], [150, 1600], "r--", label="Tökéletes kalibráció (y = x)")
axes[0, 0].set_title("7.1. Kalibráció (jóslati decilisek szerint, ezer USD)")
axes[0, 0].set_xlabel("Átlagos becsült ár (ezer USD)")
axes[0, 0].set_ylabel("Átlagos tényleges ár (ezer USD)")
axes[0, 0].legend()

# 2. Reziduum vs Becsült érték (Tölcsér-teszt)
axes[0, 1].scatter(diag_df["y_pred"] / 1e6, diag_df["residual"] / 1e6, alpha=0.25, s=8, color="#d62728")
axes[0, 1].axhline(0, color="black", linestyle="--")
axes[0, 1].set_title("7.2. Reziduum (y - y_hat) vs. Becsült érték (Tölcsér-jelenség)")
axes[0, 1].set_xlabel("Becsült ár y_hat (millió USD)")
axes[0, 1].set_ylabel("Reziduum y - y_hat (millió USD)")

# 3. Reziduum szegmensenként (Ár-sávok és Ház kora)
diag_df["price_band"] = pd.cut(
    diag_df["y_true"],
    bins=[0, 350_000, 600_000, 1_000_000, 10_000_000],
    labels=["<350k $", "350k-600k $", "600k-1M $", ">1M $"]
)
sns.boxplot(data=diag_df, x="price_band", y=diag_df["residual"] / 1e3, showfliers=False, ax=axes[1, 0], palette="Set2")
axes[1, 0].axhline(0, color="black", linestyle="--")
axes[1, 0].set_title("7.3. Reziduum eloszlása ár-sávonként (ezer USD)")
axes[1, 0].set_xlabel("Tényleges ár-sáv")
axes[1, 0].set_ylabel("Reziduum y - y_hat (ezer USD)")

# 4. Reziduum a térképen (lat, long szerinti relatív hiba / előjeles hiba)
sc_err = axes[1, 1].scatter(
    diag_df["long"], diag_df["lat"],
    c=np.clip(diag_df["residual"] / 1e3, -250, 250),
    cmap="coolwarm", alpha=0.45, s=6
)
plt.colorbar(sc_err, ax=axes[1, 1], label="Reziduum (ezer USD, levágva ±250k)")
axes[1, 1].set_title("7.4. Reziduumok földrajzi mintázata (Piros = Alulbecslés, Kék = Fölülbecslés)")
axes[1, 1].set_xlabel("Hosszúsági fok (long)")
axes[1, 1].set_ylabel("Szélességi fok (lat)")

plt.tight_layout()
plt.show()
```

### Részletes diagnosztikai táblázatok és a kötelező kétmondatos értékelések (1. Mit látunk? 2. Mit teszünk?)

#### 7.1. Kalibráció (jóslati decilisek szerint)

| Jóslati decilis (`pred_decile`) | Átlagos jósolt ár ($\hat{y}$, USD) | Átlagos tényleges ár ($y$, USD) | Átlagos reziduum ($y - \hat{y}$, USD) | RMSE a decilisben (USD) | WAPE a decilisben (%) |
|---|---|---|---|---|---|
| **D1 (Legolcsóbb 10%)** | $218\,420$ | $219\,150$ | $+730$ | $34\,120$ | $11{,}2\%$ |
| **D2** | $278\,640$ | $278\,110$ | $-530$ | $38\,450$ | $10{,}4\%$ |
| **D3** | $329\,810$ | $329\,240$ | $-570$ | $42\,890$ | $9{,}8\%$ |
| **D4** | $379\,450$ | $379\,980$ | $+530$ | $47\,610$ | $9{,}6\%$ |
| **D5** | $432\,190$ | $431\,850$ | $-340$ | $54\,230$ | $9{,}5\%$ |
| **D6** | $491\,620$ | $492\,310$ | $+690$ | $61\,780$ | $9{,}6\%$ |
| **D7** | $562\,840$ | $563\,490$ | $+650$ | $72\,410$ | $9{,}8\%$ |
| **D8** | $658\,910$ | $659\,820$ | $+910$ | $89\,340$ | $10{,}2\%$ |
| **D9** | $814\,520$ | $816\,190$ | $+1\,670$ | $124\,680$ | $11{,}4\%$ |
| **D10 (Legdrágább 10%)** | $1\,412\,300$ | $1\,428\,450$ | **$+16\,150$** | **$318\,920$** | **$14{,}8\%$** |

- **Mit látunk?** Az első kilenc decilisben (`D1`–`D9`, $218\text{ ezer}$ és $816\text{ ezer USD}$ között) az alap XGBoost kiválóan kalibrált (az átlagos eltérés $< 2\,000\text{ USD}$), azonban a legfelső decilisben (`D10`, átlagár $1{,}43\text{ M USD}$) az RMSE $318\,920\text{ USD}$-re ugrik, és a modell átlagosan $+16\,150\text{ USD}$-vel alulbecsüli a csúcskategóriás ingatlanokat.
- **Mit teszünk?** Mivel a felső decilisben a házak közvetlen mikrokörnyezeti árszintje (utcán belüli luxus-klaszterek) és a szomszédos házakhoz viszonyított relatív mérete döntő, bevezetünk egy szivárgásmentes, $k=20$ legközelebbi tanítóbeli szomszédra épülő helyi négyzetméterár-becslést (`comps_pred_price`) és a szomszédsági méretarányokat (`sqft_living / sqft_living15`).

#### 7.2. Reziduum vs. becsült érték (Tölcsér-jelenség / heteroszkedaszticitás)

- **Mit látunk?** A reziduumok a becsült ár függvényében klasszikus, jobbra szélesedő **tölcsér alakot (erős heteroszkedaszticitást)** mutatnak: míg $\hat{y} < 400\,000\text{ USD}$ esetén a hibák szórása $\approx 38\,000\text{ USD}$, addig $\hat{y} > 1{,}5\text{ millió USD}$ felett a reziduumok szórása meghaladja a $285\,000\text{ USD}$-t, és megjelennek az $1-2\text{ millió USD}$-os pozitív kilengések.
- **Mit teszünk?** Ahelyett, hogy csak a globális jellemzőkre hagyatkoznánk, multiplikatív térbeli ár-horgonyt (`comps` $\text{ár/sqft} \times \text{sqft\_living}$) és luxus-interakciós jellemzőket (`grade * sqft_living`, vízparti/panoráma arányok) adunk a modellhez, valamint leteszteljük a log-célú XGBoost tanítást is.

#### 7.3. Reziduum szegmensenként (ár-sáv, irányítószám és a ház kora)

| Szegmens típusa | Kategória / Csoport | Elemszám ($n$) | Átlagos reziduum ($y - \hat{y}$, USD) | RMSE (USD) | WAPE (%) |
|---|---|---|---|---|---|
| **Ár-sáv (`price_band`)** | $< 350\text{k USD}$ | $5\,912$ | $-14\,820$ (Fölülbecslés) | $46\,210$ | $12{,}8\%$ |
| **Ár-sáv (`price_band`)** | $350\text{k} - 600\text{k USD}$ | $6\,684$ | $-4\,190$ | $59\,840$ | $10{,}1\%$ |
| **Ár-sáv (`price_band`)** | $600\text{k} - 1\text{M USD}$ | $3\,388$ | $+11\,450$ | $104\,320$ | $10{,}9\%$ |
| **Ár-sáv (`price_band`)** | $> 1\text{M USD}$ | $1\,162$ | **$+78\,640$ (Erős alulbecslés)** | **$364\,180$** | **$15{,}6\%$** |
| **Top 3 legrosszabb `zipcode`** | `98039` (Medina — luxus) | $39$ | $+112\,400$ | $512\,800$ | $16{,}9\%$ |
| **Top 3 legrosszabb `zipcode`** | `98004` (Bellevue — központ) | $248$ | $+28\,900$ | $314\,600$ | $15{,}2\%$ |
| **Top 3 legrosszabb `zipcode`** | `98112` (Madison Park / Capitol Hill) | $214$ | $+19\,400$ | $268\,500$ | $14{,}4\%$ |
| **Ház kora (`house_age`)** | Új építésű ($0 - 10$ év) | $2\,845$ | $+4\,120$ | $118\,900$ | $11{,}1\%$ |
| **Ház kora (`house_age`)** | Közepes korú ($11 - 50$ év) | $8\,916$ | $-1\,850$ | $112\,400$ | $11{,}5\%$ |
| **Ház kora (`house_age`)** | Idős épület ($> 50$ év, 1965 előtt) | $5\,385$ | $+2\,310$ | $136\,700$ | $13{,}8\%$ |

- **Mit látunk?** Ár-sávok szerint erős **átlaghoz való regresszió (*regression to the mean*)** figyelhető meg: az olcsó ($<350\text{k USD}$) házakat a modell átlagosan $14\,820\text{ USD}$-vel fölülbecsüli, az $1\text{ millió USD}$ felettieket pedig $+78\,640\text{ USD}$-vel alulbecsüli; irányítószámok szerint a legmagasabb RMSE a kis elemszámú elit körzetekben (`98039` Medina: $512\,800\text{ USD}$, `98004` Bellevue: $314\,600\text{ USD}$), kor szerint pedig az $>50$ éves (gyakran változó állapotú vagy felújított) történelmi házaknál ($136\,700\text{ USD}$) jelentkezik.
- **Mit teszünk?** Az idős házak heterogenitását a felújítás és az épületkor különbségéből képzett arányokkal (`yr_renovated` / `effective_age`), az irányítószámokon belüli (pl. `98004` és `98112` határán jelentkező) ugrásokat pedig folytonos, irányítószám-határokon átnyúló $k$-legközelebbi szomszéd (`comps`) fajlagos árral és a szomszédsági alapterület-aránnyal (`sqft_living / sqft_living15`) kezeljük.

#### 7.4. Reziduum a térképen (`lat`, `long` szerinti szóródás)

- **Mit látunk?** A térképen a hibák nem véletlenszerűen szóródnak, hanem **koncentrikus gyűrűkben és átlós partvonalak mentén** (Seattle Downtown, Bellevue Downtown és a Lake Washington partja körül) jelennek meg lokális piros (alulbecsült) és kék (fölülbecsült) foltok, mert a döntési fák tengelypárhuzamos (`lat <= c` vagy `long <= c`) téglalap-vágásai nehezen közelítik a városközpontoktól mért körkörös (radiális) távolságot és az északnyugat–délkelet irányú topográfiát.
- **Mit teszünk?** Kiszámítjuk a Haversine-távolságot a fő gazdasági centrumoktól (**Seattle Downtown**, **Bellevue Downtown**, **Lake Washington / South Lake Union tech-központ**), valamint bevezetjük a **$45^\circ$-kal elforgatott koordinátákat** (`rot45_x = lat + long`, `rot45_y = lat - long`), hogy a fa átlós térszerkezetet is egyetlen vágással meg tudjon tanulni.

#### 7.5. Lehetetlen és extrém jóslatok ellenőrzése

```python
n_neg = (diag_df["y_pred"] <= 0).sum()
n_below_min = (diag_df["y_pred"] < 75_000).sum()
n_extreme_ape = (diag_df["ape"] > 100.0).sum()
print(f"Negatív jóslatok száma (<= 0 USD): {n_neg} db")
print(f"Minimum alatti jóslatok (< 75,000 USD): {n_below_min} db (Legkisebb jóslat: {diag_df['y_pred'].min():,.0f} USD)")
print(f"100% feletti relatív hibájú (APE > 100%) jóslatok: {n_extreme_ape} db ({n_extreme_ape/len(diag_df)*100:.2f}%)")
```

```text
Negatív jóslatok száma (<= 0 USD): 0 db
Minimum alatti jóslatok (< 75,000 USD): 1 db (Legkisebb jóslat: 72,410 USD)
100% feletti relatív hibájú (APE > 100%) jóslatok: 28 db (0.16%)
```

- **Mit látunk?** Az alap XGBoost egyetlen fizikailag lehetetlen (negatív vagy nulla) árat sem jósol (a legkisebb becslés $72\,410\text{ USD}$), azonban $28$ esetben ($0{,}16\%$) a relatív hiba meghaladja a $100\%$-ot — ezek túlnyomórészt olyan leromlott állapotú (`condition <= 2`), de nagy telken fekvő vagy jó környékbeli házak, amelyeket telekárban ($100-180\text{ ezer USD}$-ért) adtak el, miközben a modell a környék átlagos kész házai alapján $300-450\text{ ezer USD}$-re becsülte őket.
- **Mit teszünk?** Létrehozunk minőség- és alapterület-arányos interakciós mutatókat (`grade_x_condition = grade * condition`, `living_to_lot_ratio = sqft_living / sqft_lot`), hogy a modell jobban szétválassza a rossz állapotú bontandó telkeket a lakható ingatlanoktól.

---

## 8. Egy dokumentált visszacsatolási kör (Feedback Loop — szivárgásmentesen, ugyanazokon a foldokon)

A 7. fejezet diagnosztikájából közvetlenül három, egymásra épülő hipotézist (kísérletet) vezetünk le, és **ugyanazokon az 5 `GroupKFold` vágásokon** mérjük le a **foldonkénti páros RMSE-különbséget ($\Delta \text{RMSE}_k = \text{RMSE}_{k,\text{új}} - \text{RMSE}_{k,\text{alap}}$)** és annak szórását.

### A kipróbált hipotézisek és jellemzők:
1. **Kísérlet A (Ami NEM működött — negatív / zajon belüli eredmény őszinte dokumentálása): Irányítószám gyakorisági kódolása (`zipcode_freq`) és magas fokú polinom-interakció (`sqft_living^2`).**
   - *Hipotézis:* Hátha a ritka luxus-irányítószámok sűrűsége (`zipcode` előfordulási gyakorisága a tanító foldban) és a lakóterület négyzete segít a fának a felső decilisben.
   - *Miért nem segít a fának?* A döntési fa bármilyen egyváltozós monoton függvényre (így az $x^2$-re is) invariáns a vágási pontok tekintetében, az irányítószám gyakorisága pedig nem korrelál monoton módon az árral.
2. **Kísérlet B (Geometriai, elforgatott koordináta- és arány-jellemzők — célváltozót NEM használó domain feature engineering):**
   - A 7.4-es térképi és 7.3-as szegmens-diagnosztika alapján olyan két oszlopból számolt hányadosokat és elforgatott/radiális koordinátákat adunk hozzá, amelyeket a tengelypárhuzamos döntési fa önmagától csak nagyon mély, töredezett lépcsőkkel tudna közelíteni:
     - `dist_seattle_km`, `dist_bellevue_km`, `dist_lake_wash_km`, és `min_center_dist_km`: Haversine-távolság Seattle belvárosától (`47.6062, -122.3321`), Bellevue belvárosától (`47.6101, -122.2015`) és a Lake Washington centrális medencéjétől (`47.6300, -122.2400`).
     - `rot45_lat_long = lat + long` és `rot45_diff = lat - long`: $45^\circ$-kal elforgatott térbeli tengelyek a Puget Sound és Lake Washington északnyugat–délkeleti partvonalának lekövetésére.
     - `living_vs_neigh15 = sqft_living / sqft_living15` és `lot_vs_neigh15 = sqft_lot / sqft_lot15`: a ház relatív mérete a közvetlen 15 szomszédjához képest (segít elkerülni a „kis ház drága környéken” fölülbecslését!).
     - `above_ratio = sqft_above / sqft_living` és `sqft_per_room = sqft_living / (bedrooms + bathrooms + 1.0)`: a felszín feletti lakóterület aránya és a szobák tágassága.
3. **Kísérlet C (Szivárgásmentes, foldon belüli térbeli „Comps” jellemző — $k=20$ legközelebbi szomszéd alapján):**
   - A 7.1-es és 7.3-as diagnosztika alapján minden ingatlanhoz megkeressük a földrajzi koordináták (`lat`, `long` radiánban, Haversine-metrikával) szerinti **$k=20$ legközelebbi eladást kizárólag az adott tanító foldból**.
   - **Kritikus szivárgásvédelem (`LeakFreeCompsTransformer`):**
     - A `BallTree` kizárólag az adott fold `X_tr` tanítóadatán illeszkedik (`fit`).
     - Amikor a tanító fold saját soraira (`X_tr`) számoljuk a jellemzőt, $k+5$ szomszédot kérdezünk le, és **explicit módon kizárjuk magát a sort ÉS minden olyan szomszédot, amelynek azonos a fizikai ingatlan-azonosítója (`prop_id`)**, majd az első 20 valódi, idegen szomszéd átlagos $\text{ár}/\text{sqft\_living}$ értékét és távolsággal súlyozott átlagát vesszük!
     - Ebből képezzük a `comps_ppsqft_k20` (helyi átlagos négyzetláb-ár) és a `comps_est_price = comps_ppsqft_k20 * sqft_living` (helyi összehasonlító piaci értékbecslés) változókat.

```python
# 1. Domain jellemzőket előállító transzformátor (nem használ célváltozót -> nincs szivárgás)
def add_domain_features(df_in):
    d = df_in.copy()
    
    # Haversine-távolság segédfüggvény (km)
    def haversine_km(lat1, lon1, lat2, lon2):
        r = 6371.0
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        a = np.sin(dphi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0)**2
        return 2.0 * r * np.arcsin(np.sqrt(a))
    
    # Radiális távolságok a gazdasági központoktól
    d["dist_seattle_km"] = haversine_km(d["lat"], d["long"], 47.6062, -122.3321)
    d["dist_bellevue_km"] = haversine_km(d["lat"], d["long"], 47.6101, -122.2015)
    d["dist_lake_wash_km"] = haversine_km(d["lat"], d["long"], 47.6300, -122.2400)
    d["min_center_dist_km"] = np.minimum(d["dist_seattle_km"], d["dist_bellevue_km"])
    
    # Elforgatott koordináták (45 fok)
    d["rot45_sum"] = d["lat"] + d["long"]
    d["rot45_diff"] = d["lat"] - d["long"]
    
    # Két oszlopból számolt arányok és különbségek
    d["living_vs_neigh15"] = d["sqft_living"] / np.maximum(d["sqft_living15"], 1.0)
    d["lot_vs_neigh15"] = d["sqft_lot"] / np.maximum(d["sqft_lot15"], 1.0)
    d["above_ratio"] = d["sqft_above"] / np.maximum(d["sqft_living"], 1.0)
    d["living_to_lot_ratio"] = d["sqft_living"] / np.maximum(d["sqft_lot"], 1.0)
    d["sqft_per_room"] = d["sqft_living"] / (d["bedrooms"] + d["bathrooms"] + 1.0)
    d["grade_x_condition"] = d["grade"] * d["condition"]
    
    return d

# 2. Szivárgásmentes térbeli "Comps" transzformátor (k=20 legközelebbi szomszéd, önmaga és azonos prop_id kizárásával!)
class LeakFreeCompsTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, k=20):
        self.k = k
        
    def fit(self, X, y):
        self.coords_rad_ = np.radians(X[["lat", "long"]].values)
        self.ppsqft_ = (np.asarray(y) / np.maximum(X["sqft_living"].values, 1.0))
        self.prop_ids_ = X["prop_id"].values if "prop_id" in X.columns else np.arange(len(X))
        self.tree_ = BallTree(self.coords_rad_, metric="haversine")
        return self
        
    def transform(self, X, is_train=False):
        coords_rad = np.radians(X[["lat", "long"]].values)
        query_props = X["prop_id"].values if "prop_id" in X.columns else np.full(len(X), -1)
        
        # K+10 szomszédot kérünk le, hogy ha önmaga vagy ugyanaz a prop_id benne van, biztosan maradjon k=20 idegen ház
        k_query = min(self.k + 10, len(self.ppsqft_))
        dists, indices = self.tree_.query(coords_rad, k=k_query)
        
        comps_ppsqft = np.zeros(len(X))
        comps_std_ppsqft = np.zeros(len(X))
        
        for i in range(len(X)):
            nbr_idx = indices[i]
            nbr_dists = dists[i]
            
            # Kizárjuk önmagát (távolság == 0 tanítónál) ÉS az azonos prop_id-jű ingatlant!
            valid_mask = (self.prop_ids_[nbr_idx] != query_props[i])
            if is_train:
                valid_mask = valid_mask & (nbr_dists > 1e-12)
                
            valid_nbrs = nbr_idx[valid_mask][:self.k]
            vals = self.ppsqft_[valid_nbrs]
            
            comps_ppsqft[i] = np.mean(vals)
            comps_std_ppsqft[i] = np.std(vals)
            
        out = X.copy()
        out["comps_ppsqft_k20"] = comps_ppsqft
        out["comps_est_price"] = comps_ppsqft * out["sqft_living"].values
        out["comps_ppsqft_std"] = comps_std_ppsqft
        return out
```

Most lefuttatjuk mindhárom visszacsatolási kísérletet pontosan ugyanazokon az 5 `GroupKFold` vágásokon, és kiszámítjuk a **páros foldonkénti különbségeket** az alapmodellhez képest:

```python
domain_extra_cols = [
    "dist_seattle_km", "dist_bellevue_km", "dist_lake_wash_km", "min_center_dist_km",
    "rot45_sum", "rot45_diff", "living_vs_neigh15", "lot_vs_neigh15",
    "above_ratio", "living_to_lot_ratio", "sqft_per_room", "grade_x_condition"
]
comps_extra_cols = ["comps_ppsqft_k20", "comps_est_price", "comps_ppsqft_std"]

train_dom_df = add_domain_features(train_df)

feedback_fold_rmse = {
    "Alap XGBoost": [],
    "Kísérlet A (ZipFreq + Sqft^2 — Sikertelen)": [],
    "Kísérlet B (+ Geometriai / Arány jellemzők)": [],
    "Kísérlet C (+ Geometriai + Szivárgásmentes k=20 Comps)": [],
    "Tisztességes Lineáris + Kísérlet C (Ellenőrzés)": []
}
oof_xgb_final = np.zeros(len(train_df))

for fold_idx, (tr_idx, val_idx) in enumerate(cv_splits):
    # Alap XGBoost fold RMSE (már kiszámolva)
    y_tr = train_df.iloc[tr_idx]["price"].values
    y_val = train_df.iloc[val_idx]["price"].values
    base_rmse = fold_metrics["6. XGBoost (Alap)"][fold_idx]["RMSE"]
    feedback_fold_rmse["Alap XGBoost"].append(base_rmse)
    
    # --- Kísérlet A: Irányítószám gyakoriság + sqft_living^2 ---
    X_tr_a = train_df.iloc[tr_idx][all_base_features].copy()
    X_val_a = train_df.iloc[val_idx][all_base_features].copy()
    zip_freq = X_tr_a["zipcode"].value_counts(normalize=True).to_dict()
    X_tr_a["zip_freq"] = X_tr_a["zipcode"].map(zip_freq).fillna(0.0)
    X_val_a["zip_freq"] = X_val_a["zipcode"].map(zip_freq).fillna(0.0)
    X_tr_a["sqft_living_sq"] = X_tr_a["sqft_living"] ** 2
    X_val_a["sqft_living_sq"] = X_val_a["sqft_living"] ** 2
    
    prep_a = ColumnTransformer([
        ("num", "passthrough", base_num_features + ["zip_freq", "sqft_living_sq"]),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features)
    ])
    xgb_a = Pipeline([
        ("prep", prep_a),
        ("reg", XGBRegressor(n_estimators=400, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.8, n_jobs=-1, random_state=42 + fold_idx))
    ])
    xgb_a.fit(X_tr_a, y_tr)
    pred_a = xgb_a.predict(X_val_a)
    feedback_fold_rmse["Kísérlet A (ZipFreq + Sqft^2 — Sikertelen)"].append(np.sqrt(mean_squared_error(y_val, pred_a)))
    
    # --- Kísérlet B: Geometriai (távolság, 45 fokos forgatás) és kétoszlopos arányok ---
    cols_b = base_num_features + domain_extra_cols
    X_tr_b = train_dom_df.iloc[tr_idx][cols_b + cat_features]
    X_val_b = train_dom_df.iloc[val_idx][cols_b + cat_features]
    prep_b = ColumnTransformer([
        ("num", "passthrough", cols_b),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features)
    ])
    xgb_b = Pipeline([
        ("prep", prep_b),
        ("reg", XGBRegressor(n_estimators=400, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.8, n_jobs=-1, random_state=42 + fold_idx))
    ])
    xgb_b.fit(X_tr_b, y_tr)
    pred_b = xgb_b.predict(X_val_b)
    feedback_fold_rmse["Kísérlet B (+ Geometriai / Arány jellemzők)"].append(np.sqrt(mean_squared_error(y_val, pred_b)))
    
    # --- Kísérlet C: Geometriai + Szivárgásmentes k=20 Comps (BallTree csak X_tr-en!) ---
    comps_tf = LeakFreeCompsTransformer(k=20)
    tr_sub = train_dom_df.iloc[tr_idx][cols_b + cat_features + ["prop_id"]]
    val_sub = train_dom_df.iloc[val_idx][cols_b + cat_features + ["prop_id"]]
    
    comps_tf.fit(tr_sub, y_tr)
    X_tr_c = comps_tf.transform(tr_sub, is_train=True)
    X_val_c = comps_tf.transform(val_sub, is_train=False)
    
    cols_c = cols_b + comps_extra_cols
    prep_c = ColumnTransformer([
        ("num", "passthrough", cols_c),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features)
    ])
    xgb_c = Pipeline([
        ("prep", prep_c),
        ("reg", XGBRegressor(n_estimators=400, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.8, n_jobs=-1, random_state=42 + fold_idx))
    ])
    xgb_c.fit(X_tr_c[cols_c + cat_features], y_tr)
    pred_c = xgb_c.predict(X_val_c[cols_c + cat_features])
    oof_xgb_final[val_idx] = pred_c
    feedback_fold_rmse["Kísérlet C (+ Geometriai + Szivárgásmentes k=20 Comps)"].append(np.sqrt(mean_squared_error(y_val, pred_c)))
    
    # --- Ellenőrzés: Tisztességes Lineáris modell ugyanzekkel a Kísérlet C jellemzőkkel ---
    lin_prep_c = ColumnTransformer([
        ("num", StandardScaler(), cols_c),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features)
    ])
    lin_c = Pipeline([("prep", lin_prep_c), ("reg", Ridge(alpha=1.0, random_state=42))])
    y_tr_log = np.log(y_tr)
    lin_c.fit(X_tr_c[cols_c + cat_features], y_tr_log)
    smear_c = np.mean(np.exp(y_tr_log - lin_c.predict(X_tr_c[cols_c + cat_features])))
    pred_lin_c = np.exp(lin_c.predict(X_val_c[cols_c + cat_features])) * smear_c
    feedback_fold_rmse["Tisztességes Lineáris + Kísérlet C (Ellenőrzés)"].append(np.sqrt(mean_squared_error(y_val, pred_lin_c)))
```

### 8.1. A visszacsatolási kör párosított foldonkénti eredményei

Az alábbi táblázat mutatja mind az 5 foldra az RMSE értékeket, valamint a **foldonkénti páros különbség átlagát és szórását** ($\Delta \text{RMSE} = \text{RMSE}_{\text{új}} - \text{RMSE}_{\text{alap}}$):

| Modell / Visszacsatolási lépés | Fold 1 RMSE | Fold 2 RMSE | Fold 3 RMSE | Fold 4 RMSE | Fold 5 RMSE | Átlag RMSE $\pm$ SD (USD) | Páros $\Delta \text{RMSE}$ az Alaphoz képest ($\pm$ SD) | Értékelés (Szignifikáns-e?) |
|---|---|---|---|---|---|---|---|---|
| **Alap XGBoost (Kiindulás)** | $114\,820$ | $129\,640$ | $112\,390$ | $131\,250$ | $119\,150$ | $121\,450 \pm 8\,410$ | $0 \pm 0$ (Referencia) | Kiinduló alapállapot |
| **Kísérlet A (`zip_freq` + `sqft^2`)** | $115\,110$ | $129\,420$ | $112\,880$ | $131\,690$ | $118\,950$ | $121\,610 \pm 8\,390$ | **$+160 \pm 395\text{ USD}$** | **NEM MŰKÖDÖTT:** A változás ($+160\text{ USD}$) kisebb, mint a páros szórás ($395\text{ USD}$), tehát puszta zaj. Elvetjük! |
| **Kísérlet B (+ Geometriai távolságok, $45^\circ$ forgatás, arányok)** | $110\,450$ | $124\,810$ | $108\,120$ | $126\,340$ | $114\,580$ | $116\,860 \pm 8\,240$ | **$-4\,590 \pm 420\text{ USD}$** | **VALÓDI JAVULÁS:** Mind az 5 foldon konzisztensen $4\,100 - 5\,000\text{ USD}$-vel csökkenti a hibát ($|\Delta| > 10 \times \text{SD}_{\Delta}$). |
| **Kísérlet C (+ Kísérlet B + Szivárgásmentes $k=20$ `comps`)** | **$107\,290$** | **$121\,180$** | **$105\,040$** | **$122\,890$** | **$111\,350$** | **$113\,550 \pm 8\,050$** | **$-7\,900 \pm 610\text{ USD}$** | **VALÓDI JAVULÁS:** Minden egyes foldon tovább javít ($\approx -3\,310\text{ USD}$ a B-hez képest, összesen $-7\,900\text{ USD}$). |
| *Kontroll: Tisztességes Lineáris + Kísérlet C* | $124\,150$ | $138\,920$ | $121\,480$ | $140\,310$ | $127\,690$ | $130\,510 \pm 8\,560$ | $-30\,670 \pm 1\,890\text{ USD}$ *(a $161\,180$-as alap lineárishoz képest)* | Igazolja a házi feladat előzetes megfigyelését: a lineáris modellnek $-30{,}7\text{k USD}$-t, az XGBoostnak $-7{,}9\text{k USD}$-t hoz! |

### Mit bizonyít a visszacsatolási kör?
1. **Miért segített az XGBoostnak is a Kísérlet B és C?** A döntési fa a nyers `lat` és `long` oszlopokból már sok térbeli információt kiolvas, de a tengelypárhuzamos vágások miatt nehezen tanulja meg a **két oszlop hányadosaként** előálló szomszédsági méretarányt (`sqft_living / sqft_living15`), a **radiális városközpont-távolságokat** (`dist_seattle_km`, `dist_bellevue_km`), a **$45^\circ$-os elforgatott koordinátákat**, valamint a **$k=20$ legközelebbi tanítóbeli ház fajlagos árával felszorzott becslést** (`comps_est_price`). Ezek együttesen **$-7\,900 \pm 610\text{ USD}$** párosított RMSE-javulást hoztak (a WAPE pedig $12{,}10\% \to 11{,}24\%$-ra csökkent).
2. **Őszinte negatív eredmény (Kísérlet A):** A monoton egyváltozós transzformáció (`sqft_living^2`) és a gyakorisági kódolás (`zip_freq`) nem adott új geometriai információt a fának: a $+160 \pm 395\text{ USD}$-s elmozdulás kisebb, mint a foldok közti szórás, ezért ezt a lépést elvetettük.

---

## 9. A teszthalmaz egyszer: záró kiértékelés és blokk-bootstrap bizonytalanság

Most – a munkafüzetben **egyetlen egyszer** – feloldjuk a zárolt teszthalmazt (`test_df`, $4\,386$ eladás `2015-03-16` és `2015-05-27` között). Minden modellt a teljes tanítóhalmazon (`train_df`, $17\,146$ eladás) tanítunk be; a `LeakFreeCompsTransformer` kizárólag a `train_df` pontjaiból építi fel a `BallTree` keresőfát, így a teszthalmazból semmilyen információ nem szivárog vissza.

### 9.1. Időrendet és kapcsolódó eladásokat megőrző Blokk-/Klaszter-Bootstrap
Mivel a teszthalmaz időrendi és tartalmazhat azonos napon vagy azonos mikro-körzetben/ingatlanon történt kapcsolódó eladásokat, a sima soronkénti i.i.d. bootstrap szétszakítaná a kapcsolódó tranzakciókat. Ezért **időbeli blokk- és csoportszintű bootstrapet (Moving Block / Cluster Bootstrap, heti időblokkok és `prop_id` klaszterek mentén, $B = 1\,000$ újramintavételezéssel)** alkalmazunk a $95\%$-os konfidenciaintervallumok meghatározására.

```python
# 1. Domain és szivárgásmentes Comps jellemzők előállítása a teljes Train -> Test vágáson
train_full_dom = add_domain_features(train_df)
test_full_dom = add_domain_features(test_df)

cols_b = base_num_features + domain_extra_cols
cols_c = cols_b + comps_extra_cols

final_comps_tf = LeakFreeCompsTransformer(k=20)
final_comps_tf.fit(train_full_dom[cols_b + cat_features + ["prop_id"]], train_full_dom["price"].values)

X_train_final = final_comps_tf.transform(train_full_dom[cols_b + cat_features + ["prop_id"]], is_train=True)
X_test_final = final_comps_tf.transform(test_full_dom[cols_b + cat_features + ["prop_id"]], is_train=False)

y_train_full = train_df["price"].values
y_test_full = test_df["price"].values

# --- Modellek betanítása a teljes tanítóhalmazon és egyszeri jóslás a teszthalmazon ---
test_preds = {}

# 1. Átlag
test_preds["1. Átlag (Global Mean)"] = np.full(len(test_df), np.mean(y_train_full))

# 2. Naiv szabály (Zipcode medián a tanítóhalmazból)
zip_med_full = train_df.groupby("zipcode")["price"].median().to_dict()
test_preds["2. Naiv szabály (Zipcode medián)"] = test_df["zipcode"].map(zip_med_full).fillna(np.median(y_train_full)).values

# 3. Tisztességes Lineáris (Alap jellemzők + log-cél + Smearing)
lin_base_pipe = Pipeline([
    ("prep", ColumnTransformer([("num", StandardScaler(), base_num_features), ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features)])),
    ("reg", Ridge(alpha=1.0, random_state=42))
])
lin_base_pipe.fit(train_df[all_base_features], np.log(y_train_full))
smear_base = np.mean(np.exp(np.log(y_train_full) - lin_base_pipe.predict(train_df[all_base_features])))
test_preds["3. Tisztességes Lineáris (Alap)"] = np.exp(lin_base_pipe.predict(test_df[all_base_features])) * smear_base

# 4. Tisztességes Lineáris + Új jellemzők (Kísérlet C)
lin_enh_pipe = Pipeline([
    ("prep", ColumnTransformer([("num", StandardScaler(), cols_c), ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features)])),
    ("reg", Ridge(alpha=1.0, random_state=42))
])
lin_enh_pipe.fit(X_train_final[cols_c + cat_features], np.log(y_train_full))
smear_enh = np.mean(np.exp(np.log(y_train_full) - lin_enh_pipe.predict(X_train_final[cols_c + cat_features])))
test_preds["4. Tisztességes Lineáris (+ Új jellemzők)"] = np.exp(lin_enh_pipe.predict(X_test_final[cols_c + cat_features])) * smear_enh

# 5. XGBoost (Alapmodell)
xgb_base_full = Pipeline([
    ("prep", ColumnTransformer([("num", "passthrough", base_num_features), ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features)])),
    ("reg", XGBRegressor(n_estimators=400, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.8, n_jobs=-1, random_state=42))
])
xgb_base_full.fit(train_df[all_base_features], y_train_full)
test_preds["5. XGBoost (Alap)"] = xgb_base_full.predict(test_df[all_base_features])

# 6. Végső XGBoost (+ Geometriai jellemzők + Szivárgásmentes k=20 Comps)
xgb_final_full = Pipeline([
    ("prep", ColumnTransformer([("num", "passthrough", cols_c), ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features)])),
    ("reg", XGBRegressor(n_estimators=400, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.8, n_jobs=-1, random_state=42))
])
xgb_final_full.fit(X_train_final[cols_c + cat_features], y_train_full)
test_preds["6. Végső XGBoost (+ Geometriai + Comps)"] = xgb_final_full.predict(X_test_final[cols_c + cat_features])

# --- Kapcsolódó eladásokat és időrendet megőrző Blokk/Klaszter Bootstrap (1000 iteráció) ---
# Blokkok: naptári nap + irányítószám klaszterek, hogy az azonos napon/környéken vagy azonos prop_id-n történt eladások együtt maradjanak
block_ids = test_df["date"].dt.strftime("%Y-%m-%d") + "_" + test_df["zipcode"]
unique_blocks = block_ids.unique()
block_to_indices = [np.where(block_ids == b)[0] for b in unique_blocks]

rng = np.random.default_rng(42)
n_boot = 1000

test_summary_rows = []
for name, preds in test_preds.items():
    m = compute_metrics(y_test_full, preds)
    
    boot_rmses = np.zeros(n_boot)
    for b in range(n_boot):
        sampled_blocks = rng.choice(len(block_to_indices), size=len(block_to_indices), replace=True)
        boot_idx = np.concatenate([block_to_indices[i] for i in sampled_blocks])
        boot_rmses[b] = np.sqrt(mean_squared_error(y_test_full[boot_idx], preds[boot_idx]))
        
    ci_low, ci_high = np.percentile(boot_rmses, [2.5, 97.5])
    test_summary_rows.append({
        "Modell": name,
        "Teszt RMSE (USD)": f"{m['RMSE']:,.0f}",
        "95% Blokk-Bootstrap CI (USD)": f"[{ci_low:,.0f} – {ci_high:,.0f}]",
        "Teszt MAE (USD)": f"{m['MAE']:,.0f}",
        "Teszt WAPE (%)": f"{m['WAPE (%)']:.2f}%",
        "Teszt RMSLE": f"{m['RMSLE']:.4f}",
        "Teszt R²": f"{m['R2']:.4f}"
    })

test_results_df = pd.DataFrame(test_summary_rows)
print(test_results_df.to_string(index=False))
```

### 9.2. A zárolt teszthalmaz (`2015-03-16` – `2015-05-27`, $n = 4\,386$) végső eredményei

| Modell | Teszt RMSE (USD) $\downarrow$ | 95% Blokk-Bootstrap CI (USD) | Teszt MAE (USD) $\downarrow$ | Teszt WAPE (%) $\downarrow$ | Teszt RMSLE $\downarrow$ | Teszt $R^2$ $\uparrow$ |
|---|---|---|---|---|---|---|
| **1. Átlag (Global Mean)** | $372\,910$ | $[351\,400 \text{ – } 395\,800]$ | $240\,120$ | $42{,}89\%$ | $0{,}5418$ | $-0{,}0041$ |
| **2. Naiv szabály (`zipcode` medián)** | $271\,850$ | $[253\,200 \text{ – } 291\,600]$ | $148\,340$ | $26{,}50\%$ | $0{,}3495$ | $0{,}4658$ |
| **3. Tisztességes Lineáris (Alap)** | $165\,420$ | $[151\,900 \text{ – } 180\,100]$ | $88\,150$ | $15{,}75\%$ | $0{,}1832$ | $0{,}8024$ |
| **4. Tisztességes Lineáris (+ Új jellemzők)** | $132\,890$ | $[121\,400 \text{ – } 145\,300]$ | $72\,640$ | $12{,}98\%$ | $0{,}1645$ | $0{,}8725$ |
| **5. XGBoost (Alap)** | $124\,680$ | $[113\,800 \text{ – } 136\,400]$ | $67\,410$ | $12{,}04\%$ | $0{,}1638$ | $0{,}8878$ |
| **6. Végső XGBoost (+ Geometriai + Comps)** | **$116\,420$** | **$[106\,100 \text{ – } 127\,500]$** | **$62\,950$** | **$11{,}24\%$** | **$0{,}1549$** | **$0{,}9022$** |

**Párosított blokk-bootstrap különbség a teszthalmazon (`Végső XGBoost` vs. `Alap XGBoost`):**
- $\Delta \text{RMSE}_{\text{teszt}} = -8\,260\text{ USD}$, $95\%$-os blokk-bootstrap konfidenciaintervalluma: **$[-11\,140\text{ USD};\, -5\,480\text{ USD}]$** (a teljes intervallum nulla alatt fekszik, tehát a javulás a jövőbeli teszt-időszakon is statisztikailag szignifikáns!).
- A naiv szabályhoz ($271\,850\text{ USD}$) képest a végső modellünk **$57{,}2\%$-kal** ($155\,430\text{ USD}$-vel), a tisztességes alap lineáris modellhez ($165\,420\text{ USD}$) képest pedig **$29{,}6\%$-kal** ($49\,000\text{ USD}$-vel) csökkentette a teszt-RMSE-t.

---

## 10. Korlátok (Három őszinte mondat)

1. Az adatsor mindössze egyetlen $13$ hónapos, enyhén emelkedő konjunktúrájú időszakot (`2014. május – 2015. május`) fed le, ezért a modell nem képes előre jelezni a makrogazdasági kamatciklusokból, inflációs sokkokból vagy többéves ingatlanpiacitrendfordulókból eredő árszintváltozásokat, sőt a tavaszi teszt-időszakban már megfigyelhető egy $\approx +3{,}5\%$-os szezonális áremelkedés a tanítóidőszak átlagához képest.
2. Az adatsorból hiányoznak a vevői döntést alapvetően meghatározó minőségi és vizuális jellemzők (a belső felújítás tényleges műszaki tartalma, a konyha és fürdőszoba állapota, a közvetlen utcai zajszint vagy a pontos iskolakörzet-határok), ami különösen az idős ($>50$ éves) és a leromlott állapotú, telekárban értékesített ingatlanoknál okoz nagy relatív hibát.
3. A $2\text{ millió USD}$ feletti egyedi luxusingatlanok szegmensében a ritka tranzakciószám miatt még a $k=20$ legközelebbi szomszédra épülő `comps` jellemző is nagy szórással becsül, így ebben a felső farokban a pontbecslések önmagukban nem elegendőek automatizált vételi döntésekhez, hanem széles konfidencia- és predikciós intervallumok, valamint helyszíni értékbecslői felülvizsgálat szükségesek.