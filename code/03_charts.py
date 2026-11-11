"""
Step 3. Figures for the note (grayscale, vector PDF through XeLaTeX with the Inter typeface).
Usage: python 03_charts.py <output_folder>
"""
import sys, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("pgf")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, FixedLocator

OUT = sys.argv[1]
res = json.load(open(f"{OUT}/results.json"))
cs = pd.read_csv(f"{OUT}/chart_series.csv", dtype={"month": str}).set_index("month")
roll = pd.read_csv(f"{OUT}/rolling60.csv", dtype={"month": str}).set_index("month")
t = pd.to_datetime(cs.index + "-28")
tr = pd.to_datetime(roll.index + "-28")

BLACK, DARK, MID, LIGHT, GRID = "#000000", "#4d4d4d", "#8c8c8c", "#bdbdbd", "#e3e3e3"
plt.rcParams.update({
    "pgf.texsystem": "xelatex", "pgf.rcfonts": False, "font.family": "sans-serif",
    "pgf.preamble": r"\usepackage{fontspec}\setmainfont{Inter}[RawFeature={-calt}]\setsansfont{Inter}[RawFeature={-calt}]\pagestyle{empty}",
    "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.5, "axes.edgecolor": MID,
    "xtick.color": BLACK, "ytick.color": BLACK, "text.color": BLACK, "axes.labelcolor": BLACK,
    "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 3, "ytick.major.size": 0,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.5, "axes.axisbelow": True,
})
W = 6.3   # inches, full text width
def num(v, d=0):
    return f"{v:,.{d}f}".replace("-", r'\symbol{"2212}')      # true minus sign taken from the text font
def pct(d=0, scale=1.0):
    return FuncFormatter(lambda v, p: num(v * scale, d) + r"\%")
def plain(d=0):
    return FuncFormatter(lambda v, p: num(v, d))
def years(ax):
    ax.set_xlim(pd.Timestamp("1999-06-01"), pd.Timestamp("2029-06-01"))
    ticks = pd.to_datetime([f"{y}-01-01" for y in range(2000, 2027, 5)])
    ax.set_xticks(ticks); ax.set_xticklabels([str(d.year) for d in ticks])

# ---- Figure 2 in the note: growth of CHF 100 ----
fig, ax = plt.subplots(figsize=(W, 2.45))
ax.plot(t, cs["unhedged"], color=BLACK, lw=1.3)
ax.plot(t, cs["hedged_100"], color=MID, lw=1.3)
ax.set_yscale("log"); ax.set_ylim(40, 700)
ax.yaxis.set_major_locator(FixedLocator([50, 100, 200, 400])); ax.yaxis.set_minor_locator(FixedLocator([]))
ax.yaxis.set_major_formatter(plain()); years(ax)
ax.set_ylabel("CHF, log scale")
e = res["chart_end_values"]
ax.annotate(f"Fully hedged  {num(e['hedged_100'])}", (t[-1], e["hedged_100"]), xytext=(6, 5), textcoords="offset points", va="bottom", fontsize=7.5, color=BLACK)
ax.annotate(f"Unhedged  {num(e['unhedged'])}", (t[-1], e["unhedged"]), xytext=(6, -5), textcoords="offset points", va="top", fontsize=7.5, color=BLACK)
ax.plot([], [], color=BLACK, lw=1.3, label="Unhedged"); ax.plot([], [], color=MID, lw=1.3, label="Fully hedged")
ax.legend(loc="upper left", frameon=False, fontsize=7.5, handlelength=1.8)
fig.tight_layout(pad=0.4); fig.savefig(f"{OUT}/fig2_growth.pdf"); plt.close(fig)

# ---- Figure 1 in the note: spot path versus the path implied by the rate gap ----
fig, ax = plt.subplots(figsize=(W, 2.3))
ax.plot(t, cs["spot_index"], color=BLACK, lw=1.3)
ax.plot(t, cs["forward_implied_index"], color=MID, lw=1.3)
ax.set_ylim(40, 125); ax.yaxis.set_major_formatter(plain()); years(ax)
ax.set_ylabel("Index, July 1999 = 100")
ax.annotate(f"Forward implied  {num(e['forward_implied_index'], 1)}", (t[-1], e["forward_implied_index"]), xytext=(6, 4), textcoords="offset points", va="bottom", fontsize=7.5)
ax.annotate(f"Actual spot  {num(e['spot_index'], 1)}", (t[-1], e["spot_index"]), xytext=(6, -4), textcoords="offset points", va="top", fontsize=7.5)
ax.plot([], [], color=BLACK, lw=1.3, label="Dollar in francs, actual spot"); ax.plot([], [], color=MID, lw=1.3, label="Path implied by the rate gap")
ax.legend(loc="upper right", frameon=False, fontsize=7.5, handlelength=1.8, bbox_to_anchor=(0.9, 1.0))
fig.tight_layout(pad=0.4); fig.savefig(f"{OUT}/fig1_spot_vs_forward.pdf"); plt.close(fig)

