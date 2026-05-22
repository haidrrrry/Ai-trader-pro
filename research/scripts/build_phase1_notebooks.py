#!/usr/bin/env python3
"""Generate Phase 1 research notebooks."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def save_notebook(cells: list[dict], path: Path) -> None:
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "cells": cells,
    }
    try:
        import nbformat

        nb = nbformat.from_dict(nb)
        nbformat.validate(nb)
        path.write_text(nbformat.writes(nb), encoding="utf-8")
    except Exception:
        path.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print(f"wrote {path}")


def build_backtesting_engine() -> list[dict]:
    return [
        md(
            "# Agent Backtesting Engine\n\n"
            "**AI Trader Pro — Walk-Forward Backtesting with vectorbt**\n\n"
            "Pipeline:\n"
            "1. Load market data (yfinance)\n"
            "2. Generate RSI signals\n"
            "3. Backtest with vectorbt\n"
            "4. Compute risk metrics\n"
            "5. Walk-forward validation\n"
            "6. Parameter optimization\n"
            "7. Export figures to `research/figures/`"
        ),
        md("## 1. Setup"),
        code(
            "%matplotlib inline\n\n"
            "from __future__ import annotations\n\n"
            "import warnings\n"
            "from pathlib import Path\n\n"
            "import matplotlib.pyplot as plt\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import plotly.graph_objects as go\n"
            "import plotly.express as px\n"
            "import seaborn as sns\n"
            "import yfinance as yf\n\n"
            "try:\n"
            "    import vectorbt as vbt\n"
            "except ImportError as exc:\n"
            "    raise ImportError(\n"
            "        'Install research deps: pip install -r research/requirements.txt'\n"
            "    ) from exc\n\n"
            "warnings.filterwarnings('ignore', category=FutureWarning)\n\n"
            "plt.style.use('seaborn-v0_8-darkgrid')\n"
            "FIGURES_DIR = Path('figures')\n"
            "FIGURES_DIR.mkdir(parents=True, exist_ok=True)\n\n"
            "TRADING_DAYS = 252\n"
            "RISK_FREE_RATE = 0.04  # annual\n"
            "SEED = 42\n"
            "np.random.seed(SEED)\n\n"
            "print(f'pandas {pd.__version__} | vectorbt {vbt.__version__}')"
        ),
        md("## 2. Load Market Data"),
        code(
            "SYMBOL = 'SPY'\n"
            "START = '2018-01-01'\n"
            "END = '2024-12-31'\n\n"
            "raw = yf.download(SYMBOL, start=START, end=END, auto_adjust=True, progress=False)\n"
            "if isinstance(raw.columns, pd.MultiIndex):\n"
            "    raw.columns = raw.columns.get_level_values(0)\n\n"
            "close = raw['Close'].dropna().astype(float)\n"
            "returns = close.pct_change().dropna()\n\n"
            "print(f'{SYMBOL}: {len(close)} bars | {close.index[0].date()} → {close.index[-1].date()}')\n"
            "close.tail()"
        ),
        md("## 3. Strategy Signals (RSI Mean-Reversion)"),
        code(
            "def rsi_signals(close: pd.Series, window: int = 14, lower: float = 30, upper: float = 70) -> tuple[pd.Series, pd.Series]:\n"
            "    rsi = vbt.RSI.run(close, window=window).rsi\n"
            "    entries = rsi < lower\n"
            "    exits = rsi > upper\n"
            "    return entries.fillna(False), exits.fillna(False)\n\n"
            "entries, exits = rsi_signals(close, window=14, lower=30, upper=70)\n"
            "print(f'Entry signals: {int(entries.sum())} | Exit signals: {int(exits.sum())}')"
        ),
        md("## 4. vectorbt Backtest"),
        code(
            "pf = vbt.Portfolio.from_signals(\n"
            "    close,\n"
            "    entries=entries,\n"
            "    exits=exits,\n"
            "    init_cash=100_000,\n"
            "    fees=0.001,\n"
            "    freq='1D',\n"
            ")\n\n"
            "equity = pf.value()\n"
            "trade_returns = pf.trades.returns.values if pf.trades.count() else np.array([])\n"
            "daily_returns = pf.returns().dropna()\n\n"
            "summary = pf.stats()\n"
            "print(summary[['Start', 'End', 'Total Return [%]', 'Max Drawdown [%]', 'Sharpe Ratio', 'Win Rate [%]', 'Total Trades']])"
        ),
        md("## 5. Performance Metrics"),
        code(
            "def max_drawdown(equity_curve: pd.Series) -> float:\n"
            "    peak = equity_curve.cummax()\n"
            "    dd = (equity_curve - peak) / peak\n"
            "    return float(dd.min())\n\n"
            "def sharpe_ratio(daily_rets: pd.Series, rf: float = RISK_FREE_RATE) -> float:\n"
            "    excess = daily_rets - rf / TRADING_DAYS\n"
            "    if excess.std() == 0:\n"
            "        return 0.0\n"
            "    return float(np.sqrt(TRADING_DAYS) * excess.mean() / excess.std())\n\n"
            "def sortino_ratio(daily_rets: pd.Series, rf: float = RISK_FREE_RATE) -> float:\n"
            "    excess = daily_rets - rf / TRADING_DAYS\n"
            "    downside = excess[excess < 0]\n"
            "    if len(downside) == 0 or downside.std() == 0:\n"
            "        return 0.0\n"
            "    return float(np.sqrt(TRADING_DAYS) * excess.mean() / downside.std())\n\n"
            "def profit_factor(trade_rets: np.ndarray) -> float:\n"
            "    if trade_rets.size == 0:\n"
            "        return 0.0\n"
            "    gains = trade_rets[trade_rets > 0].sum()\n"
            "    losses = abs(trade_rets[trade_rets < 0].sum())\n"
            "    return float(gains / losses) if losses > 0 else float('inf')\n\n"
            "def win_rate(trade_rets: np.ndarray) -> float:\n"
            "    if trade_rets.size == 0:\n"
            "        return 0.0\n"
            "    return float((trade_rets > 0).mean())\n\n"
            "def expectancy(trade_rets: np.ndarray) -> float:\n"
            "    if trade_rets.size == 0:\n"
            "        return 0.0\n"
            "    return float(trade_rets.mean())\n\n"
            "def calmar_ratio(daily_rets: pd.Series, equity_curve: pd.Series) -> float:\n"
            "    ann_return = (1 + daily_rets.mean()) ** TRADING_DAYS - 1\n"
            "    mdd = abs(max_drawdown(equity_curve))\n"
            "    return float(ann_return / mdd) if mdd > 0 else 0.0\n\n"
            "metrics = {\n"
            "    'Sharpe': sharpe_ratio(daily_returns),\n"
            "    'Sortino': sortino_ratio(daily_returns),\n"
            "    'Calmar': calmar_ratio(daily_returns, equity),\n"
            "    'Max Drawdown': max_drawdown(equity),\n"
            "    'Profit Factor': profit_factor(trade_returns),\n"
            "    'Win Rate': win_rate(trade_returns),\n"
            "    'Expectancy': expectancy(trade_returns),\n"
            "    'Total Return': float(equity.iloc[-1] / equity.iloc[0] - 1),\n"
            "    'Trades': int(pf.trades.count()),\n"
            "}\n\n"
            "metrics_df = pd.DataFrame([metrics]).T\n"
            "metrics_df.columns = ['Value']\n"
            "metrics_df.style.format('{:.4f}')"
        ),
        md("## 6. Walk-Forward Optimization"),
        code(
            "def walk_forward_backtest(\n"
            "    close: pd.Series,\n"
            "    train_bars: int = 504,\n"
            "    test_bars: int = 126,\n"
            "    window: int = 14,\n"
            "    lower: float = 30,\n"
            "    upper: float = 70,\n"
            ") -> pd.DataFrame:\n"
            "    rows = []\n"
            "    start = 0\n"
            "    fold = 0\n"
            "    while start + train_bars + test_bars <= len(close):\n"
            "        train_slice = close.iloc[start : start + train_bars]\n"
            "        test_slice = close.iloc[start + train_bars : start + train_bars + test_bars]\n"
            "        ent, ex = rsi_signals(test_slice, window=window, lower=lower, upper=upper)\n"
            "        fold_pf = vbt.Portfolio.from_signals(\n"
            "            test_slice, entries=ent, exits=ex, init_cash=100_000, fees=0.001, freq='1D'\n"
            "        )\n"
            "        fold_eq = fold_pf.value()\n"
            "        fold_rets = fold_pf.returns().dropna()\n"
            "        fold_trades = fold_pf.trades.returns.values if fold_pf.trades.count() else np.array([])\n"
            "        rows.append(\n"
            "            {\n"
            "                'fold': fold,\n"
            "                'test_start': test_slice.index[0].date(),\n"
            "                'test_end': test_slice.index[-1].date(),\n"
            "                'total_return': float(fold_eq.iloc[-1] / fold_eq.iloc[0] - 1),\n"
            "                'sharpe': sharpe_ratio(fold_rets),\n"
            "                'max_drawdown': max_drawdown(fold_eq),\n"
            "                'win_rate': win_rate(fold_trades),\n"
            "                'trades': int(fold_pf.trades.count()),\n"
            "            }\n"
            "        )\n"
            "        start += test_bars\n"
            "        fold += 1\n"
            "    return pd.DataFrame(rows)\n\n"
            "wf_results = walk_forward_backtest(close)\n"
            "print(f'Walk-forward folds: {len(wf_results)}')\n"
            "wf_results"
        ),
        md("## 7. Parameter Optimization (Grid Search)"),
        code(
            "def optimize_rsi_params(\n"
            "    close: pd.Series,\n"
            "    windows: list[int] | None = None,\n"
            "    lowers: list[float] | None = None,\n"
            "    uppers: list[float] | None = None,\n"
            ") -> pd.DataFrame:\n"
            "    windows = windows or [10, 14, 20, 28]\n"
            "    lowers = lowers or [25, 30, 35]\n"
            "    uppers = uppers or [65, 70, 75]\n"
            "    rows = []\n"
            "    for w in windows:\n"
            "        for lo in lowers:\n"
            "            for hi in uppers:\n"
            "                if lo >= hi:\n"
            "                    continue\n"
            "                ent, ex = rsi_signals(close, window=w, lower=lo, upper=hi)\n"
            "                opt_pf = vbt.Portfolio.from_signals(\n"
            "                    close, entries=ent, exits=ex, init_cash=100_000, fees=0.001, freq='1D'\n"
            "                )\n"
            "                opt_eq = opt_pf.value()\n"
            "                opt_rets = opt_pf.returns().dropna()\n"
            "                opt_trades = opt_pf.trades.returns.values if opt_pf.trades.count() else np.array([])\n"
            "                rows.append(\n"
            "                    {\n"
            "                        'window': w,\n"
            "                        'lower': lo,\n"
            "                        'upper': hi,\n"
            "                        'sharpe': sharpe_ratio(opt_rets),\n"
            "                        'sortino': sortino_ratio(opt_rets),\n"
            "                        'max_drawdown': max_drawdown(opt_eq),\n"
            "                        'total_return': float(opt_eq.iloc[-1] / opt_eq.iloc[0] - 1),\n"
            "                        'win_rate': win_rate(opt_trades),\n"
            "                        'profit_factor': profit_factor(opt_trades),\n"
            "                        'trades': int(opt_pf.trades.count()),\n"
            "                    }\n"
            "                )\n"
            "    return pd.DataFrame(rows).sort_values('sharpe', ascending=False)\n\n"
            "param_grid = optimize_rsi_params(close.iloc[-756:])  # last ~3 years for speed\n"
            "best = param_grid.iloc[0]\n"
            "print('Best params (by Sharpe):')\n"
            "print(best[['window', 'lower', 'upper', 'sharpe', 'total_return', 'max_drawdown', 'trades']])\n"
            "param_grid.head(10)"
        ),
        md("## 8. Visualizations"),
        code(
            "fig, axes = plt.subplots(2, 2, figsize=(14, 10))\n\n"
            "# Equity curve\n"
            "axes[0, 0].plot(equity.index, equity.values, color='#d4a458', linewidth=1.5)\n"
            "axes[0, 0].set_title('Equity Curve')\n"
            "axes[0, 0].set_ylabel('Portfolio Value ($)')\n\n"
            "# Drawdown\n"
            "peak = equity.cummax()\n"
            "dd = (equity - peak) / peak\n"
            "axes[0, 1].fill_between(dd.index, dd.values, 0, color='#e74c3c', alpha=0.6)\n"
            "axes[0, 1].set_title('Drawdown')\n"
            "axes[0, 1].set_ylabel('Drawdown')\n\n"
            "# Monthly returns heatmap\n"
            "monthly = daily_returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)\n"
            "monthly_df = monthly.to_frame('return')\n"
            "monthly_df['year'] = monthly_df.index.year\n"
            "monthly_df['month'] = monthly_df.index.month\n"
            "pivot = monthly_df.pivot(index='year', columns='month', values='return')\n"
            "sns.heatmap(pivot, annot=True, fmt='.1%', cmap='RdYlGn', center=0, ax=axes[1, 0], cbar_kws={'label': 'Return'})\n"
            "axes[1, 0].set_title('Monthly Returns Heatmap')\n\n"
            "# Trade return distribution\n"
            "if trade_returns.size:\n"
            "    axes[1, 1].hist(trade_returns, bins=20, color='#3498db', edgecolor='white', alpha=0.85)\n"
            "    axes[1, 1].axvline(0, color='black', linestyle='--', linewidth=1)\n"
            "axes[1, 1].set_title('Trade Return Distribution')\n"
            "axes[1, 1].set_xlabel('Trade Return')\n\n"
            "plt.tight_layout()\n"
            "equity_path = FIGURES_DIR / 'backtest_equity_drawdown.png'\n"
            "plt.savefig(equity_path, dpi=150, bbox_inches='tight')\n"
            "plt.show()\n"
            "print(f'Saved {equity_path}')"
        ),
        code(
            "# Parameter optimization surface (Sharpe vs RSI window & lower threshold)\n"
            "surface = param_grid.pivot_table(index='lower', columns='window', values='sharpe', aggfunc='mean')\n"
            "fig = px.imshow(\n"
            "    surface,\n"
            "    labels=dict(x='RSI Window', y='Lower Threshold', color='Sharpe'),\n"
            "    title='Parameter Optimization — Sharpe Ratio Surface',\n"
            "    color_continuous_scale='Viridis',\n"
            "    aspect='auto',\n"
            ")\n"
            "surface_path = FIGURES_DIR / 'backtest_param_surface.html'\n"
            "fig.write_html(surface_path)\n"
            "fig.show()\n"
            "print(f'Saved {surface_path}')"
        ),
        code(
            "# Walk-forward fold performance\n"
            "if not wf_results.empty:\n"
            "    fig, ax = plt.subplots(figsize=(12, 4))\n"
            "    ax.bar(wf_results['fold'].astype(str), wf_results['total_return'], color='#2ecc71', alpha=0.85)\n"
            "    ax.axhline(0, color='black', linewidth=0.8)\n"
            "    ax.set_xlabel('Fold')\n"
            "    ax.set_ylabel('Test Return')\n"
            "    ax.set_title('Walk-Forward Out-of-Sample Returns')\n"
            "    wf_path = FIGURES_DIR / 'backtest_walk_forward.png'\n"
            "    plt.savefig(wf_path, dpi=150, bbox_inches='tight')\n"
            "    plt.show()\n"
            "    print(f'Saved {wf_path}')"
        ),
        md("## 9. Summary"),
        code(
            "print('=' * 60)\n"
            "print('BACKTEST SUMMARY')\n"
            "print('=' * 60)\n"
            "for k, v in metrics.items():\n"
            "    if isinstance(v, float):\n"
            "        print(f'  {k:18s}: {v:>10.4f}')\n"
            "    else:\n"
            "        print(f'  {k:18s}: {v:>10}')\n"
            "if not wf_results.empty:\n"
            "    print(f\"\\nWalk-forward avg Sharpe : {wf_results['sharpe'].mean():.4f}\")\n"
            "    print(f\"Walk-forward avg return: {wf_results['total_return'].mean():.2%}\")\n"
            "print(f\"\\nBest RSI params       : window={int(best['window'])}, lower={int(best['lower'])}, upper={int(best['upper'])}\")\n"
            "print(f\"Best in-sample Sharpe  : {best['sharpe']:.4f}\")"
        ),
    ]


def build_multi_agent_notebook() -> list[dict]:
    return [
        md(
            "# Multi-Agent Collaboration Experiments\n\n"
            "**AI Trader Pro — Light copy-trade simulation**\n\n"
            "Simple experiment:\n"
            "- 5 synthetic agents with different return profiles\n"
            "- 1 leader, 3 followers with copy lag\n"
            "- Compare solo vs copy-trade performance\n"
            "- Correlation matrix + bar chart"
        ),
        md("## 1. Setup"),
        code(
            "%matplotlib inline\n\n"
            "from __future__ import annotations\n\n"
            "from pathlib import Path\n\n"
            "import matplotlib.pyplot as plt\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import seaborn as sns\n\n"
            "FIGURES_DIR = Path('figures')\n"
            "FIGURES_DIR.mkdir(parents=True, exist_ok=True)\n\n"
            "TRADING_DAYS = 252\n"
            "SEED = 42\n"
            "rng = np.random.default_rng(SEED)\n\n"
            "plt.style.use('seaborn-v0_8-darkgrid')\n"
            "print('Setup complete.')"
        ),
        md("## 2. Simulate Agent Returns"),
        code(
            "agents = {\n"
            "    'MomentumBot': {'mu': 0.0008, 'sigma': 0.012, 'style': 'trend'},\n"
            "    'MeanReversionAgent': {'mu': 0.0004, 'sigma': 0.008, 'style': 'mean-rev'},\n"
            "    'SentimentTrader': {'mu': 0.0003, 'sigma': 0.018, 'style': 'sentiment'},\n"
            "    'RiskParityAI': {'mu': 0.0005, 'sigma': 0.006, 'style': 'risk-parity'},\n"
            "    'AggressiveAlpha': {'mu': 0.0010, 'sigma': 0.022, 'style': 'aggressive'},\n"
            "}\n\n"
            "dates = pd.bdate_range('2024-01-01', periods=TRADING_DAYS)\n"
            "returns = pd.DataFrame(index=dates)\n\n"
            "for name, params in agents.items():\n"
            "    returns[name] = rng.normal(params['mu'], params['sigma'], TRADING_DAYS)\n\n"
            "returns.head()"
        ),
        md("## 3. Copy-Trade Simulation"),
        code(
            "LEADER = 'MomentumBot'\n"
            "FOLLOWERS = ['MeanReversionAgent', 'SentimentTrader', 'RiskParityAI']\n"
            "COPY_LAG = 1          # days delay before follower mirrors leader\n"
            "COPY_WEIGHT = 0.6     # fraction of leader signal copied\n"
            "NOISE = 0.003         # follower execution noise\n\n"
            "adjusted = returns.copy()\n"
            "leader_signal = returns[LEADER].shift(COPY_LAG).fillna(0)\n\n"
            "for follower in FOLLOWERS:\n"
            "    own = returns[follower]\n"
            "    copied = COPY_WEIGHT * leader_signal + (1 - COPY_WEIGHT) * own\n"
            "    copied += rng.normal(0, NOISE, TRADING_DAYS)\n"
            "    adjusted[f'{follower}_copy'] = copied\n"
            "    adjusted[f'{follower}_solo'] = own\n\n"
            "print(f'Leader: {LEADER} | Followers: {FOLLOWERS}')\n"
            "adjusted.filter(like='_copy').head()"
        ),
        md("## 4. Performance Comparison"),
        code(
            "def quick_metrics(daily_rets: pd.Series) -> dict[str, float]:\n"
            "    equity = (1 + daily_rets).cumprod()\n"
            "    peak = equity.cummax()\n"
            "    dd = (equity - peak) / peak\n"
            "    sharpe = np.sqrt(TRADING_DAYS) * daily_rets.mean() / daily_rets.std() if daily_rets.std() else 0\n"
            "    return {\n"
            "        'total_return': float(equity.iloc[-1] - 1),\n"
            "        'sharpe': float(sharpe),\n"
            "        'max_drawdown': float(dd.min()),\n"
            "        'volatility': float(daily_rets.std() * np.sqrt(TRADING_DAYS)),\n"
            "    }\n\n"
            "rows = []\n"
            "for col in adjusted.columns:\n"
            "    m = quick_metrics(adjusted[col])\n"
            "    m['agent'] = col\n"
            "    rows.append(m)\n\n"
            "perf = pd.DataFrame(rows).set_index('agent')\n"
            "perf.style.format({'total_return': '{:.2%}', 'sharpe': '{:.3f}', 'max_drawdown': '{:.2%}', 'volatility': '{:.2%}'})"
        ),
        md("## 5. Solo vs Copy-Trade"),
        code(
            "comparison_rows = []\n"
            "for follower in FOLLOWERS:\n"
            "    solo = perf.loc[f'{follower}_solo']\n"
            "    copy = perf.loc[f'{follower}_copy']\n"
            "    comparison_rows.append(\n"
            "        {\n"
            "            'follower': follower,\n"
            "            'solo_sharpe': solo['sharpe'],\n"
            "            'copy_sharpe': copy['sharpe'],\n"
            "            'sharpe_delta': copy['sharpe'] - solo['sharpe'],\n"
            "            'solo_return': solo['total_return'],\n"
            "            'copy_return': copy['total_return'],\n"
            "        }\n"
            "    )\n\n"
            "comparison = pd.DataFrame(comparison_rows)\n"
            "comparison.style.format(\n"
            "    {\n"
            "        'solo_sharpe': '{:.3f}',\n"
            "        'copy_sharpe': '{:.3f}',\n"
            "        'sharpe_delta': '{:+.3f}',\n"
            "        'solo_return': '{:.2%}',\n"
            "        'copy_return': '{:.2%}',\n"
            "    }\n"
            ")"
        ),
        md("## 6. Correlation & Visualizations"),
        code(
            "corr = returns.corr()\n\n"
            "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n\n"
            "sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0, ax=axes[0])\n"
            "axes[0].set_title('Agent Return Correlation (Solo)')\n\n"
            "x = np.arange(len(comparison))\n"
            "width = 0.35\n"
            "axes[1].bar(x - width / 2, comparison['solo_sharpe'], width, label='Solo', color='#3498db')\n"
            "axes[1].bar(x + width / 2, comparison['copy_sharpe'], width, label='Copy-Trade', color='#d4a458')\n"
            "axes[1].set_xticks(x)\n"
            "axes[1].set_xticklabels([f.split('Agent')[0] for f in FOLLOWERS], rotation=15)\n"
            "axes[1].set_ylabel('Sharpe Ratio')\n"
            "axes[1].set_title('Solo vs Copy-Trade Sharpe')\n"
            "axes[1].legend()\n\n"
            "plt.tight_layout()\n"
            "collab_path = FIGURES_DIR / 'multi_agent_collaboration.png'\n"
            "plt.savefig(collab_path, dpi=150, bbox_inches='tight')\n"
            "plt.show()\n"
            "print(f'Saved {collab_path}')"
        ),
        md("## 7. Conclusions"),
        code(
            "improved = comparison[comparison['sharpe_delta'] > 0]\n"
            "worse = comparison[comparison['sharpe_delta'] <= 0]\n\n"
            "print('=' * 55)\n"
            "print('MULTI-AGENT COLLABORATION — SUMMARY')\n"
            "print('=' * 55)\n"
            "print(f'Leader agent          : {LEADER}')\n"
            "print(f'Followers tested      : {len(FOLLOWERS)}')\n"
            "print(f'Copy improved Sharpe  : {len(improved)} / {len(FOLLOWERS)} followers')\n"
            "if not improved.empty:\n"
            "    best = improved.loc[improved['sharpe_delta'].idxmax()]\n"
            "    print(f'Best follower gain    : {best[\"follower\"]} ({best[\"sharpe_delta\"]:+.3f} Sharpe)')\n"
            "print(f'\\nAvg solo Sharpe       : {comparison[\"solo_sharpe\"].mean():.3f}')\n"
            "print(f'Avg copy Sharpe       : {comparison[\"copy_sharpe\"].mean():.3f}')\n"
            "print(f'\\nInterpretation: copy-trading helps when leader alpha > follower noise.')\n"
            "print(f'High correlation ({float(corr[LEADER].drop(LEADER, errors=\"ignore\").mean()):.2f} avg) → limited diversification benefit.')"
        ),
    ]


def main() -> None:
    save_notebook(build_backtesting_engine(), ROOT / "Agent_Backtesting_Engine.ipynb")
    save_notebook(build_multi_agent_notebook(), ROOT / "Multi_Agent_Collaboration_Experiments.ipynb")


if __name__ == "__main__":
    main()
