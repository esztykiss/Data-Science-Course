# 1. Modellválasztás és alapvonal

## Cél és adatok

A feladat a Titanic utasainak túlélését (`Survived`) becsüli a Kaggle-féle *Titanic - Machine Learning from Disaster* tanító adatsoron. Az adathalmaz 891 utast és 12 eredeti oszlopot tartalmaz; a célváltozó túlélési aránya 0,384. Bemenetként a `Pclass`, `Sex`, `Age`, `SibSp`, `Parch`, `Fare` és `Embarked` mezőket használtuk. Az azonosító és szöveges mezőket (`PassengerId`, `Name`, `Ticket`), valamint a sok hiányzó értékű `Cabin` mezőt kihagytuk. A hiányzó `Age` értékeket mediánnal, az `Embarked` értékeket módusszal pótoltuk, a kategóriákat one-hot kódoltuk; így 8 prediktor keletkezett.

## Kísérleti felosztás

A felosztás stratifikált, 75% tanuló és 25% teszt, `random_state=7`: 668 tanuló- és 223 tesztminta. A skálázót kizárólag a tanuló adaton illesztettük, majd ugyanazzal transzformáltuk a tesztadatot. Minden alábbi baseline és hangolási mérés ezt a felosztást használja.

A két kiválasztott modell a **Random Forest** és a **Gradient Boosting**. Mindkettő döntési fákból épít ensemble-t, de eltérően: a Random Forest párhuzamos fákkal csökkenti a varianciát, a Gradient Boosting pedig egymás után javítja az előző fák hibáit. Ez a páros lehetővé teszi a fa-komplexitás és az ensemble paramétereinek összehasonlítását.

## Hat modell alapértékekkel

| Modell | Tesztpontosság |
|---|---:|
| Gradient Boosting | 0,843 |
| SVM | 0,825 |
| Döntési fa | 0,821 |
| Random Forest | 0,821 |
| Neurális háló | 0,798 |
| Logisztikus regresszió | 0,771 |

Az eredeti hatmodell-összehasonlítás legjobb alapértéke a Gradient Boosting 0,843-as tesztpontossága volt. A hangolás célja ennek felülmúlása volt ugyanazon spliten.
A neurális háló 500 iteráció után sem konvergált (a futás `ConvergenceWarning` figyelmeztetést adott), ezért a 0,798-as eredményét ezzel a korláttal együtt kell értelmezni.

## Reprodukálhatósági megjegyzés

A notebook szerkesztőben megnyitott CSV-t a futtatókörnyezet nem tudta közvetlenül elérni. Az újrafuttatás a kanonikus Kaggle Titanic train CSV nyilvános másolatával történt; annak sémája, első sorai és utolsó utasai megegyeznek a megnyitott fájléval, a mért fájl 891 sort tartalmazott. A notebook első adatbetöltő cellája a `Titanic-Dataset.csv` fájlt a kernel munkakönyvtárából várja; beadás előtt a notebookot a helyi fájl elérhetővé tétele mellett érdemes újrafuttatni.