# ---- Figure 3: volatility against hedge ratio, full sample and three sub periods ----
fig, ax = plt.subplots(figsize=(W, 2.65))
fr = pd.DataFrame(res["frontier"]); fr = fr[fr["h"] <= 1.0001]
g = np.array(res["regret"]["grid"]); vb = res["regret"]["vol_by_block"]
styles = [((0, (4, 2)), "Aug 1999 to Aug 2008"), ((0, (1, 1.5)), "Sep 2008 to Sep 2017"), ((0, (6, 1.5, 1, 1.5)), "Oct 2017 to Oct 2026")]
for (ls, lab), (k, v) in zip(styles, vb.items()):
    v = np.array(v) * 100
    ax.plot(g * 100, v, color=MID, lw=1.1, ls=ls, label=lab)
    i = int(np.argmin(v)); ax.plot(g[i] * 100, v[i], "o", ms=4, mfc="white", mec=DARK, mew=0.9, zorder=5, clip_on=False)
ax.plot(fr["h"] * 100, fr["ann_vol"] * 100, color=BLACK, lw=1.6, label="Full sample")
i = int(np.argmin(fr["ann_vol"].values)); ax.plot(fr["h"].values[i] * 100, fr["ann_vol"].values[i] * 100, "o", ms=4.5, color=BLACK, zorder=6)
ax.set_xlim(0, 100); ax.set_ylim(13, 19)
ax.xaxis.set_major_locator(FixedLocator(range(0, 101, 25))); ax.xaxis.set_major_formatter(pct()); ax.yaxis.set_major_formatter(pct())
ax.set_xlabel("Hedge ratio (share of opening dollar value sold forward)"); ax.set_ylabel("Annualized volatility in CHF")
ax.legend(loc="upper center", frameon=False, fontsize=7.5, handlelength=3.2, ncol=4, bbox_to_anchor=(0.5, 1.13), columnspacing=1.4)
fig.tight_layout(pad=0.4); fig.savefig(f"{OUT}/fig3_vol_vs_hedge.pdf"); plt.close(fig)

# ---- Figure 4: rolling 60 month correlation and minimum variance hedge ratio (two panels, one axis each) ----
fig, (a1, a2) = plt.subplots(2, 1, figsize=(W, 3.35), sharex=True, gridspec_kw={"hspace": 0.28})
rv = roll.dropna(); trv = pd.to_datetime(rv.index + "-28")
a1.axhline(0, color=MID, lw=0.6); a1.plot(trv, rv["corr_local_fx"], color=BLACK, lw=1.3)
a1.set_ylim(-0.65, 0.35); a1.yaxis.set_major_locator(FixedLocator([-0.6, -0.4, -0.2, 0, 0.2])); a1.yaxis.set_major_formatter(plain(1))
a1.set_title("Correlation between S\\&P 500 returns in dollars and the change in the dollar against the franc", loc="left", fontsize=8, pad=5)
a2.axhline(1, color=MID, lw=0.6); a2.axhline(0, color=MID, lw=0.6)
a2.plot(trv, rv["h_star"], color=BLACK, lw=1.3)
a2.set_ylim(-0.1, 1.45); a2.yaxis.set_major_locator(FixedLocator([0, 0.25, 0.5, 0.75, 1.0, 1.25])); a2.yaxis.set_major_formatter(pct(0, 100))
a2.set_title("Hedge ratio that would have minimized volatility", loc="left", fontsize=8, pad=5)
for a in (a1, a2):
    a.set_xlim(pd.Timestamp("2004-01-01"), pd.Timestamp("2027-06-01"))
    ticks = pd.to_datetime([f"{y}-01-01" for y in range(2005, 2027, 5)]); a.set_xticks(ticks); a.set_xticklabels([str(d.year) for d in ticks])
a1.tick_params(axis="x", length=0)
fig.subplots_adjust(left=0.085, right=0.985, top=0.93, bottom=0.07); fig.savefig(f"{OUT}/fig4_rolling.pdf"); plt.close(fig)

# ---- Figure 5: rate gap ----
fig, ax = plt.subplots(figsize=(W, 2.05))
d = cs["diff_pct"].dropna(); td = pd.to_datetime(d.index + "-28")
ax.plot(td, d, color=BLACK, lw=1.3)
now = res["now"]["diff"]
ax.axhline(now, color=MID, lw=0.7, ls=(0, (4, 2)))
ax.annotate(f"September 2026: {num(now, 2)}", (pd.Timestamp("2010-06-01"), now), xytext=(0, 4), textcoords="offset points", fontsize=7.5, ha="center")
ax.set_ylim(0, 5); ax.yaxis.set_major_formatter(plain()); years(ax); ax.set_xlim(pd.Timestamp("1999-06-01"), pd.Timestamp("2027-06-01"))
ax.set_ylabel("Percentage points")
fig.tight_layout(pad=0.4); fig.savefig(f"{OUT}/fig5_rate_gap.pdf"); plt.close(fig)
print("figures written")
