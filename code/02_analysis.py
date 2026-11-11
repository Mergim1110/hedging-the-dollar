"""
Step 2. Hedged versus unhedged US equity returns for a Swiss franc investor.
Usage: python 02_analysis.py <data_folder> <output_folder>
All figures quoted in the note are produced here and written to results.json.
"""
import sys, json, math
import numpy as np, pandas as pd

DATA, OUT = sys.argv[1], sys.argv[2]

# ---------- inputs ----------
sp = pd.read_csv(f"{DATA}/sp500tr_monthly.csv", dtype={"month": str}).set_index("month")["sp500tr_close_usd"]
ch = pd.read_csv(f"{DATA}/ch3m.csv", dtype={"month": str}).set_index("month")["ch_3m_interbank_pct"]
us = pd.read_csv(f"{DATA}/us3m.csv", dtype={"month": str}).set_index("month")["us_3m_interbank_pct"]
fx = pd.read_csv(f"{DATA}/usdchf_daily.csv", parse_dates=["date"])
fx["month"] = fx["date"].dt.strftime("%Y-%m")
fx_last = fx.groupby("month").tail(1).set_index("month")           # last H.10 observation of each month
S = fx_last["chf_per_usd"]

# ASSUMPTION A3: the US rate for April 2020 is missing at source; use the mean of March and May 2020.
us_filled = us.copy()
assert np.isnan(us_filled["2020-04"])
us_filled["2020-04"] = round((us["2020-03"] + us["2020-05"]) / 2, 2)

months = [m for m in sp.index if m >= "1999-07" and m <= "2026-10"]
df = pd.DataFrame(index=months)
df["P"] = sp.reindex(months)
df["S"] = S.reindex(months)
df["S_date"] = fx_last["date"].reindex(months).dt.strftime("%Y-%m-%d")
df["i_ch"] = ch.reindex(months)
df["i_us"] = us_filled.reindex(months)
assert df[["P", "S"]].notna().all().all()

# ---------- monthly returns (month t+1, forward struck at end of month t) ----------
# ASSUMPTION A1: covered interest parity with the two OECD three month interbank rates, no basis, no costs.
# ASSUMPTION A2: the monthly average rate of month t stands in for the one month rate at the end of month t;
#                simple accrual over one twelfth of a year.
r = pd.DataFrame(index=months[1:])
P0, P1 = df["P"].shift(1), df["P"]
S0, S1 = df["S"].shift(1), df["S"]
F0 = S0 * (1 + df["i_ch"].shift(1) / 1200) / (1 + df["i_us"].shift(1) / 1200)
r["r_local"] = (P1 / P0 - 1)[1:]                      # S&P 500 TR in USD
r["r_fx"] = (S1 / S0 - 1)[1:]                         # change in CHF per USD
r["carry"] = (F0 / S0 - 1)[1:]                        # forward premium of the dollar (negative when USD rates are higher)
r["x"] = r["r_fx"] - r["carry"]                       # payoff of staying long dollars instead of selling them forward
r["r_unhedged"] = ((P1 / P0) * (S1 / S0) - 1)[1:]
r["rf_chf"] = (df["i_ch"].shift(1) / 1200)[1:]
r["diff_pct"] = (df["i_us"].shift(1) - df["i_ch"].shift(1))[1:]   # USD minus CHF rate known at start of month
assert r.notna().all().all(), r[r.isna().any(axis=1)]
n = len(r)

def hedged(h, extra_cost_pa=0.0):
    """CHF return with a share h of the opening dollar value sold forward one month."""
    return r["r_unhedged"] - h * r["x"] - h * extra_cost_pa / 12

def stats(x):
    x = np.asarray(x, float)
    idx = np.cumprod(1 + x)
    peak = np.maximum.accumulate(np.concatenate([[1.0], idx]))[1:]
    roll12 = pd.Series(1 + x).rolling(12).apply(np.prod, raw=True) - 1
    ex = x - r["rf_chf"].values
    return {
        "ann_return": idx[-1] ** (12 / len(x)) - 1,
        "ann_vol": x.std(ddof=1) * math.sqrt(12),
        "max_drawdown": (idx / np.maximum(peak, 1.0) - 1).min(),
        "worst_12m": roll12.min(),
        "best_12m": roll12.max(),
        "sharpe_vs_chf_cash": ex.mean() * 12 / (ex.std(ddof=1) * math.sqrt(12)),
        "growth_of_100": 100 * idx[-1],
    }

