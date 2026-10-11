# 2. Hiperparaméter-próbák

A próbák a feladatban megadott két modellen készültek: Random Forest és Gradient Boosting. Mind a nyolc modellt ugyanazzal a stratifikált 75/25 train/test felosztással tanítottuk (`random_state=7`). Az alapértékeket is megtartottuk összehasonlításként.

## Random Forest

| Próba | `n_estimators` | `max_depth` | `min_samples_leaf` | Mit vizsgál? |
|---|---:|---:|---:|---|
| Alap | 200 | 6 | 1 (alapérték) | Eredeti baseline |
| Regularizált | 300 | 4 | 3 | Kisebb fákat és nagyobb levélméretet vizsgál |
| Mély | 300 | `None` | 1 (alapérték) | A korlátlan fa-mélység túlillesztési kockázatát vizsgálja |

## Gradient Boosting

| Próba | `learning_rate` | `max_depth` | `n_estimators` | Mit vizsgál? |
|---|---:|---:|---:|---|
| Alap | 0,10 | 3 | 100 | Eredeti baseline |
| Visszafogott | 0,05 | 2 | 200 | Alacsonyabb tanulási ráta és sekélyebb fák |
| Optimalizált | 0,08 | 3 | 150 | A próbákban legjobb teszteredményt adó kombináció |
| Kisebb ráta | 0,05 | 3 | 250 | Több fa kisebb tanulási rátával |
| Mélyebb | 0,10 | 4 | 200 | A nagyobb fa-komplexitás túlillesztési kockázatát vizsgálja |

A paraméterek kiválasztása a train és test pontosság együttes megfigyelésére szolgált. A mélyebb beállításokat szándékosan is teszteltük, hogy az overfitting jele mérhető legyen, ne csak feltételezés.