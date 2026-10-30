window.LESSON_LABEL = "4. óra · Klasszifikáció";

// 90 perces óra: kb. 1 slide/perc alatt. Kérdés-költségvetés: összesen 6 kérdés (qa()), mindegyik válasza a KÖVETKEZŐ kattintásra jelenik meg.
// Minden más slide állítás. A hallgatók NEM látják az adatot az órán: ami kell, az a slide-on van (táblázat-képként).
// Minden szám a demo.ipynb-ből jön (30 000 soros réteges minta az OpenML 41162-es „kick” adatsorból, rögzített seedek, 3-fold CV,
// a teszthalmaz csak a végén), kivéve a build_assets.py ábráit (ár-sávok, nyers sorok, célérték-átlag példa), amelyek ugyanabból a mintából jönnek.
// A 2. órás gif-eket újrahasznosítjuk: a hallgatók már látták őket.
const L2 = "../02-gepi-tanulas/assets/";

// Állítás-slide. img: stack elrendezés (kép a szöveg alatt): cím ~20 karakter, a szöveg <= ~110 karakter, különben ráfut a képre.
function S(o) {
  return {
    type: "content", eyebrow: o.eyebrow, title: o.title,
    ...(o.img ? { visualLayout: "stack", visual: { kind: "image", src: "assets/" + o.img, alt: o.alt || o.title, caption: o.caption || "" } } : {}),
    ...(o.gif ? { visual: { kind: "image", src: L2 + o.gif, alt: o.alt || o.title, caption: o.caption || "" } } : {}),
    blocks: (o.blocks || []).map((b) => (typeof b === "string" ? { kind: "text", html: b } : b)),
  };
}
// A 6 kérdés egyike: a kérdés step 0, a válaszok step 1, 2, ...
function qa(o) {
  const answers = (Array.isArray(o.answer) ? o.answer : [o.answer]).map((x, i) =>
    typeof x === "string" ? { kind: "text", step: i + 1, html: x } : { ...x, step: i + 1 });
  return {
    type: "content", eyebrow: o.eyebrow, title: o.title,
    ...(o.img ? { visualLayout: "stack", visual: { kind: "image", src: "assets/" + o.img, alt: o.alt || o.title, caption: o.caption || "" } } : {}),
    blocks: [{ kind: "ask", html: o.ask }, ...answers],
  };
}
const T = (label, html) => ({ kind: "tension", label, html });
const LIST = (...items) => ({ kind: "list", items });

