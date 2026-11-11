"""
Step 4. Turn results.json into LaTeX macros and table bodies, so that every computed statistic in the note comes from the scripts.
Usage: python 04_numbers.py <output_folder> <note_folder>
"""
import sys, json
OUT, NOTE = sys.argv[1], sys.argv[2]
R = json.load(open(f"{OUT}/results.json"))
MINUS = "\u2212"

def f(v, d=1):                      # plain number, true minus sign
    s = f"{v:.{d}f}"
    if float(s) == 0: s = s.lstrip("-")
    return s.replace("-", MINUS)
def p(v, d=1): return f(v * 100, d)  # fraction to percent number
def a(v, d=1): return f(abs(v) * 100, d)   # absolute value in percent, for prose ("fell by ...")

S, st = R["strategies"], R["sample"]
mv, cv, now, rg, ro = R["min_var_hedge"], R["carry_vs_spot"], R["now"], R["regret"], R["rolling60"]
sub, ep, w20, ter = R["subperiods"], R["episodes"], R["worst20"], R["carry_terciles"]
n = st["n_months"]
carry_cagr = (1 + cv["carry_cum"]) ** (12 / n) - 1
grid = rg["grid"]
def vb(block, h): return list(rg["vol_by_block"].values())[block][grid.index(h)]
best = [min(v) for v in rg["vol_by_block"].values()]
best_h = [grid[v.index(min(v))] for v in rg["vol_by_block"].values()]

