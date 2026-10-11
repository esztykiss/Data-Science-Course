# Titanic túlélés-előrejelzés: feladat, cél és munkamenet

## A feladat

A `demo.ipynb` 9. szekciója hat osztályozó modellt hasonlít össze alapértelmezett hiperparaméterekkel a Titanic adatsoron. A feladat az alaperedmények javítása két kiválasztott modellen úgy, hogy mindkettőnél legalább három hiperparaméter-beállítást próbálunk ki. Minden beállításhoz külön tanuló- és tesztpontosságot kell mérni, majd az eredmények alapján megindokolni a legjobb választást és azonosítani az overfittinget.

## A cél

A Kaggle *Titanic - Machine Learning from Disaster* adatsor utasairól megjósolni a `Survived` célváltozót. A cél nem pusztán a tesztpontosság növelése, hanem olyan beállítás keresése, amely a teszthalmazon jól teljesít, és közben nem mutat túl nagy tanuló–teszt szakadékot.

## Az adatok és előfeldolgozás

Az adatsor 891 utast tartalmaz, 12 eredeti oszloppal. A használt jellemzők: `Pclass`, `Sex`, `Age`, `SibSp`, `Parch`, `Fare`, `Embarked`; a `Survived` az előrejelzendő címke. A `PassengerId`, `Name`, `Ticket` azonosító/szöveges mezőket és a sok hiányzó értéket tartalmazó `Cabin` oszlopot nem használtuk. A hiányzó életkort a mediánnal, a hiányzó beszállási kikötőt a módusszal pótoltuk; a kategorikus mezőket one-hot kódoltuk. A végső bemeneti mátrix 8 jellemzőből áll.

A felosztás 75% tanuló és 25% teszt, stratifikálva a túlélési címke szerint, `random_state=7` rögzített véletlenmaggal. Ez 668 tanuló- és 223 tesztmintát jelent. A `StandardScaler` csak a tanuló adaton illeszkedett, majd ugyanazt a transzformációt alkalmaztuk a teszthalmazra.

## Munkamenet lépésről lépésre

1. **Alapvonal rögzítése.** Újramértük a notebook hat alapmodelljének tesztpontosságát. A Gradient Boosting lett a legjobb alapmodell 0,843 tesztpontossággal; Random Forest 0,821-et ért el.
2. **Két modell kiválasztása.** A Random Forestet és a Gradient Boostinget vizsgáltuk részletesen, mert mindkettő faalapú ensemble, de eltérő tanítási stratégiát alkalmaz.
3. **Hiperparaméterek próbája.** Három Random Forest- és öt Gradient Boosting-konfigurációt mértünk, a baseline-okat is beleértve. A Random Forestnél a fa mélységét, az erdő méretét és a minimális levélméretet; a Gradient Boostingnál a tanulási rátát, a fa mélységét és a fák számát változtattuk.
4. **Train/test összehasonlítás.** Minden konfigurációra kiszámoltuk a tanuló- és tesztpontosságot. A különbséget `tanuló pontosság - tesztpontosság` képlettel számítottuk; a nagy rés túlillesztésre utal.
5. **Következtetés.** A legjobb mért tesztpontosság 0,857 lett a Gradient Boosting `learning_rate=0.08`, `max_depth=3`, `n_estimators=150` beállításával. Ez 0,014-del meghaladta az eredeti Gradient Boosting 0,843-as eredményét. A legnagyobb overfitting-rés a korlátlan mélységű Random Forestnél volt (0,193), majd a mélyebb Gradient Boostingnál (0,154).

## Eredmények röviden

| Modellbeállítás | Tanuló pontosság | Tesztpontosság | Rés |
|---|---:|---:|---:|
| Random Forest alap | 0,865 | 0,821 | 0,045 |
| Random Forest regularizált (`depth=4`, `leaf=3`) | 0,840 | 0,816 | 0,024 |
| Random Forest korlátlan mélység | 0,987 | 0,794 | 0,193 |
| Gradient Boosting alap | 0,909 | 0,843 | 0,066 |
| Gradient Boosting visszafogott (`lr=0.05`, `depth=2`) | 0,859 | 0,821 | 0,039 |
| Gradient Boosting legjobb (`lr=0.08`, `depth=3`, 150 fa) | 0,915 | 0,857 | 0,058 |
| Gradient Boosting kisebb ráta (`lr=0.05`, `depth=3`, 250 fa) | 0,915 | 0,852 | 0,063 |
| Gradient Boosting mélyebb (`lr=0.1`, `depth=4`, 200 fa) | 0,979 | 0,825 | 0,154 |

A regularizált Random Forestnek volt a legkisebb tanuló–teszt rése, de alacsonyabb tesztpontossággal. A legjobb összteljesítményt ezért a `0.857` tesztpontosságú, közepes komplexitású Gradient Boosting adta. Az eredmények egyetlen rögzített train/test felosztásra vonatkoznak; a végleges modellválasztást keresztvalidációval lenne érdemes megerősíteni.

## Adatfájl és reprodukálhatóság

A mappában található `Titanic-Dataset.csv` a kanonikus Kaggle Titanic tanító adatsor nyilvános másolata. A VS Code-ban megnyitott eredeti CSV-t a Python kernel fájlrendszere nem érte el közvetlenül; ezért a méréseket ezzel a reprodukálható példánnyal futtattuk. A példány 891 sort, ugyanazt az oszlopfejlécet, valamint a megnyitott CSV-vel egyező első és utolsó utasrekordokat tartalmaz. A notebook újrafuttatásához a CSV-t a kernel munkakönyvtárába kell tenni, vagy a beolvasási útvonalat erre a fájlra kell állítani.