def ols(y, x, nw_lags=6):
    """Slope of y on x with White and Newey West standard errors."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    X = np.column_stack([np.ones_like(x), x]); T = len(y)
    b = np.linalg.solve(X.T @ X, X.T @ y); e = y - X @ b
    XtXi = np.linalg.inv(X.T @ X)
    def cov(L):
        Sm = (X * e[:, None]).T @ (X * e[:, None])
        for l in range(1, L + 1):
            w = 1 - l / (L + 1)
            G = (X[l:] * e[l:, None]).T @ (X[:-l] * e[:-l, None])
            Sm += w * (G + G.T)
        return XtXi @ Sm @ XtXi * T / (T - 2)
    return {"alpha": b[0], "beta": b[1], "se_white": math.sqrt(cov(0)[1, 1]), "se_nw": math.sqrt(cov(nw_lags)[1, 1]),
            "se_alpha_nw": math.sqrt(cov(nw_lags)[0, 0]), "r2": 1 - e.var() / y.var(), "n": T}

res = {"sample": {"first_return_month": r.index[0], "last_return_month": r.index[-1], "n_months": n, "years": n / 12,
                  "spot_start": float(df["S"].iloc[0]), "spot_start_date": df["S_date"].iloc[0],
                  "spot_end": float(df["S"].iloc[-1]), "spot_end_date": df["S_date"].iloc[-1],
                  "us_2020_04_filled": float(us_filled["2020-04"])}}

# ---------- 1. headline table ----------
res["usd_local"] = stats(r["r_local"])
res["usd_local"].pop("sharpe_vs_chf_cash")
res["strategies"] = {f"h{int(h*100):03d}": stats(hedged(h)) for h in [0, 0.25, 0.5, 0.75, 1.0]}
res["frontier"] = [{"h": round(h, 2), **{k: v for k, v in stats(hedged(h)).items() if k in ("ann_return", "ann_vol", "max_drawdown")}}
                   for h in np.arange(0, 1.51, 0.05)]

# ---------- 2. minimum variance hedge ratio ----------
reg = ols(r["r_unhedged"], r["x"])
res["min_var_hedge"] = {"h_star": reg["beta"], "se_white": reg["se_white"], "se_nw6": reg["se_nw"],
                        "ci95_low": reg["beta"] - 1.96 * reg["se_nw"], "ci95_high": reg["beta"] + 1.96 * reg["se_nw"],
                        "vol_at_h_star": hedged(reg["beta"]).std(ddof=1) * math.sqrt(12)}
res["correlations"] = {"local_vs_fx": float(np.corrcoef(r["r_local"], r["r_fx"])[0, 1]),
                       "vol_fx": r["r_fx"].std(ddof=1) * math.sqrt(12), "vol_local": r["r_local"].std(ddof=1) * math.sqrt(12)}

# ---------- 3. carry versus realized depreciation ----------
ls, lc = np.log1p(r["r_fx"]), np.log1p(r["carry"])
lx = ls - lc
res["carry_vs_spot"] = {
    "spot_log_pa": ls.mean() * 12, "carry_log_pa": lc.mean() * 12, "excess_log_pa": lx.mean() * 12,
    "spot_total_change": float(df["S"].iloc[-1] / df["S"].iloc[0] - 1),
    "spot_cagr": float((df["S"].iloc[-1] / df["S"].iloc[0]) ** (12 / n) - 1),
    "carry_cum": float(np.expm1(lc.sum())), "avg_diff_pct": r["diff_pct"].mean(),
    "x_mean_pa": r["x"].mean() * 12, "x_se_pa": r["x"].std(ddof=1) / math.sqrt(n) * 12, "x_tstat": r["x"].mean() / (r["x"].std(ddof=1) / math.sqrt(n)),
    "x_vol_pa": r["x"].std(ddof=1) * math.sqrt(12),
    "share_months_unhedged_beats_hedged": float((r["x"] > 0).mean()),
}
fama = ols(r["r_fx"], r["carry"])
res["fama_regression"] = {"beta": fama["beta"], "se_nw6": fama["se_nw"], "se_white": fama["se_white"], "alpha": fama["alpha"], "r2": fama["r2"],
                          "t_beta_vs_1": (fama["beta"] - 1) / fama["se_nw"], "t_beta_vs_0": fama["beta"] / fama["se_nw"]}
# terciles of the rate differential known at the start of the month
q = pd.qcut(r["diff_pct"], 3, labels=["low", "mid", "high"])
res["carry_terciles"] = {str(k): {"n": int((q == k).sum()), "diff_min": float(r["diff_pct"][q == k].min()), "diff_max": float(r["diff_pct"][q == k].max()),
                                   "avg_diff": float(r["diff_pct"][q == k].mean()),
                                   "spot_pa": float(r["r_fx"][q == k].mean() * 12), "carry_pa": float(r["carry"][q == k].mean() * 12),
                                   "x_pa": float(r["x"][q == k].mean() * 12),
                                   "x_tstat": float(r["x"][q == k].mean() / (r["x"][q == k].std(ddof=1) / math.sqrt((q == k).sum())))}
                         for k in ["low", "mid", "high"]}

# ---------- 4. sub periods ----------
def block(a, b):
    m = (r.index >= a) & (r.index <= b); rr = r[m]
    g = lambda v: float(np.prod(1 + v) ** (12 / len(v)) - 1)
    hreg = ols(rr["r_unhedged"], rr["x"])
    return {"from": a, "to": b, "n": int(m.sum()), "ret_unhedged": g(rr["r_unhedged"]), "ret_hedged": g(rr["r_unhedged"] - rr["x"]),
            "vol_unhedged": float(rr["r_unhedged"].std(ddof=1) * math.sqrt(12)), "vol_hedged": float((rr["r_unhedged"] - rr["x"]).std(ddof=1) * math.sqrt(12)),
            "corr_local_fx": float(np.corrcoef(rr["r_local"], rr["r_fx"])[0, 1]), "h_star": hreg["beta"],
            "spot_pa": float((1 + rr["r_fx"]).prod() ** (12 / len(rr)) - 1), "avg_diff_pct": float(rr["diff_pct"].mean())}
assert n % 3 == 0
BLOCKS = [(r.index[i * n // 3], r.index[(i + 1) * n // 3 - 1]) for i in range(3)]     # three equal blocks of n/3 months
assert BLOCKS == [("1999-08", "2008-08"), ("2008-09", "2017-09"), ("2017-10", "2026-10")]
res["subperiods"] = [block(a, b) for a, b in BLOCKS]
res["sample"]["block_months"] = n // 3

# ---------- 5. rolling 60 month statistics ----------
W = 60
roll = pd.DataFrame(index=r.index)
roll["corr_local_fx"] = r["r_local"].rolling(W).corr(r["r_fx"])
roll["h_star"] = r["r_unhedged"].rolling(W).cov(r["x"]) / r["x"].rolling(W).var()
roll["vol_unhedged"] = r["r_unhedged"].rolling(W).std() * math.sqrt(12)
roll["vol_hedged"] = hedged(1.0).rolling(W).std() * math.sqrt(12)
rv = roll.dropna()
res["rolling60"] = {"corr_min": float(rv["corr_local_fx"].min()), "corr_min_month": rv["corr_local_fx"].idxmin(),
                    "corr_max": float(rv["corr_local_fx"].max()), "corr_max_month": rv["corr_local_fx"].idxmax(),
                    "corr_last": float(rv["corr_local_fx"].iloc[-1]), "h_star_min": float(rv["h_star"].min()), "h_star_min_month": rv["h_star"].idxmin(),
                    "h_star_max": float(rv["h_star"].max()), "h_star_max_month": rv["h_star"].idxmax(), "h_star_last": float(rv["h_star"].iloc[-1]),
                    "share_windows_hedged_lower_vol": float((rv["vol_hedged"] < rv["vol_unhedged"]).mean()), "n_windows": int(len(rv)),
                    "share_windows_h_star_above_half": float((rv["h_star"] > 0.5).mean())}

# ---------- 6. stress behavior ----------
worst = r.nsmallest(20, "r_local")
res["worst20"] = {"avg_local": float(worst["r_local"].mean()), "avg_fx": float(worst["r_fx"].mean()),
                  "n_usd_down": int((worst["r_fx"] < 0).sum()), "n_usd_up": int((worst["r_fx"] > 0).sum()),
                  "avg_unhedged": float(worst["r_unhedged"].mean()), "avg_hedged": float((worst["r_unhedged"] - worst["x"]).mean()),
                  "months": [{"month": m, "local": float(v.r_local), "fx": float(v.r_fx)} for m, v in worst.iterrows()]}
# Falls of at least 15 percent in the S&P 500 (USD, month end data), from a peak to the following trough.
# A trough is the lowest month end before the index recovers by at least 15 percent (or before the sample ends).
TH = 0.15
lvl = df["P"]; episodes = []; peak_m = lvl.index[0]; trough_m = lvl.index[0]
for m in lvl.index[1:]:
    if lvl[m] < lvl[trough_m]:
        trough_m = m
    if lvl[trough_m] / lvl[peak_m] - 1 <= -TH:
        if lvl[m] / lvl[trough_m] - 1 >= TH:                 # recovery confirms the trough
            episodes.append((peak_m, trough_m)); peak_m = trough_m = m
    elif lvl[m] >= lvl[peak_m]:
        peak_m = trough_m = m
if lvl[trough_m] / lvl[peak_m] - 1 <= -TH:
    episodes.append((peak_m, trough_m))
ep = []
for a, b in episodes:
    m = (r.index > a) & (r.index <= b); rr = r[m]
    ep.append({"peak": a, "trough": b, "months": int(m.sum()), "local": float((1 + rr["r_local"]).prod() - 1), "fx": float((1 + rr["r_fx"]).prod() - 1),
               "unhedged": float((1 + rr["r_unhedged"]).prod() - 1), "hedged": float((1 + rr["r_unhedged"] - rr["x"]).prod() - 1),
               "half": float((1 + rr["r_unhedged"] - 0.5 * rr["x"]).prod() - 1)})
res["episodes"] = ep

# ---------- 7. where we are now ----------
i_us_now, i_ch_now = float(df["i_us"]["2026-09"]), float(df["i_ch"]["2026-09"])
d_now = i_us_now - i_ch_now
res["now"] = {"month": "2026-09", "i_us": i_us_now, "i_ch": i_ch_now, "diff": d_now,
              "annual_carry": ((1 + i_ch_now / 1200) / (1 + i_us_now / 1200)) ** 12 - 1,
              "diff_percentile": float((r["diff_pct"] < d_now).mean()), "diff_max": float(r["diff_pct"].max()),
              "diff_min": float(r["diff_pct"].min()), "diff_median": float(r["diff_pct"].median()),
              "spot_last": float(df["S"].iloc[-1]),
              "ytd_2026": {k: float((1 + v[r.index >= "2026-01"]).prod() - 1) for k, v in
                           {"local": r["r_local"], "fx": r["r_fx"], "unhedged": r["r_unhedged"], "hedged": hedged(1.0)}.items()},
              "cal_2025": {k: float((1 + v[(r.index >= "2025-01") & (r.index <= "2025-12")]).prod() - 1) for k, v in
                           {"local": r["r_local"], "fx": r["r_fx"], "unhedged": r["r_unhedged"], "hedged": hedged(1.0)}.items()}}

# ---------- 8. sensitivity to the carry proxy ----------
res["sensitivity"] = {f"extra_cost_{int(c*10000)}bp": {"h100_return": stats(hedged(1.0, c))["ann_return"], "h050_return": stats(hedged(0.5, c))["ann_return"],
                                                       "h100_vol": stats(hedged(1.0, c))["ann_vol"], "h100_max_drawdown": stats(hedged(1.0, c))["max_drawdown"],
                                                       "h100_worst_12m": stats(hedged(1.0, c))["worst_12m"], "h100_growth_of_100": stats(hedged(1.0, c))["growth_of_100"]}
                      for c in [-0.0025, 0.0, 0.0025, 0.005]}
# break even extra cost at which fully hedged and unhedged compound to the same value
lo, hi_ = -0.05, 0.05
for _ in range(60):
    mid = (lo + hi_) / 2
    if stats(hedged(1.0, mid))["ann_return"] > res["strategies"]["h000"]["ann_return"]: lo = mid
    else: hi_ = mid
res["sensitivity"]["break_even_extra_cost_pa"] = (lo + hi_) / 2


# ---------- 9. robustness of the hedge ratio across the three sub periods ----------
grid = np.round(np.arange(0, 1.0001, 0.05), 2)
blocks = BLOCKS
vol_grid = {}
for a, b in blocks:
    m = (r.index >= a) & (r.index <= b)
    vol_grid[f"{a}_{b}"] = [float((r["r_unhedged"][m] - h * r["x"][m]).std(ddof=1) * math.sqrt(12)) for h in grid]
regret = {k: [v_ - min(v) for v_ in v] for k, v in vol_grid.items()}        # extra volatility versus the best ratio on the grid
max_regret = [max(regret[k][i] for k in regret) for i in range(len(grid))]
i_best = int(np.argmin(max_regret))
res["regret"] = {"grid": [float(g) for g in grid], "vol_by_block": vol_grid, "max_regret": max_regret,
                 "minimax_h": float(grid[i_best]), "minimax_regret": max_regret[i_best],
                 "max_regret_h000": max_regret[0], "max_regret_h050": max_regret[list(grid).index(0.5)],
                 "max_regret_h075": max_regret[list(grid).index(0.75)], "max_regret_h100": max_regret[-1]}
res["twelve_month_break_even_spot"] = float(df["S"].iloc[-1] * (1 + res["now"]["annual_carry"]))


# ---------- 10. Early 2025: equities and the dollar fell together ----------
# From the month end high of January 2025 to the month end low of April 2025 (a fall below the 15 percent threshold).
seg = lvl["2024-12":"2025-12"]
assert seg.loc["2025-01"] == seg.loc[:"2025-04"].max() and seg.loc["2025-04"] == seg.loc["2025-01":"2025-09"].min()
m = (r.index >= "2025-02") & (r.index <= "2025-04"); rr = r[m]
res["early_2025"] = {"peak": "2025-01", "trough": "2025-04", "local": float((1 + rr["r_local"]).prod() - 1), "fx": float((1 + rr["r_fx"]).prod() - 1),
                     "unhedged": float((1 + rr["r_unhedged"]).prod() - 1), "hedged": float((1 + rr["r_unhedged"] - rr["x"]).prod() - 1)}
# chart series
ch_ = pd.DataFrame(index=[df.index[0]] + list(r.index))
ch_["unhedged"] = np.concatenate([[100], 100 * np.cumprod(1 + r["r_unhedged"].values)])
ch_["hedged_100"] = np.concatenate([[100], 100 * np.cumprod(1 + hedged(1.0).values)])
ch_["hedged_075"] = np.concatenate([[100], 100 * np.cumprod(1 + hedged(0.75).values)])
ch_["usd_local"] = np.concatenate([[100], 100 * np.cumprod(1 + r["r_local"].values)])
ch_["spot_index"] = np.concatenate([[100], 100 * np.cumprod(1 + r["r_fx"].values)])
ch_["forward_implied_index"] = np.concatenate([[100], 100 * np.cumprod(1 + r["carry"].values)])
ch_["diff_pct"] = (df["i_us"] - df["i_ch"]).reindex(ch_.index)
ch_.to_csv(f"{OUT}/chart_series.csv", index_label="month", float_format="%.6f")
res["chart_end_values"] = {k: float(ch_[k].iloc[-1]) for k in ["unhedged", "hedged_100", "hedged_075", "usd_local", "spot_index", "forward_implied_index"]}
res["strategies"]["h075"]["growth_of_100_check"] = float(ch_["hedged_075"].iloc[-1])


# ---------- 11. checks behind statements made in the text ----------
dn, up = r[r["r_local"] < 0], r[r["r_local"] >= 0]
fr_ = pd.DataFrame(res["frontier"])
hi_ter = (r["diff_pct"] >= res["carry_terciles"]["high"]["diff_min"]).astype(int)
res["text_checks"] = {
    "n_down_months": int(len(dn)), "avg_fx_in_down_months": float(dn["r_fx"].mean()), "avg_fx_in_up_months": float(up["r_fx"].mean()),
    "flat_band_50_to_90": float(fr_[(fr_["h"] >= 0.5) & (fr_["h"] <= 0.9)]["ann_vol"].max() - fr_["ann_vol"].min()),
    "wide_gap_episodes": int((hi_ter.diff() == 1).sum() + int(hi_ter.iloc[0] == 1)),
    "roll_h_max_2017_2019": float(roll.loc["2017-01":"2019-12", "h_star"].max()),
    "roll_h_min_2017_2019": float(roll.loc["2017-01":"2019-12", "h_star"].min()),
    "vol_cut_block1": float(res["subperiods"][0]["vol_unhedged"] - res["subperiods"][0]["vol_hedged"]),
}
tc = res["text_checks"]
assert tc["avg_fx_in_down_months"] > 0 > tc["avg_fx_in_up_months"]
assert tc["flat_band_50_to_90"] < 0.002 and tc["wide_gap_episodes"] == 4 and tc["vol_cut_block1"] > 0.04
assert res["subperiods"][1]["vol_hedged"] > res["subperiods"][1]["vol_unhedged"] and res["subperiods"][2]["vol_hedged"] > res["subperiods"][2]["vol_unhedged"]
assert not (res["min_var_hedge"]["ci95_low"] <= 0 or res["min_var_hedge"]["ci95_high"] >= 1)


# ---------- 12. robustness: other equal splits, the period since September 2008, and hedge settlements ----------
def minimax_split(k):
    edges = [round(i * n / k) for i in range(k + 1)]
    vols = np.array([[float((r["r_unhedged"].iloc[edges[i]:edges[i + 1]] - h * r["x"].iloc[edges[i]:edges[i + 1]]).std(ddof=1) * math.sqrt(12))
                      for h in grid] for i in range(k)])
    mr = (vols - vols.min(axis=1, keepdims=True)).max(axis=0)
    return {"blocks": k, "minimax_h": float(grid[int(mr.argmin())]), "minimax_regret": float(mr.min()),
            "regret_h000": float(mr[0]), "regret_h100": float(mr[-1]), "first_months": [r.index[e] for e in edges[:-1]]}
res["alt_splits"] = [minimax_split(k) for k in (2, 3, 4, 5)]
assert abs(res["alt_splits"][1]["minimax_h"] - res["regret"]["minimax_h"]) < 1e-9
since = r[r.index >= "2008-09"]
res["since_2008_09"] = {"n": int(len(since)), "h_star": ols(since["r_unhedged"], since["x"])["beta"]}
res["min_var_hedge"]["ci95_low_white"] = reg["beta"] - 1.96 * reg["se_white"]
res["min_var_hedge"]["ci95_high_white"] = reg["beta"] + 1.96 * reg["se_white"]
roll12x = r["x"].rolling(12).sum()
res["hedge_settlements"] = {"max_12m_loss_share_of_notional": float(roll12x.max()), "window_end": roll12x.idxmax(),
                            "max_1m_loss": float(r["x"].max()), "max_1m_month": r["x"].idxmax()}
def worst_window(x):
    roll12 = (1 + x).rolling(12).apply(np.prod, raw=True) - 1
    end = roll12.idxmin(); i = list(r.index).index(end); w = r.iloc[i - 11:i + 1]
    return {"start": w.index[0], "end": end, "return": float(roll12.min()), "fx": float((1 + w["r_fx"]).prod() - 1),
            "unhedged_same_window": float((1 + w["r_unhedged"]).prod() - 1), "hedged_same_window": float((1 + w["r_unhedged"] - w["x"]).prod() - 1)}
res["worst_12m_windows"] = {"unhedged": worst_window(r["r_unhedged"]), "hedged": worst_window(hedged(1.0))}
res["min_var_hedge"]["se_by_lags"] = {str(L): ols(r["r_unhedged"], r["x"], nw_lags=L)["se_nw"] for L in (0, 3, 6, 12, 24)}
res["min_var_hedge"]["ci95_high_by_lags"] = {k: reg["beta"] + 1.96 * v for k, v in res["min_var_hedge"]["se_by_lags"].items()}
assert max(res["min_var_hedge"]["ci95_high_by_lags"].values()) < 1
res["fama_regression"]["se_label"] = "Newey West, six lags"
assert res["hedge_settlements"]["window_end"] == "2012-07" and 0.35 < res["since_2008_09"]["h_star"] < 0.50
assert res["subperiods"][0]["h_star"] > 1 and res["text_checks"]["roll_h_min_2017_2019"] > 0.7
assert res["worst_12m_windows"]["hedged"]["start"] == "2008-03" and res["worst_12m_windows"]["hedged"]["end"] == "2009-02"
# facts typed in the note, asserted here
assert months[-1] == "2026-10" and df["S_date"].iloc[-1] == "2026-10-30" and df["S_date"].iloc[0] == "1999-07-30"
assert ch.index[-1] == "2026-09" and us.index[-1] == "2026-09" and -0.1 < res["now"]["i_ch"] < 0
assert rv.index[-1] == "2026-10" and r.index[-60] == "2021-11"
dd_top = [f_["max_drawdown"] for f_ in res["frontier"] if 0.899 < f_["h"] < 1.001]
res["text_checks"]["max_drawdown_range_90_to_100"] = [float(min(dd_top)), float(max(dd_top))]
assert max(dd_top) - min(dd_top) < 0.002          # the maximum drawdown is flat above a 90 percent hedge
dd_all = [f_["max_drawdown"] for f_ in res["frontier"] if f_["h"] < 0.901]
assert all(b_ > a_ for a_, b_ in zip(dd_all, dd_all[1:]))   # and shrinks at every step up to 90 percent
assert df["S_date"]["2010-12"] == "2010-12-30" and df["S_date"]["2021-12"] == "2021-12-30"
assert [df["S_date"][m_] for m_ in ("2002-03", "2013-03", "2018-03", "2024-03")] == ["2002-03-29", "2013-03-29", "2018-03-30", "2024-03-29"]
res["autocorr_1"] = {"r_unhedged": float(r["r_unhedged"].autocorr(1)), "x": float(r["x"].autocorr(1))}

# calendar year table
r["year"] = [m[:4] for m in r.index]
cal = r.groupby("year").apply(lambda g: pd.Series({"local": (1 + g.r_local).prod() - 1, "fx": (1 + g.r_fx).prod() - 1,
                                                    "unhedged": (1 + g.r_unhedged).prod() - 1, "hedged": (1 + g.r_unhedged - g.x).prod() - 1, "n": len(g)}))
assert sorted(cal.index[cal["n"] == 12]) == [str(y) for y in range(2000, 2026)]
res["calendar"] = {"n_full_years": int((cal["n"] == 12).sum()),
                   "n_years_hedged_beats": int(((cal["hedged"] > cal["unhedged"]) & (cal["n"] == 12)).sum())}

# ---------- outputs ----------
panel = r.drop(columns=["year"]).copy()
panel["r_hedged_100"] = hedged(1.0); panel["r_hedged_050"] = hedged(0.5)
panel.insert(0, "sp500tr_close", df["P"].reindex(panel.index)); panel.insert(1, "chf_per_usd", df["S"].reindex(panel.index))
panel.insert(2, "fx_obs_date", df["S_date"].reindex(panel.index))
panel.to_csv(f"{OUT}/monthly_panel.csv", index_label="month", float_format="%.8f")
df.to_csv(f"{OUT}/levels.csv", index_label="month")
roll.to_csv(f"{OUT}/rolling60.csv", index_label="month", float_format="%.6f")
cal.to_csv(f"{OUT}/calendar_years.csv", float_format="%.6f")
json.dump(res, open(f"{OUT}/results.json", "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))
