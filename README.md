# Hedging the Dollar at Four Percent

Mergim Manxholli, November 2026. Independent analysis based on public information as of 11 November 2026. Not investment advice.

How much of its US equity exposure should a Swiss franc investor hedge? This repository holds the research note and everything needed to rebuild it: `Manxholli_Hedging_the_Dollar_at_Four_Percent.pdf` (9 pages), the input data, the code and every output.

## Findings in brief

S&P 500 Total Return, 327 months, August 1999 to October 2026:

* A fully hedged position returned 6.3% a year in francs and an unhedged one 6.2%. The difference is not statistically different from zero.
* Volatility is lowest at a hedge ratio of about 70%, not 100%.
* The best ratio was above 100% before September 2008 and near 40% afterward. A ratio of 75% stayed within 0.64 volatility points of the best ratio in every period.
* A rate gap of four points is a weak reason to hedge less.

## What is here

| Folder | Content |
|---|---|
| `data/` | The four input files: S&P 500 Total Return month end closes, Swiss and US three month interbank rates, daily USD/CHF |
| `code/` | Four Python scripts, run in order |
| `out/` | Every intermediate output: `results.json` (all statistics), `monthly_panel.csv` (the 327 monthly returns), `levels.csv` (month end levels and rates), `rolling60.csv`, `calendar_years.csv`, `chart_series.csv`, `numbers_used_in_note.csv` (each computed number printed in the running text; table cells are in `note/t1.tex` to `t5.tex`), `log.txt` (console output of the analysis), and the five figures, named by their number in the note |
| `note/` | LaTeX source of the note and the compiled `note.pdf` (the same file as the PDF in the root folder). `numbers.tex` and `t1.tex` to `t5.tex` are written by the scripts |

## Sources (all retrieved 11 November 2026)

1. S&P 500 Total Return Index, monthly closes: Yahoo Finance, ticker ^SP500TR, https://finance.yahoo.com/quote/^SP500TR/history/ (monthly frequency, column Close). Values are keyed into `code/01_build_inputs.py` as displayed on the page.
2. Swiss francs per US dollar, daily noon buying rates in New York: Board of Governors of the Federal Reserve System, H.10 release, FRED series DEXSZUS (last updated 9 November 2026), https://fred.stlouisfed.org/series/DEXSZUS. The daily file comes from the public mirror https://github.com/datasets/exchange-rates (file `data/daily.csv`, commit d33880bb of 10 November 2026) and was spot checked against FRED.
3. Three month interbank rates, monthly averages: OECD Main Economic Indicators via FRED, series IR3TIB01CHM156N (Switzerland) and IR3TIB01USM156N (United States), both last updated 15 October 2026. Text files: https://fred.stlouisfed.org/data/IR3TIB01CHM156N.txt and https://fred.stlouisfed.org/data/IR3TIB01USM156N.txt. Swiss values are stored truncated to four decimals. The US value for April 2020 is missing at source.

## How to reproduce

```
git clone https://github.com/datasets/exchange-rates mirror && git -C mirror checkout d33880bb076ce11576c4fe7e2ffd3bef904a98fe
python code/01_build_inputs.py data mirror/data/daily.csv     # rebuilds data/ (optional, data/ is included)
python code/02_analysis.py data out > out/log.txt             # all statistics (results.json and CSV files)
python code/03_charts.py out                                  # figures (needs XeLaTeX and the Inter typeface)
python code/04_numbers.py out note                            # numbers and tables for the note
cd note && xelatex note.tex && xelatex note.tex               # the PDF
```

Requires Python 3 with numpy, pandas and matplotlib, and XeLaTeX with the Inter and TeX Gyre Pagella typefaces for the figures and the PDF.

## Assumptions (modeling choices, not data)

* A1. Forward rates are rebuilt from covered interest parity with the two OECD rate series. No cross currency basis.
* A2. The monthly average three month rate of month t stands in for the one month rate at the end of month t. Accrual over one twelfth of a year.
* A3. The missing US rate for April 2020 is set to the average of March and May 2020 (0.76%).
* A4. No transaction costs, taxes or collateral costs. The index is gross of dividend withholding tax.

## Data note

The S&P 500 index levels in `data/sp500tr_monthly.csv` and in the output files were keyed in from Yahoo Finance for this analysis. Keep this repository private or remove them before making it public.