window.SLIDES = [
  { type: "title", eyebrow: "Data Science műhelykurzus", title: "Klasszifikáció", kicker: "A nyers adattól a hangolt modellig — és hogyan higgyünk el egy számot?", note: "Kárpáti András · 4. óra" },

  // ---------------- Recap (a 2. óra gif-jei) ----------------
  S({ eyebrow: "Recap · logisztikus regresszió", title: "Egy egyenes a két osztály között", gif: "gradient_descent_lr.gif", caption: "a 2. órán látott animáció",
      blocks: ["Súlyozott összeg, valószínűséggé alakítva. A határa <strong>egyenes</strong>: kanyart nem tud, azt kézzel kell beletenni."] }),
  S({ eyebrow: "Recap · döntési fa", title: "Kérdések sorozata", gif: "tree_depth.gif", caption: "a 2. órán látott animáció: növekvő max_depth",
      blocks: ["Korlát nélkül <strong>memorizál</strong>: a tanítón tökéletes, újon rossz. Ma számokkal is látjuk."] }),
  S({ eyebrow: "Recap · Random Forest", title: "Sok különböző fa átlaga", gif: "random_forest_ensemble.gif", caption: "a 2. órán látott animáció: egyre több fa",
      blocks: ["Az átlag kioltja a zajt: a <strong>variance</strong> csökken, a bias nem."] }),
  S({ eyebrow: "Recap · Gradient Boosting", title: "Kis fák, amelyek a hibákat javítják", gif: "gradient_boosting_rounds.gif", caption: "a 2. órán látott animáció: körről körre élesedik",
      blocks: ["A fák <strong>egymás után</strong> tanulnak, mindegyik az előző hibáját javítja. Az XGBoost ennek gyors, regularizált megvalósítása.",
               { kind: "plaque", year: "2016", html: "Chen és Guestrin publikálja az XGBoostot („XGBoost: A Scalable Tree Boosting System”)." }] }),

  // ---------------- EDA ----------------
  S({ eyebrow: "A feladat", title: "Használtautó-aukció: rossz vétel",
      blocks: ["Egy autókereskedő aukción vesz használt autót. Néhány vásárlás „kick”, azaz <strong>rossz vétel</strong>: az autóval komoly gond van (az adatsor leírása szerint pl. hamisított km-óra, műszaki hiba, okmányprobléma), ezért nem adható el.",
               "<strong>Pozitív osztály = rossz vétel.</strong> Egy kihagyott rossz vétel drága (szállítás, felesleges javítás, piaci veszteség); egy plusz ellenőrzés feltevésünk szerint olcsóbb. Ez dönti el később a küszöböt."] }),
  S({ eyebrow: "Az adat", title: "Kaggle: Don't Get Kicked!",
      blocks: [LIST("<strong>72 983</strong> vásárlás, <strong>33</strong> oszlop (Kaggle, Carvana; OpenML 41162, CC0). Az órán egy <strong>30 000 soros, réteges mintát</strong> használunk: 24 000 tanító + 6 000 teszt sor",
                    "<strong>12,3%</strong> rossz vétel: a „minden vétel jó” modell pontossága 87,7%",
                    "Oszlopok: az autó adatai (márka, modell, kor, km), a vételár, aukció, és <strong>piaci árbecslések</strong> (aukciós/kiskereskedelmi, átlagos/„tiszta” állapotú autóra) <strong>kétszer</strong>: a vásárláskor és ma",
                    "A becslés <strong>nem az új autó ára</strong>: a vásárláskori medián becslés 1 éves autóra 8 176, 9 évesre 2 629 USD (teljes adat; az adatsor nem definiálja, az értékekből következtetünk)")] }),
  S({ eyebrow: "EDA", title: "Kor szerint", img: "eda_kor.png", caption: "a 30 000 soros mintán; szaggatott vonal: átlag (12,3%)",
      blocks: ["Az autó korával nő a rossz vétel aránya: 1 évesnél <strong>3,8%</strong>, 9 évesnél <strong>29%</strong>."] }),
  S({ eyebrow: "EDA", title: "Vételár szerint", img: "eda_ar.png", caption: "fent: hány autó van a sávban; lent: közülük hány rossz vétel (100-nál kevesebb autós sávban nem rajzoltunk arányt)",
      blocks: ["3 000–4 000 USD között <strong>27%</strong> a rossz vétel, 7 000–9 000 USD között csak ~<strong>9%</strong>."] }),
  qa({ eyebrow: "EDA", title: "A hiányzó érték", img: "eda_hianyzas.png", caption: "WheelType: az autó keréktípusa; a „hiányzik” 1 299 autó",
      ask: "1 299 autónál nincs megadva a kerék típusa. Dobjuk el ezeket a sorokat?",
      answer: ["Nem! <strong>71%</strong>-uk rossz vétel (a többinél 8–11%): a hiányzás maga is jel."] }),
  S({ eyebrow: "EDA · tanulság", title: "A hiányzás jel vagy szivárgás?",
      blocks: [T("Kérdés, nem tény", "Nem tudjuk, <strong>miért</strong> hiányzik. Ha a vásárláskor is hiányzott, jó jelzés. Ha csak utólag derült ki, a rossz vétel <strong>következtében</strong>, akkor szivárgás: élesben nem látnánk előre."),
               "Ezt a vásárláskori adatrögzítés ismeretében kell eldönteni. A demóban jellemzőként használjuk."] }),

  // ---------------- Tisztítás ----------------
  S({ eyebrow: "Tisztítás", title: "Ilyen a nyers adat", img: "tbl_raw.png", caption: "hat valódi sor a mintából, a problémás cellák kiemelve",
      blocks: ["Unix-idő a dátum helyén, <strong>0 dollár</strong> becslés (vásárláskor és ma is), „MANUAL” és „Manual”, üres keréktípus, számnak látszó irányítószám."] }),
  S({ eyebrow: "Tisztítás", title: "Mit csinálunk velük?",
      blocks: [LIST("<strong>0 dollár ár</strong> → hiányzó érték (NaN): a mintában 348 vásárláskori és 209 mai becslésnél", "<strong>PurchDate</strong> (unix-idő) → hónap és a hét napja", "<strong>VNZIP1, BYRNO, WheelTypeID</strong>: számnak látszó kódok → kategória (nincs értelme átlagolni). A <code>WheelTypeID</code> a <code>WheelType</code> kódja, vagyis <strong>ugyanaz az információ</strong>", "<strong>Transmission</strong>: „Manual” → „MANUAL”", "<strong>Hiányzó értékek:</strong> lineáris modellnek medián + „hiányzott” jelző oszlop; fának a NaN marad. A hiányzást nem tüntetjük el nyomtalanul")] }),
  S({ eyebrow: "Kódolás", title: "One-hot kódolás", img: "tbl_onehot.png", caption: "valódi sorok a tanító halmazból; a hiányzó érték is kap egy oszlopot",
      blocks: ["One-hot: minden értékhez külön 0/1 oszlop; a „hiányzik” is kap egyet. Kevés érték esetén használjuk."] }),
  S({ eyebrow: "Kódolás", title: "Sok érték: célérték-átlag", img: "tbl_celatlag.png", caption: "csak a 24 000 tanító sorból számolva; 30-nál kevesebb autós érték: hiányzik",
      blocks: ["A <code>Model</code>nek 876 értéke van: one-hot-tal 876 oszlop. Helyette minden értékhez a <strong>csoport rossz-vétel-aránya</strong>."] }),
  S({ eyebrow: "Kódolás", title: "A célérték-átlag szabályai",
      blocks: [LIST("<strong>Csak a tanító adatból számoljuk</strong>: a teszt (és a validációs rész) célértékéből számolva szivárgás lenne, hiszen a jellemzőt a megoldásból állítanánk elő. Keresztvalidációnál minden foldon a tanító résznek megfelelően",
                    "<strong>Egyszerűen:</strong> a 30-nál kevesebb autós érték (és a tanítóban nem látott új érték) <strong>hiányzónak</strong> számít, nincs simítás. A 3 autós modell 100%-a úgysem megbízható. A 876 értékből 704 ilyen, de a tanító autók csak 17%-át fedik",
                    "A hiányzót a modell kezeli: a fa NaN-ként, a lineáris modell mediánnal és „hiányzott” jelzővel")] }),
  S({ eyebrow: "A split", title: "Előbb szétválasztunk",
      blocks: [LIST("<strong>24 000</strong> tanító és <strong>6 000</strong> teszt sor, rétegzetten (mindkettőben 12,3% rossz vétel)", "Ami az adatból <strong>tanul</strong> (imputer, scaler, encoder, célérték-átlag), azt egy <strong>pipeline</strong>-ba tesszük, és csak a tanító részen illesztjük, különben a teszt információja beszivárog (<strong>szivárgás</strong>)", "A teszthalmaz <strong>zárolva</strong> van a végéig: egyszer használjuk, hogy becsüljük a modell teljesítményét új autókon")] }),

  // ---------------- Keresztvalidáció és kiértékelés ----------------
  S({ eyebrow: "Keresztvalidáció", title: "Mi a keresztvalidáció?", img: "cv_abra.png", caption: "3-fold keresztvalidáció (CV); élesben 5–10 foldot szokás",
      blocks: ["A teszthalmaz zárolt, ezért a <strong>tanító adatot 3 részre vágjuk</strong>, és mindig egy másik rész a „vizsga”."] }),
  S({ eyebrow: "Keresztvalidáció", title: "Out-of-fold jóslat",
      blocks: ["A 3 kör végén minden autóra <strong>pontosan egy</strong> jóslat van, olyan modelltől, amely azt az autót <strong>sosem látta</strong>: ez az <strong>out-of-fold</strong> jóslat.",
               "Ezeken számoljuk a mutatókat, és ezeken nézzük a hibákat. A mutató <strong>átlag ± szórás</strong> a 3 körön: a szórás a bizonytalanság mértéke."] }),
  qa({ eyebrow: "Keresztvalidáció", title: "Időbeli adat", img: "idoszeru_split.png", caption: "kiterjedő ablak. A mi adatunk 2009–2010 vásárlásai, a demó gyorsaságból mégis véletlenül vág: a számok optimisták lehetnek (nem mértük)",
      ask: "Jó-e véletlenül vágni, ha az adatnak időbeli dimenziója van?",
      answer: ["Nem: a jövőt a múltból kell jósolni. A validáció mindig a tanítás <strong>után</strong> jön."] }),
  qa({ eyebrow: "Értékelés", title: "A pontosság csapdája",
      ask: "A „minden vétel jó” modell 87,7%-ot ér el. Jó modell?",
      answer: [T("Nem", "Egyetlen rossz vételt sem talál meg (<strong>recall = 0</strong>), mégis szép a pontossága: a többségi osztály uralja."),
               "Ha a rossz vétel csak 1% lenne, ugyanez a modell <strong>99,1%</strong>-os lenne (szintetikus példa)."] }),
  S({ eyebrow: "Értékelés", title: "Kiegyensúlyozott pontosság",
      blocks: ["<strong>Kiegyensúlyozott pontosság = (a rossz vételek recallja + a jó vételek recallja) / 2.</strong>",
               "A „minden vétel jó”: (0 + 1) / 2 = <strong>0,50</strong>. A logisztikus regresszió 0,5-ös küszöbön: (0,25 + 0,99) / 2 = <strong>0,62</strong>, miközben a pontossága 0,90.",
               T("Szabály a kurzuson", "Ritka pozitívnál <strong>kiegyensúlyozott pontosságot, PR-AUC-t és konfúziós mátrixot</strong> jelentünk, nyers pontosságot nem.")] }),
  S({ eyebrow: "Értékelés", title: "Konfúziós mátrix", img: "cm_lr.png", caption: "logisztikus regresszió, 0,5-ös küszöb, out-of-fold jóslatok a tanító halmazon",
      blocks: ["Négy rossz vételből egyet fogunk meg: <strong>740</strong> találat, <strong>2 212</strong> kihagyott, <strong>265</strong> fölösleges riasztás."] }),
  S({ eyebrow: "Értékelés", title: "Precision és recall",
      blocks: ["<strong>Precision = TP / (TP + FP)</strong>: a megjelöltek közül hány a valódi találat. Itt 740 / 1 005 = <strong>0,74</strong>.",
               "<strong>Recall = TP / (TP + FN)</strong>: a valódi rossz vételek közül hányat találtunk meg. Itt 740 / 2 952 = <strong>0,25</strong>.",
               "A két mutató a <strong>küszöb</strong> állításával cserélhető egymásra."] }),
  S({ eyebrow: "Értékelés", title: "A küszöb nem 0,5", img: "tbl_kuszob_lr.png", caption: "logisztikus regresszió, out-of-fold, tanító halmaz",
      blocks: ["A küszöböt lejjebb víve a recall nő (<strong>25% → 69%</strong>), a precision esik (<strong>74% → 23%</strong>)."] }),
  S({ eyebrow: "Értékelés", title: "ROC és PR görbe", img: "metrics_roc_pr.png", caption: "ugyanazok a jóslatok; a PR alapvonala a pozitívok aránya (0,12)",
      blocks: ["ROC-AUC <strong>0,76</strong>, PR-AUC <strong>0,45</strong>. Ritka pozitívnál a PR-AUC a megbízhatóbb."] }),
  S({ eyebrow: "Értékelés", title: "Mit jelent az AUC és az AP?",
      blocks: ["<strong>ROC-AUC:</strong> annak az esélye, hogy egy véletlen rossz vétel magasabb pontot kap, mint egy véletlen jó vétel. 0,5 = találgatás. Ritka pozitívnál hízelgő.",
               "<strong>PR-AUC</strong> (average precision): a precision átlaga az összes recall-szinten. Alapvonala a pozitívok aránya (itt 0,12).",
               { kind: "plaque", year: "II. világháború", html: "A ROC-görbe a radarjel-felismerés (signal detection) munkájából ered: a kezelő döntése, hogy egy folt ellenséges gép-e, ugyanilyen küszöb-kérdés." }] }),
  S({ eyebrow: "Értékelés", title: "A legkockázatosabb 5%",
      blocks: ["Ha csak a modell szerint legkockázatosabb <strong>5%</strong>-ot (1 200 autót) vizsgáljuk meg, ezek <strong>68%</strong>-a valóban rossz vétel: az átlag (12%) <strong>5,5-szöröse</strong>.",
               LIST("legkockázatosabb 1% (240 autó): 88% találat", "legkockázatosabb 10% (2 400 autó): 48%", "legkockázatosabb 20% (4 800 autó): 32%")] }),
  S({ eyebrow: "Értékelés", title: "Hogyan hasonlítsunk modelleket?",
      blocks: [LIST("A mérőszámot <strong>előre</strong> választjuk, nem utólag", "<strong>Ugyanazok a foldok</strong> minden modellnek; mindig legyen dummy és egyszerű alapmodell", "<strong>Átlag ± szórás</strong>: a szórásnál kisebb különbség <strong>döntetlen</strong>", "Modellt vagy küszöböt <strong>soha</strong> nem a teszthalmazon választunk")] }),

  // ---------------- Modell-létra ----------------
  qa({ eyebrow: "Modell-létra", title: "Melyik nyert?", img: "tbl_letra.png", caption: "hat versenyző, ugyanazok a 3 fold; 3-fold CV a tanító halmazon, átlag ± szórás",
      ask: "Tipp: melyik modell kapta a legjobb PR-AUC-ot?",
      answer: ["Az <strong>XGBoost</strong>: 0,484, a logisztikus regresszió 0,449 (páros különbség +0,032 ± 0,008)."] }),
  S({ eyebrow: "Modell-létra", title: "Mit olvasunk ki?",
      blocks: [LIST("A <strong>korlát nélküli fa</strong> memorizál: PR-AUC 0,19, alig jobb a véletlennél (0,12)", "A <strong>logisztikus regresszió</strong> erős alap (0,45); a Random Forest 0,46, az XGBoost 0,48: <strong>mérsékelt</strong> nyertes", "A lineáris modell one-hot bemenetet kap (643 oszlop), a fák kevesebbet (33 oszlop)"),
               T("Tanulság", "Nem egy nagyobb modell a következő lépés, hanem a hibák megértése.")] }),
  S({ eyebrow: "Modell-létra", title: "Mire figyel az XGBoost?", img: "xgb_fontossag.png", caption: "a tíz legfontosabb oszlop (gain alapú fontosság). A demóban a WheelType és a WheelTypeID is benne maradt; élesben az egyiket eldobnánk",
      blocks: ["A <code>WheelType</code> (név) és a <code>WheelTypeID</code> (kód) <strong>ugyanaz az információ</strong>, ezért megoszlik a fontosságuk; utána a kor és az aukció."] }),

  // ---------------- Visszacsatolási kör ----------------
  S({ eyebrow: "Visszacsatolás", title: "Hibák → hipotézis → újramérés",
      blocks: ["A hibákat a tanító halmaz <strong>out-of-fold</strong> jóslatain nézzük, nem a teszthalmazon.",
               LIST("megnézzük a hibákat, szegmensekre bontjuk őket", "megfogalmazunk <strong>egy</strong> hipotézist", "változtatunk (jellemző, minta vagy működési pont)", "<strong>ugyanazokon a foldokon</strong> újra mérünk"),
               T("Költség", "Minden iteráció elhasznál egy kicsit a validációs „költségvetésből”. Ezért állunk meg egy körnél, és a teszthalmaz érintetlen marad.")] }),
  S({ eyebrow: "Visszacsatolás", title: "Az XGBoost hibái", img: "cm_xgb.png", caption: "XGBoost, 0,5-ös küszöb, out-of-fold jóslatok a tanító halmazon",
      blocks: ["Recall <strong>25%</strong> (749 / 2 952), precision <strong>83%</strong>: négy rossz vételből egyet talál meg."] }),
  S({ eyebrow: "Visszacsatolás", title: "Nézzünk tévedéseket", img: "tbl_tevedesek.png", caption: "felül: a legbiztosabban kihagyott rossz vételek; alul: a legbiztosabb álriasztások",
      blocks: ["A kihagyott rossz vételek friss, átlagos autók, 0–1% jósolt eséllyel: a nyers oszlopok nem árulják el, miért rosszak."] }),
  S({ eyebrow: "Visszacsatolás", title: "Hipotézis: az értékvesztés", img: "loop_arvaltozas.png", caption: "a mai és a vásárláskori becsült aukciós átlagár hányadosa szerint tíz sávra bontva (az ábrán „vételkori”: ugyanaz); a sávok létszáma nem egyenlő, mert sok autónál pontosan 1,00 a hányados",
      blocks: ["Egy rossz vétel értékvesztés. Ahol az ár nem mozdult (≈ 1,00), a modell <strong>alulbecsül</strong>: 0,17 a valódi 0,19 helyett."] }),
  S({ eyebrow: "Visszacsatolás", title: "Fordított U alak",
      blocks: ["A rossz vétel aránya az árváltozás szerint <strong>fordított U</strong>: ~20% ott, ahol az ár alig mozdult (1,00 körül), és ~10% mindkét szélen. Egy egyenes csak lejtő lehet, ezt nem követi.",
               "Egy fa követni tudná, de csak ha az <strong>arányt egyetlen oszlopban</strong> megkapja: a fa egy oszlopra tesz fel kérdést, két oszlopot nem oszt el egymással.",
               T("Őszintén", "Azt, <strong>miért</strong> magas a kockázat ott, ahol az ár nem mozdult, nem tudjuk (lehet, hogy az árbecslés nem frissült). A mintázat attól még használható.")] }),
  S({ eyebrow: "Feature engineering", title: "Amit a fa nem számol ki",
      blocks: ["A fa egy oszlopra tesz fel kérdést: két oszlop <strong>hányadosát vagy különbségét</strong> nekünk kell kiszámolni. Ez a <strong>feature engineering</strong>.",
               LIST("<strong>árarány</strong>: mai becsült ár / vásárláskori becsült ár, négy féle árra (aukciós/kiskereskedelmi, átlagos/tiszta)", "<strong>árkülönbség</strong>: mai − vásárláskori aukciós átlagbecslés", "fizetett ár / mai ár; kiskereskedelmi / aukciós ár; tiszta / átlagos ár")] }),
  qa({ eyebrow: "Feature engineering", title: "Javít az új jellemző?", img: "tbl_jellemzok.png", caption: "3-fold × 2 ismételt CV; a különbség páros: ugyanazok a foldok",
      ask: "Javítják az új jellemzők az XGBoostot és a logisztikus regressziót is?",
      answer: ["Csak az XGBoostot: <strong>+0,018 ± 0,006</strong> (páros); a logisztikus regresszió +0,001, azaz semmi."] }),
  S({ eyebrow: "Feature engineering", title: "Miért csak a fának segít?",
      blocks: ["A hatás fordított U alakú, nem monoton: az egyenes csak lejtő lehet. A fa <strong>hajlik</strong>, ha megkapja a jelet.",
               T("Tanulság", "A feature engineering a modell és az adat <strong>párosításáról</strong> szól: a fának az arányt kell kiszámolnunk, a lineáris modellnek a kanyart (pl. sávokat).")] }),
  S({ eyebrow: "Visszacsatolás", title: "A küszöb üzleti döntés", img: "loop_kuszob_gorbek.png", caption: "XGBoost, out-of-fold, tanító halmaz",
      blocks: ["0,56-nál a pontosság a legjobb (recall 0,25); 0,12-nél a recall 0,62, de a pontosság 0,75. A választás <strong>üzleti döntés</strong>."] }),
  S({ eyebrow: "Visszacsatolás", title: "A javítás együtt", img: "tbl_javitas.png", caption: "XGBoost, out-of-fold, tanító halmaz",
      blocks: ["Az új jellemzők és a 0,12-es küszöb együtt: recall <strong>0,62</strong>, kiegyensúlyozott pontosság <strong>0,70</strong> (a pontosság 0,75)."] }),
  S({ eyebrow: "Visszacsatolás", title: "Mit tanultunk a körből?",
      blocks: [LIST("A hibaelemzés <strong>konkrét hipotézist</strong> adott: az árváltozás", "A <strong>feature engineering</strong> a fának segített (+0,018 PR-AUC), a lineáris modellnek nem", "A <strong>működési pont</strong> (küszöb) üzleti döntés: a recall 0,25-ről 0,62-re nő, de a pontosság 0,90-ről 0,75-re esik", "A kört egyszer járjuk be: minden iteráció a validációs költségvetésből vesz el")] }),

  // ---------------- Hangolás ----------------
  S({ eyebrow: "Hangolás", title: "Hiperparaméter és véletlen keresés",
      blocks: ["<strong>Paramétert</strong> a modell tanul (pl. a fa kérdései). <strong>Hiperparamétert</strong> mi állítunk be tanulás előtt: mélység, fák száma, learning rate.",
               "<strong>Véletlen keresés:</strong> ha csak néhány hiperparaméter számít, a véletlen minták több különböző értéket próbálnak ki, mint egy rács. A demóban: 8 jelölt az XGBoostra, 3 a forestre, 3-fold CV, a célfüggvény a PR-AUC."] }),
  qa({ eyebrow: "Hangolás", title: "Előtte és utána", img: "tuning_elotte_utana.png", caption: "PR-AUC új CV-foldokon (átlag ± szórás), amelyeket a keresés sosem látott",
      ask: "Segített a hangolás?",
      answer: ["Nem: XGBoost 0,499 → 0,493, forest 0,473 → 0,468: a zajon belül. Az alapbeállítás is jó."] }),
  S({ eyebrow: "Hangolás", title: "Ha nem javul, az egyszerűbbet tartjuk",
      blocks: ["A keresés „legjobb pontszáma” 8 próba <strong>maximuma</strong>, elvileg optimista: 0,495 a keresés szerint, 0,493 új foldokon.",
               T("Őszinte lépés", "Ha a hangolt modell nem jobb, <strong>az egyszerűbbet (az alapot) tartjuk meg</strong>. A hangolás hipotézis, nem garancia. A demó kis kereséssel dolgozik; élesben több jelölt és több fold kell.")] }),

  // ---------------- Záró teszt ----------------
  S({ eyebrow: "Záró teszt", title: "Előre rögzített szabály",
      blocks: [LIST("Jelöltek: logisztikus regresszió (CV: 0,450), XGBoost alap (0,499), XGBoost hangolt (0,493). Nyer a <strong>legjobb CV PR-AUC</strong>: az alap XGBoost", "Küszöb: üzleti költség híján a demóban a kiegyensúlyozott pontosságot maximalizáló érték a végső modell out-of-fold jóslataiból → <strong>0,12</strong>", "Illesztés az egész tanító halmazon, aztán a teszthalmaz <strong>egyszer</strong>")] }),
  S({ eyebrow: "Záró teszt", title: "A teszthalmazon", img: "tbl_vegso.png", caption: "6 000 autó, ebből 738 rossz vétel",
      blocks: ["Küszöb 0,5 → 0,12: recall 0,22 → <strong>0,62</strong>, kiegyens. pontosság 0,61 → <strong>0,69</strong>, de precision 0,87 → 0,27."] }),
  S({ eyebrow: "Záró teszt", title: "A teszt mátrixa", img: "cm_vegso.png", caption: "alap XGBoost, küszöb 0,12, a teszthalmazon",
      blocks: ["A 738 rossz vételből <strong>454</strong>-et fogunk meg, <strong>1 212</strong> fölösleges riasztással; 284 kimarad."] }),
  S({ eyebrow: "Záró teszt", title: "Megéri?",
      blocks: ["1 212 fölösleges riasztás egy 454 megfogott rossz vételért: attól függ, <strong>mennyibe kerül egy plusz ellenőrzés</strong>, és mennyit ér egy elkerült kick. Ezt az üzlet tudja, nem a modell.",
               "A modell dolga a választási lehetőségeket adni (a PR-görbe pontjait); a küszöböt az üzleti költség dönti el."] }),
  S({ eyebrow: "Összefoglaló", title: "Ellenőrzőlista",
      blocks: [LIST("Először szétválasztunk; ami tanul, az pipeline-ban él (a célérték-átlag is)", "Időbeli adatnál a múltból jósolunk a jövőre", "Alapmodell és dummy mindig; ugyanazok a foldok minden modellnek", "Mutatók előre: kiegyensúlyozott pontosság, PR-AUC, konfúziós mátrix, a legkockázatosabb X%", "A hiányzás lehet jel, de lehet szivárgás is", "Feature engineering: a modellnek azt számoljuk ki, amit magától nem tud", "Ha a hangolt modell nem jobb, az egyszerűbbet tartjuk meg; a teszthalmaz egyszer")] }),
  S({ eyebrow: "Házi", title: "Építs saját klasszifikátort",
      blocks: ["Válassz <strong>egy</strong> adatsort (lehetőleg mindenki mást), és építs rá bináris klasszifikátort egyetlen notebookban: split előbb, dummy és alapmodell, legalább három modell, a mai mutatók, <strong>egy dokumentált visszacsatolási kör új jellemzővel</strong>, a teszthalmaz egyszer.",
               "Pontozás: az <strong>indoklás</strong> számít, nem a pontszám; a sikertelen próbálkozás is érték, ha őszintén leírod. Részletek, adatsorok: <code>homework.md</code>."] }),
];