M = {
 "NMonths": str(n), "YearsSample": f(n / 12, 1),
 "SpotStart": f(st["spot_start"], 4), "SpotEnd": f(st["spot_end"], 4),
 "SpotFall": a(cv["spot_total_change"]), "SpotPa": a(cv["spot_cagr"]), "CarryCum": a(cv["carry_cum"]), "CarryPa": a(carry_cagr),
 "AvgDiff": f(cv["avg_diff_pct"], 1),
 "RetLocal": p(R["usd_local"]["ann_return"]), "VolLocal": p(R["usd_local"]["ann_vol"]),
 "RetU": p(S["h000"]["ann_return"]), "RetH": p(S["h100"]["ann_return"]), "RetTq": p(S["h075"]["ann_return"]),
 "RetGap": a(S["h100"]["ann_return"] - S["h000"]["ann_return"]),
 "VolU": p(S["h000"]["ann_vol"]), "VolH": p(S["h100"]["ann_vol"]), "VolTq": p(S["h075"]["ann_vol"]), "VolStar": p(mv["vol_at_h_star"]),
 "DDU": a(S["h000"]["max_drawdown"]), "DDH": a(S["h100"]["max_drawdown"]), "DDTq": a(S["h075"]["max_drawdown"]),
 "WorstU": a(S["h000"]["worst_12m"]), "WorstH": a(S["h100"]["worst_12m"]),
 "GrowthU": f(S["h000"]["growth_of_100"], 0), "GrowthH": f(S["h100"]["growth_of_100"], 0),
 "HStar": p(mv["h_star"], 0), "HStarLo": p(mv["ci95_low"], 0), "HStarHi": p(mv["ci95_high"], 0), "HStarSE": f(mv["se_nw6"], 2), "HStarDec": f(mv["h_star"], 2),
 "CorrAbs": f(abs(R["correlations"]["local_vs_fx"]), 2), "VolFx": p(R["correlations"]["vol_fx"]),
 "XMeanAbs": a(cv["x_mean_pa"]), "XSE": p(cv["x_se_pa"]), "XT": f(cv["x_tstat"], 2), "ShareMonths": p(cv["share_months_unhedged_beats_hedged"]),
 "YearsHedgedBeats": str(R["calendar"]["n_years_hedged_beats"]), "FullYears": str(R["calendar"]["n_full_years"]),
 "RetHCostA": p(R["sensitivity"]["extra_cost_25bp"]["h100_return"]), "RetHCostB": p(R["sensitivity"]["extra_cost_50bp"]["h100_return"]),
 "BreakEvenCost": p(R["sensitivity"]["break_even_extra_cost_pa"], 2),
 "HOne": p(sub[0]["h_star"], 0), "HTwo": p(sub[1]["h_star"], 0), "HThree": p(sub[2]["h_star"], 0),
 "CorrOne": f(sub[0]["corr_local_fx"], 2), "CorrTwoAbs": f(abs(sub[1]["corr_local_fx"]), 2), "CorrThreeAbs": f(abs(sub[2]["corr_local_fx"]), 2),
 "RollHLast": p(ro["h_star_last"], 0), "RollCorrLastAbs": f(abs(ro["corr_last"]), 2), "RollHMin": p(ro["h_star_min"], 0), "RollHMax": p(ro["h_star_max"], 0),
 "RollShareAboveHalf": p(ro["share_windows_h_star_above_half"], 0), "RollN": str(ro["n_windows"]),
 "WUp": str(w20["n_usd_up"]), "WDown": str(w20["n_usd_down"]), "WAvgFx": p(w20["avg_fx"]), "WAvgLocalAbs": a(w20["avg_local"]),
 "WAvgUAbs": a(w20["avg_unhedged"]), "WAvgHAbs": a(w20["avg_hedged"]),
 "IUS": f(now["i_us"], 2), "ICHAbs": f(abs(now["i_ch"]), 2), "DiffNow": f(now["diff"], 2), "CarryNow": a(now["annual_carry"]),
 "Pctile": p(now["diff_percentile"], 0), "BreakEvenSpot": f(R["twelve_month_break_even_spot"], 3),
 "CalLocal": p(now["cal_2025"]["local"]), "CalFxAbs": a(now["cal_2025"]["fx"]), "CalU": p(now["cal_2025"]["unhedged"]), "CalH": p(now["cal_2025"]["hedged"]),
 "YtdLocal": p(now["ytd_2026"]["local"]), "YtdFx": p(now["ytd_2026"]["fx"]), "YtdU": p(now["ytd_2026"]["unhedged"]), "YtdH": p(now["ytd_2026"]["hedged"]),
 "EarlyLocalAbs": a(R["early_2025"]["local"]), "EarlyFxAbs": a(R["early_2025"]["fx"]), "EarlyUAbs": a(R["early_2025"]["unhedged"]), "EarlyHAbs": a(R["early_2025"]["hedged"]),
 "DDHCostB": a(R["sensitivity"]["extra_cost_50bp"]["h100_max_drawdown"]), "GrowthHCostB": f(R["sensitivity"]["extra_cost_50bp"]["h100_growth_of_100"], 0),
 "WorstHFx": p(R["worst_12m_windows"]["hedged"]["fx"]),
 "RegUTwo": f(rg["max_regret_h000"] * 100, 2), "RegTqTwo": f(rg["max_regret_h075"] * 100, 2), "RegEightyTwo": f(rg["minimax_regret"] * 100, 2), "RegHTwo": f(rg["max_regret_h100"] * 100, 2),
 "SELagMin": f(min(mv["se_by_lags"].values()), 2), "SELagMax": f(max(mv["se_by_lags"].values()), 2), "HiCILagMax": p(max(mv["ci95_high_by_lags"].values()), 0),
 "HStarLoWhite": p(mv["ci95_low_white"], 0), "HStarHiWhite": p(mv["ci95_high_white"], 0),
 "BlockMonths": str(st["block_months"]), "HSince": p(R["since_2008_09"]["h_star"], 0),
 "TerHighX": p(ter["high"]["x_pa"]), "TerHighT": f(ter["high"]["x_tstat"], 1), "TerHighSpotAbs": a(ter["high"]["spot_pa"]), "TerHighCarryAbs": a(ter["high"]["carry_pa"]),
 "TerLowXAbs": a(ter["low"]["x_pa"]), "TerHighMin": f(ter["high"]["diff_min"], 1),
 "FamaBetaAbs": f(abs(R["fama_regression"]["beta"]), 2), "FamaSE": f(R["fama_regression"]["se_nw6"], 2),
 "RegU": f(rg["max_regret_h000"] * 100, 1), "RegHalf": f(rg["max_regret_h050"] * 100, 1), "RegTq": f(rg["max_regret_h075"] * 100, 1),
 "RegH": f(rg["max_regret_h100"] * 100, 1), "RegBest": f(rg["minimax_regret"] * 100, 1), "MinimaxH": p(rg["minimax_h"], 0),
 "DownFx": p(R["text_checks"]["avg_fx_in_down_months"]), "UpFxAbs": a(R["text_checks"]["avg_fx_in_up_months"]), "NDown": str(R["text_checks"]["n_down_months"]),
 "AltTwo": p(R["alt_splits"][0]["minimax_h"], 0), "AltFour": p(R["alt_splits"][2]["minimax_h"], 0), "AltFive": p(R["alt_splits"][3]["minimax_h"], 0),
 "CashCall": p(R["hedge_settlements"]["max_12m_loss_share_of_notional"], 0), "CashCallOne": p(R["hedge_settlements"]["max_1m_loss"], 1),
 "FillRate": f(st["us_2020_04_filled"], 2),
 "EndFwd": f(R["chart_end_values"]["forward_implied_index"], 1), "EndSpot": f(R["chart_end_values"]["spot_index"], 1),
}
# signs behind the macros that print absolute values in directional prose
assert cv["spot_total_change"] < 0 and cv["carry_cum"] < 0 and cv["x_mean_pa"] > 0 and S["h100"]["ann_return"] > S["h000"]["ann_return"]
assert R["correlations"]["local_vs_fx"] < 0 and R["fama_regression"]["beta"] < 0 and now["annual_carry"] < 0 and now["i_ch"] < 0
assert now["cal_2025"]["fx"] < 0 and now["cal_2025"]["local"] > 0 and now["ytd_2026"]["unhedged"] > now["ytd_2026"]["hedged"]
assert all(R["early_2025"][k] < 0 for k in ("local", "fx", "unhedged", "hedged")) and w20["avg_fx"] > 0
assert ter["high"]["x_pa"] > 0 > ter["low"]["x_pa"] and ter["high"]["spot_pa"] < 0 and ter["high"]["carry_pa"] < 0
assert sub[1]["corr_local_fx"] < 0 and sub[2]["corr_local_fx"] < 0 and ro["corr_last"] < 0 and R["worst_12m_windows"]["hedged"]["fx"] > 0
import re, os
tex = open(f"{NOTE}/note.tex").read() if os.path.exists(f"{NOTE}/note.tex") else ""
used = {k: (not tex) or bool(re.search(r"\\" + k + r"(?![A-Za-z])", tex)) for k in M}
with open(f"{NOTE}/numbers.tex", "w") as g:
    for k, v in M.items():
        if used[k]: g.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")

