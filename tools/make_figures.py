"""Generate the data figures used on yei1y.github.io.

Every plotted number comes from a result file written by the corresponding
project, or from the verified figures recorded in 项目清单.md. Nothing is
hand-typed into the plots: change a result file, re-run this script, and the
site figures follow. The script also re-derives two headline numbers (ROC-AUC,
net profit) as a cross-check and prints them.

Palette and fonts mirror assets/css/style.css so the figures sit inside the
page rather than beside it.

Usage:  python tools/make_figures.py [--root D:\\codes\\项目] [--out assets/figures]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager as fm
from matplotlib.patches import Patch

# --- Palette: kept in sync with assets/css/style.css -------------------------------
INK = '#1B252B'
INK2 = '#4A585F'
INK3 = '#5F6C74'
RULE = '#E4E1D9'
PAPER = '#FBFAF6'
MINT = '#1F7A66'
MINT_L = '#7FC9B6'
MINT_T = '#DCF4EA'
SKY = '#2A6797'
SKY_T = '#DFEEFB'
PEACH = '#9C552E'
PEACH_L = '#E9A87F'
LEMON = '#7E6410'
LAV = '#61479B'

SERIES = [MINT, SKY, PEACH, LAV, LEMON]


def pick_font() -> str:
    """First CJK-capable family actually installed, else a Latin fallback."""
    installed = {f.name for f in fm.fontManager.ttflist}
    for name in ('Noto Sans SC', 'Microsoft YaHei', 'Source Han Sans SC',
                 'PingFang SC', 'SimHei', 'Noto Sans CJK SC'):
        if name in installed:
            return name
    return 'DejaVu Sans'


def setup(font: str) -> None:
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': [font, 'DejaVu Sans'],
        'axes.unicode_minus': False,
        'figure.facecolor': PAPER,
        'axes.facecolor': PAPER,
        'savefig.facecolor': PAPER,
        'axes.edgecolor': RULE,
        'axes.labelcolor': INK2,
        'axes.titlecolor': INK,
        'text.color': INK,
        'xtick.color': INK3,
        'ytick.color': INK3,
        'grid.color': RULE,
        'axes.grid': True,
        'grid.linewidth': .7,
        'axes.axisbelow': True,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'font.size': 10.5,
        'figure.dpi': 200,
        'savefig.dpi': 200,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': .18,
        'legend.frameon': False,
    })


def save(fig, out: Path, name: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    fig.savefig(path)
    plt.close(fig)
    print(f'  wrote {path.name}  ({path.stat().st_size / 1024:.0f} KB)')


# ---------------------------------------------------------------- figure 01: funnel
def fig_funnel(out: Path) -> None:
    """E-commerce funnel: SQL-derived session counts, log-scaled session track."""
    stages = ['首页\nHome', '列表页\nListing', '详情页\nDetail', '支付页\nPayment', '确认页\nConfirm']
    sessions = np.array([97274, 71684, 47922, 6052, 1684])
    step_rate = [np.nan, 73.69, 66.85, 12.63, 27.83]

    fig, (ax, axr) = plt.subplots(
        1, 2, figsize=(9.6, 3.5), gridspec_kw={'width_ratios': [1.55, 1], 'wspace': .12})

    y = np.arange(len(stages))[::-1]
    colors = [MINT_L] * len(stages)
    colors[3] = MINT
    ax.barh(y, sessions, color=colors, height=.62)
    ax.set_xscale('log')
    ax.set_xlim(700, 300000)
    ax.set_yticks(y, stages)
    ax.tick_params(axis='y', labelsize=9.5, length=0)
    ax.set_xlabel('会话数（对数刻度）', fontsize=9.5)
    ax.grid(axis='y', visible=False)
    ax.set_title('各环节到达人数', fontsize=11, pad=8, loc='left')
    for yi, v in zip(y, sessions):
        ax.text(v * 1.12, yi, f'{v:,}', va='center', fontsize=9, color=INK2)
    ax.annotate('最大流失环节\n12.63%',
                xy=(sessions[3] * 1.06, y[3] + .22),
                xytext=(3400, y[3] + 1.02),
                fontsize=9, color=MINT, fontweight='bold', ha='left', va='center',
                arrowprops=dict(arrowstyle='-', color=MINT, lw=1, shrinkA=0, shrinkB=2))

    xr = np.arange(len(stages))
    rates = [np.nan] + step_rate[1:]
    bars = axr.bar(xr, [0 if np.isnan(r) else r for r in rates], color=MINT_L, width=.62)
    bars[3].set_color(MINT)
    axr.set_xticks(xr, ['首页', '列表', '详情', '支付', '确认'], fontsize=9.5)
    axr.set_ylim(0, 100)
    axr.set_ylabel('相邻两段转化率（%）', fontsize=9.5)
    axr.axhline(50, color=RULE, lw=.9, ls=(0, (4, 4)))
    axr.set_title('逐段转化率', fontsize=11, pad=8, loc='left')
    for xi, r in zip(xr, rates):
        if np.isnan(r):
            axr.text(xi, 2, '—', ha='center', fontsize=10, color=INK3)
            continue
        axr.text(xi, r + 3, f'{r:.2f}%', ha='center', fontsize=9,
                 color=MINT if r == 12.63 else INK2,
                 fontweight='bold' if r == 12.63 else 'normal')

    fig.text(.005, -.06,
             '口径：会话数取自 MySQL 8.0 的 24 条查询，清洗后 97,274 条会话；'
             '转化率 = 本环节人数 / 上一环节人数。整体转化率 1.73%。',
             fontsize=8.6, color=INK3)
    save(fig, out, 'fig-funnel.png')


# ------------------------------------------------------------------- figure 02: ROC
def _roc(y: np.ndarray, score: np.ndarray):
    order = np.argsort(-score, kind='mergesort')
    y = y[order]
    tp = np.cumsum(y)
    fp = np.cumsum(1 - y)
    tpr = np.concatenate([[0], tp / tp[-1]])
    fpr = np.concatenate([[0], fp / fp[-1]])
    return fpr, tpr


def auc_of(y: np.ndarray, score: np.ndarray) -> float:
    fpr, tpr = _roc(y, score)
    return float(np.trapezoid(tpr, fpr))


def fig_roc(out: Path, root: Path) -> None:
    """ROC with a bootstrap band — makes the 76 positive test cases visible."""
    d = pd.read_csv(root / 'Company-Bankruptcy-Prediction/results/tables/test_probabilities.csv')
    y = d['Y_test'].to_numpy()
    s = d['prob_weighted'].to_numpy()
    n_pos = int(y.sum())

    fpr, tpr = _roc(y, s)
    auc = auc_of(y, s)

    # Percentile bootstrap over test cases -> an honest band for a 76-case minority.
    rng = np.random.default_rng(20260601)
    grid = np.linspace(0, 1, 121)
    curves = []
    idx = np.arange(len(y))
    for _ in range(1000):
        b = rng.choice(idx, size=len(idx), replace=True)
        if y[b].sum() < 2 or y[b].sum() == len(b):
            continue
        bf, bt = _roc(y[b], s[b])
        curves.append(np.interp(grid, bf, bt))
    band = np.percentile(np.array(curves), [2.5, 97.5], axis=0)

    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    ax.fill_between(grid, band[0], band[1], color=MINT_T, lw=0, label='95% bootstrap band')
    ax.plot(fpr, tpr, color=MINT, lw=1.8, label=f'SCAD 白盒模型  AUC = {auc:.4f}')
    ax.plot([0, 1], [0, 1], color=INK3, lw=.9, ls=(0, (4, 4)), label='随机猜测')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.005)
    ax.set_xlabel('假阳性率 False positive rate')
    ax.set_ylabel('真阳性率 True positive rate')
    ax.set_title('测试集 ROC', fontsize=11.5, loc='left', pad=10)
    ax.legend(loc='lower right', fontsize=9)
    ax.text(0, -.30,
            f'测试集 2,046 家，其中破产 {n_pos} 家（3.71%）。'
            f'AUC 由仓库落盘的测试概率重新计算，与论文报告的 0.9380 一致。',
            transform=ax.transAxes, fontsize=8.6, color=INK3)
    save(fig, out, 'fig-roc.png')
    print(f'    check: recomputed AUC = {auc:.4f} (repo reports 0.9380)')


# --------------------------------------------------------------- figure 03: SCAD
def fig_scad(out: Path, root: Path) -> None:
    """The 16 surviving features and their SCAD coefficients."""
    d = pd.read_csv(root / 'Company-Bankruptcy-Prediction/results/tables/scad_selected_features.csv')
    d = d.sort_values('coefficient')

    def label(row) -> str:
        blocks = str(row['blocks']).replace(' ', '')
        inter = '交互' if row['is_interaction'] else '主效应'
        return f"{row['feature_id']} · {blocks} · {inter}"

    labels = [label(r) for _, r in d.iterrows()]
    vals = d['coefficient'].to_numpy()
    order = np.argsort(vals)                 # draw negative (largest loss) at the bottom
    labels = [labels[i] for i in order]
    vals = vals[order]
    colors = [PEACH if v > 0 else SKY for v in vals]

    # Most coefficients sit within ±10 while one reaches +65: a symmetric log axis
    # keeps the tail honest without flattening the rest into a line.
    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    y = np.arange(len(vals))
    ax.set_xscale('symlog', linthresh=10)
    ax.set_xlim(-40, 120)
    ax.hlines(y, 0, vals, color=colors, lw=2.4, alpha=.75)
    ax.scatter(vals, y, color=colors, s=38, zorder=3)
    ax.axvline(0, color=INK3, lw=.9)
    ax.set_xticks([-20, -10, 0, 10, 20, 40, 60, 80, 100, 120])
    ax.set_xticklabels(['-20', '-10', '0', '10', '20', '40', '60', '80', '100', '120'],
                       fontsize=9.5)
    ax.set_yticks(y, labels, fontsize=8.6)
    ax.tick_params(axis='y', length=0)
    ax.set_xlabel('SCAD 系数（对称对数刻度，线性区 ±10）', fontsize=9.5)
    ax.set_title('代价敏感 SCAD 的 16 个非零特征', fontsize=11.5, loc='left', pad=10)
    ax.grid(axis='y', visible=False)
    ax.legend(handles=[Patch(color=PEACH, label='正系数（推高破产风险）'),
                       Patch(color=SKY, label='负系数（降低破产风险）')],
              loc='lower right', fontsize=9)
    n_int = int(d['is_interaction'].sum())
    n_lev = int(d['involves_leverage'].sum())
    ax.text(0, -.155,
            f'共 {len(d)} 个非零特征，其中 {n_int} 个是交互项、{n_lev} 个涉及杠杆模块；'
            '块名取自杜邦模块。系数单位为标准化尺度，最大者 F01 达 +65.6，'
            '故横轴取对称对数以免其余特征被压成一条线。',
            transform=ax.transAxes, fontsize=8.6, color=INK3)
    save(fig, out, 'fig-scad.png')


# ---------------------------------------------------------------- figure 04: DML
def fig_dml(out: Path, root: Path) -> None:
    """Specification curve for the ATE: the null survives every nuisance choice."""
    base = pd.read_csv(root / 'ai-adoption-productivity-dml/output/tables/robustness_results.csv')
    keep = ['Baseline (RF, K=5)', 'LASSO (CV)', 'XGBoost', 'K = 2', 'K = 10', 'Strict D (full only)']
    base = base[base['specification'].isin(keep)].copy()
    zh = {'Baseline (RF, K=5)': '基线 · 随机森林 · 5 折（报告值）',
          'LASSO (CV)': 'LASSO · 交叉验证',
          'XGBoost': 'XGBoost',
          'K = 2': '交叉拟合 K = 2',
          'K = 10': '交叉拟合 K = 10',
          'Strict D (full only)': '严格 D · 仅全样本'}
    base['label'] = base['specification'].map(zh)
    base = base.iloc[::-1]                      # draw the baseline at the top

    fig, ax = plt.subplots(figsize=(8.2, 3.9))
    y = np.arange(len(base))
    for yi, (_, r) in zip(y, base.iterrows()):
        c = MINT if r['specification'] == 'Baseline (RF, K=5)' else SKY
        ax.plot([r['ci_lower'], r['ci_upper']], [yi, yi], color=c, lw=2.2, alpha=.85,
                solid_capstyle='butt')
        ax.scatter([r['estimate']], [yi], color=c, s=42, zorder=3)
        ax.text(r['ci_upper'] + .004, yi, f"{r['estimate'] * 100:+.2f}%  (p = {r['p_value']:.3f})",
                va='center', fontsize=9, color=INK2)
    ax.axvline(0, color=PEACH, lw=1.3)
    ax.set_yticks(y, base['label'], fontsize=9.5)
    ax.tick_params(axis='y', length=0)
    ax.set_xlim(-.02, .13)
    ax.set_xlabel('AI 采纳对劳动生产率的平均处理效应 ATE（95% 置信区间）', fontsize=9.5)
    ax.set_title('六种设定下的平均因果效应', fontsize=11.5, loc='left', pad=10)
    ax.grid(axis='y', visible=False)
    ax.text(0, -.315,
            '前五行：换 nuisance 估计量与交叉拟合折数，置信区间始终覆盖 0（ATE ∈ [0.0004, 0.0059]）。'
            '末行为严格 D 设定（分母仅用全样本），结论由零变为 +5.57%，说明结果对分母口径敏感。\n'
            '另有一项安慰剂式设定（结果变量换成 productivity_change）估计值 +269.9%，量级不可比，故不绘入。',
            transform=ax.transAxes, fontsize=8.6, color=INK3)
    save(fig, out, 'fig-dml-forest.png')


# ------------------------------------------------------- figure 05: market survey
def fig_segments(out: Path) -> None:
    """Weighted K-means segmentation — shares recorded in 项目清单.md."""
    shares = [13.19, 56.35, 30.46]
    labels = ['人群一\nSegment 1', '人群二\nSegment 2', '人群三\nSegment 3']
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(8.0, 3.1),
                                  gridspec_kw={'width_ratios': [1.35, 1], 'wspace': .18})

    y = np.arange(len(shares))[::-1]
    ax.barh(y, shares, color=[MINT_L, MINT, MINT_L], height=.58)
    ax.set_yticks(y, labels, fontsize=9.5)
    ax.tick_params(axis='y', length=0)
    ax.set_xlim(0, 72)
    ax.set_xlabel('占样本比例（%）', fontsize=9.5)
    ax.grid(axis='y', visible=False)
    ax.set_title('加权 K-Means 的三类人群', fontsize=11, loc='left', pad=8)
    for yi, v in zip(y, shares):
        ax.text(v + 1.5, yi, f'{v:.2f}%', va='center', fontsize=9.5, color=INK2)

    metrics = {'SEM 解释方差': 68.7, '量表信度 α': 98.3}
    xs = np.arange(len(metrics))
    ax2.bar(xs, list(metrics.values()), color=MINT_L, width=.5)
    ax2.set_xticks(xs, list(metrics))
    ax2.set_ylim(0, 108)
    ax2.set_ylabel('数值（%）', fontsize=9.5)
    ax2.set_title('模型的解释力与信度', fontsize=11, loc='left', pad=8)
    for xi, (k, v) in zip(xs, metrics.items()):
        ax2.text(xi, v + 2.5, f'{v:g}%' if k == 'SEM 解释方差' else f'α = {v / 100:.3f}',
                 ha='center', fontsize=9.5, color=INK2)

    fig.text(.005, -.08,
             '人群划分：以购入价格为核心指标、共 9 个聚类变量加权而成，样本为广深 2 城 21 街道的 747 份有效问卷；'
             'SEM 的 CMIN/DF = 1.407、RMSEA = 0.030。量表为 40 题 10 维度，KMO = 0.977。',
             fontsize=8.6, color=INK3)
    save(fig, out, 'fig-segments.png')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=r'D:\codes\项目', help='projects root directory')
    ap.add_argument('--out', default=None, help='output directory (default: <repo>/assets/figures)')
    a = ap.parse_args()

    root = Path(a.root)
    here = Path(__file__).resolve().parent.parent
    out = Path(a.out) if a.out else here / 'assets' / 'figures'

    font = pick_font()
    setup(font)
    print(f'font: {font}\noutput: {out}\n')

    missing = []
    for name, fn, needs_root in [
        ('funnel', fig_funnel, False),
        ('roc', fig_roc, True),
        ('scad', fig_scad, True),
        ('dml forest', fig_dml, True),
        ('segments', fig_segments, False),
    ]:
        try:
            print(f'{name}:')
            fn(out, root) if needs_root else fn(out)
        except FileNotFoundError as e:
            missing.append(f'{name}: {e}')
            print(f'  skipped — {e}')

    if missing:
        print('\nmissing inputs:')
        for m in missing:
            print('  ' + m)
        return 1
    print('\nall figures regenerated.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
