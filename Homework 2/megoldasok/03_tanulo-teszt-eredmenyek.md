# 3. Tanuló- és teszteredmények

A pontosságot minden konfiguráción külön számoltuk a tanuló- és a teszthalmazon. A rés a tanuló pontosságából kivont tesztpontosság; a nagy pozitív érték a tanuló adatra való túlillesztés jele lehet.

| Modellbeállítás | Tanuló pontosság | Tesztpontosság | Tanuló–teszt rés |
|---|---:|---:|---:|
| RF baseline (`depth=6`, 200 fa) | 0,865 | 0,821 | 0,045 |
| RF regularizált (`depth=4`, `leaf=3`, 300 fa) | 0,840 | 0,816 | 0,024 |
| RF mély (`depth=None`, 300 fa) | 0,987 | 0,794 | **0,193** |
| GB baseline (`lr=0,10`, `depth=3`, 100 fa) | 0,909 | 0,843 | 0,066 |
| GB visszafogott (`lr=0,05`, `depth=2`, 200 fa) | 0,859 | 0,821 | 0,039 |
| GB optimalizált (`lr=0,08`, `depth=3`, 150 fa) | 0,915 | **0,857** | 0,058 |
| GB kisebb ráta (`lr=0,05`, `depth=3`, 250 fa) | 0,915 | 0,852 | 0,063 |
| GB mélyebb (`lr=0,10`, `depth=4`, 200 fa) | 0,979 | 0,825 | **0,154** |

A legjobb teszteredményt a Gradient Boosting `learning_rate=0.08`, `max_depth=3`, `n_estimators=150` beállítása adta: 0,857. Ez 0,014-del, vagyis 1,4 százalékponttal jobb az alap Gradient Boosting 0,843-as eredményénél. A legnagyobb train/test rés a korlátlan mélységű Random Forestnél jelentkezett (0,193), ezt a mélyebb Gradient Boosting követte (0,154); mindkettőnél a tanuló pontosság jóval magasabb, mint a tesztpontosság.

A számok a kiválasztott, egyetlen stratifikált felosztásra érvényesek. A teszteredmény alapján végzett paraméterválasztás optimista becslést adhat, ezért végső modellválasztás előtt keresztvalidáció ajánlott.