def rows(lines): return "\n".join(" & ".join(l) + r" \\" for l in lines) + "\n"
# Table 1: results by hedge ratio
T1 = [[lab, p(S[k]["ann_return"]), p(S[k]["ann_vol"]), p(S[k]["max_drawdown"]), p(S[k]["worst_12m"]), f(S[k]["sharpe_vs_chf_cash"], 2), f(S[k]["growth_of_100"], 0)]
      for lab, k in [("Unhedged (0\\%)", "h000"), ("25\\%", "h025"), ("50\\%", "h050"), ("75\\%", "h075"), ("Fully hedged (100\\%)", "h100")]]
open(f"{NOTE}/t1.tex", "w").write(rows(T1))
# Table 2: sub periods
names = ["Aug 1999 to Aug 2008", "Sep 2008 to Sep 2017", "Oct 2017 to Oct 2026"]
T2 = [[names[i], p(s["ret_unhedged"]), p(s["ret_hedged"]), p(s["vol_unhedged"]), p(s["vol_hedged"]), f(s["corr_local_fx"], 2), p(s["h_star"], 0) + "\\%",
       p(s["spot_pa"]), f(s["avg_diff_pct"], 1)] for i, s in enumerate(sub)]
open(f"{NOTE}/t2.tex", "w").write(rows(T2))
# Table 3: stress episodes
mon = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun", "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}
def my(m): return f"{mon[m[5:]]} {m[:4]}"
T3 = [[f"{my(e['peak'])} to {my(e['trough'])}", p(e["local"]), p(e["fx"]), p(e["unhedged"]), p(e["hedged"])] for e in ep]
sp = R["early_2025"]
T3b = [[f"Memo: {my(sp['peak'])} to {my(sp['trough'])}", p(sp["local"]), p(sp["fx"]), p(sp["unhedged"]), p(sp["hedged"])]]
open(f"{NOTE}/t3.tex", "w").write(rows(T3) + "\\midrule\n" + rows(T3b))
# Table 4: regret
T4 = []
for lab, h in [("Unhedged (0\\%)", 0.0), ("50\\%", 0.5), ("75\\%", 0.75), ("80\\%", 0.8), ("Fully hedged (100\\%)", 1.0)]:
    v = [vb(i, h) for i in range(3)]
    T4.append([lab] + [p(x, 2) for x in v] + [f(max(v[i] - best[i] for i in range(3)) * 100, 2)])
T4b = ["Best ratio from 0\\% to 100\\%"] + [p(best[i], 2) + f" (at {p(best_h[i], 0)}\\%)" for i in range(3)] + [""]
open(f"{NOTE}/t4.tex", "w").write(rows(T4) + "\\midrule\n" + rows([T4b]))
# Table 5: terciles
T5 = [[lab, f(ter[k]["diff_min"], 1) + " to " + f(ter[k]["diff_max"], 1), str(ter[k]["n"]), p(ter[k]["spot_pa"]), p(ter[k]["carry_pa"]), p(ter[k]["x_pa"]), f(ter[k]["x_tstat"], 1)]
      for lab, k in [("Narrow", "low"), ("Middle", "mid"), ("Wide", "high")]]
open(f"{NOTE}/t5.tex", "w").write(rows(T5))
import csv
with open(f"{OUT}/numbers_used_in_note.csv", "w", newline="") as g:
    w = csv.writer(g); w.writerow(["macro", "value"]); [w.writerow([k, v]) for k, v in M.items() if used[k]]
print(sum(used.values()), "macros written")
