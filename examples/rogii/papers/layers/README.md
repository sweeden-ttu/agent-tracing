# Leaderboard ensemble layers — reference papers

Open-access PDFs for each architectural layer in the top Rogii Kaggle kernels (see [`../../docs/LEADERBOARD_FIELD_ANALYSIS.md`](../../docs/LEADERBOARD_FIELD_ANALYSIS.md)).

**Download script:** `python examples/rogii/scripts/download_layer_papers.py`

| Layer | Primary paper | PDF in repo | Status |
|-------|---------------|-------------|--------|
| **01 Alignment** | Sakoe & Chiba (1978) DTW | [`01_alignment/sakoe1978_dtw.pdf`](01_alignment/sakoe1978_dtw.pdf) | Downloaded |
| | Lowerre (1976) HARPY beam search | — | [CMU tech report](https://www.ri.cmu.edu/pub_files/1976/1/Lowerre_1976_1_The_HARPY_Speech_Recognition_System.pdf) (link only) |
| **02 Physics** | Gordon et al. (1993) particle filter | — | [DOI](https://doi.org/10.1049/ip-f-2.1993.0015) (paywall; use SMC tutorial below) |
| | Doucet & Johansen (2011) SMC tutorial | [`02_physics/doucet2011_tutorial_smc.pdf`](02_physics/doucet2011_tutorial_smc.pdf) | Downloaded |
| **02 Physics (leakage)** | Kaufman et al. (2012) leakage | [`../ps_point_leakage_aware/kaufman2012_leakage.pdf`](../ps_point_leakage_aware/kaufman2012_leakage.pdf) | Downloaded |
| **03 Spatial** | Cover & Hart (1967) k-NN | — | [DOI](https://doi.org/10.1109/TIT.1967.1053964) |
| | Shepard (1968) spatial interpolation | — | [DOI](https://doi.org/10.1145/321267.321298) |
| **04 Features** | Lewis (1995) fast NCC | — | [CMU mirror](http://www.cs.cmu.edu/~dst/COWI/Papers/lewis95.pdf) (often offline) |
| | Wolpert (1992) stacked generalization | — | [Citeseer](http://www.mlresearch.org/reproducing-model-ensembles/wolpert92.pdf) |
| **05 Models** | Ke et al. (2017) LightGBM | [`05_models/ke2017_lightgbm.pdf`](05_models/ke2017_lightgbm.pdf) | Downloaded |
| | Prokhorenkova et al. (2018) CatBoost | [`05_models/prokhorenkova2018_catboost.pdf`](05_models/prokhorenkova2018_catboost.pdf) | Downloaded |
| | Chen & Guestrin (2016) XGBoost | [`05_models/chen2016_xgboost.pdf`](05_models/chen2016_xgboost.pdf) | Downloaded |
| **06 Sequence** | Bai et al. (2018) TCN | [`06_sequence/bai2018_tcn.pdf`](06_sequence/bai2018_tcn.pdf) | Downloaded |
| | Qu et al. (2025) TabICL | [`06_sequence/qu2025_tabicl.pdf`](06_sequence/qu2025_tabicl.pdf) | Downloaded |
| **07 Blend** | Hoerl & Kennard (1970) ridge | — | [DOI](https://doi.org/10.2307/1267351) |
| | Breiman (1996) stacked regressions | — | [Berkeley](https://www.stat.berkeley.edu/~breiman/stacked.pdf) |
| | Hastie et al. (2016) regularization / stacking context | [`07_blend/tibshirani1996_ridge_lasso_survey.pdf`](07_blend/tibshirani1996_ridge_lasso_survey.pdf) | Downloaded (arXiv book; L1/L2 blend theory) |
| **08 Post** | Savitzky & Golay (1964) smoothing | — | [DOI](https://doi.org/10.1021/ac60214a047) |

Variant-primary papers (trace branches) remain under [`../`](../) — see [`../manifest.json`](../manifest.json) and [`../../BASE_PAPERS.md`](../../BASE_PAPERS.md).

Machine-readable index: [`manifest.json`](manifest.json)
