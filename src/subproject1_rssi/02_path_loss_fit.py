"""
02_path_loss_fit.py —— 对数距离路径损耗模型拟合

模型：
    RSSI(d) = A - 10 * n * log10(d / d0),   d0 = 1 m

参数含义：
    A : 1m 参考距离处的 RSSI（dBm），反映发射功率与天线增益
    n : 路径损耗指数（自由空间≈2，室内≈3~4），越大衰减越快

拟合方法（两种，结果对比）：
    1) 线性化最小二乘：令 x = log10(d), y = RSSI -> y = A - 10*n*x
       用 np.polyfit 做一元线性回归，斜率 m = -10*n，截距 b = A
    2) 非线性最小二乘：scipy.optimize.curve_fit 直接拟合非线性模型

输出：
    - 拟合参数 A, n 及置信区间
    - 决定系数 R^2、RMSE
    - 距离估计函数 estimate_distance(rssi)
    - 图表：散点 + 拟合曲线 + 残差图 -> results/path_loss_fit.png
"""

import csv
import os
import sys

import numpy as np
from scipy import optimize
import matplotlib
matplotlib.use("Agg")  # 无显示环境使用非交互后端
import matplotlib.pyplot as plt

# 项目根目录定位（脚本在 src/subproject1_rssi/ 下）
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))


def load_data(csv_path):
    """读取 RSSI 采集 CSV，返回 (distances, rssi_means, rssi_all)。"""
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    dists = np.array([float(r["distance_m"]) for r in rows])
    rssis = np.array([float(r["rssi_dbm"]) for r in rows])

    # 每个距离位置取中位数（抗离群点）作为该位置的代表值
    unique_d = np.unique(dists)
    means = np.array([np.median(rssis[dists == d]) for d in unique_d])
    return unique_d, means, rssis


def path_loss_model(d, A, n, d0=1.0):
    """对数距离路径损耗模型。d0=1m 为参考距离。"""
    # 避免 log10(0)；距离应 > 0
    d = np.maximum(d, 1e-6)
    return A - 10.0 * n * np.log10(d / d0)


def fit_linear(d, rssi):
    """线性化最小二乘拟合：y = A - 10*n*log10(d)。"""
    x = np.log10(d)
    # polyfit: y = slope*x + intercept  => slope = -10*n, intercept = A
    slope, intercept = np.polyfit(x, rssi, 1)
    n = -slope / 10.0
    A = intercept
    return A, n


def fit_curve(d, rssi):
    """非线性最小二乘拟合（curve_fit），可同时给出参数不确定度。"""
    popt, pcov = optimize.curve_fit(path_loss_model, d, rssi, p0=[-40.0, 3.0])
    A, n = popt
    perr = np.sqrt(np.diag(pcov))  # 参数标准误差
    return A, n, perr


def estimate_distance(rssi, A, n, d0=1.0):
    """由 RSSI 反推距离：d = d0 * 10^((A - RSSI) / (10*n))。"""
    return d0 * 10.0 ** ((A - rssi) / (10.0 * n))


def evaluate_fit(d, rssi, A, n):
    """计算拟合优度指标。"""
    pred = path_loss_model(d, A, n)
    ss_res = np.sum((rssi - pred) ** 2)
    ss_tot = np.sum((rssi - np.mean(rssi)) ** 2)
    r_squared = 1.0 - ss_res / ss_tot
    rmse = np.sqrt(np.mean((rssi - pred) ** 2))
    mae = np.mean(np.abs(rssi - pred))
    return r_squared, rmse, mae


def plot_fit(d, rssi, rssis_all, A, n, out_path):
    """绘制散点、拟合曲线、残差图。"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 左图：散点 + 拟合曲线
    ax = axes[0]
    ax.scatter(d, rssi, color="C0", s=40, zorder=3, label="Per-distance median")
    ax.scatter(rssis_all, np.repeat(d, len(rssis_all) // len(d) + 1)[:len(rssis_all)],
               color="C0", alpha=0.15, s=10, label="All samples (jittered x)")
    d_grid = np.linspace(min(d) * 0.5, max(d) * 1.3, 200)
    ax.plot(d_grid, path_loss_model(d_grid, A, n), "r-", lw=2,
            label=f"Fit: A={A:.2f} dBm, n={n:.2f}")
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("RSSI (dBm)")
    ax.set_title("Path Loss Model Fit")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 右图：残差
    ax = axes[1]
    resid = rssi - path_loss_model(d, A, n)
    ax.scatter(d, resid, color="C1", s=40, zorder=3)
    ax.axhline(0, color="gray", ls="--", lw=1)
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Residual (dBm)")
    ax.set_title("Residuals")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[plot] saved to {out_path}")


def main():
    csv_path = os.path.join(ROOT, "data", "rssi_raw.csv")
    out_plot = os.path.join(ROOT, "results", "path_loss_fit.png")

    d, rssi, rssis_all = load_data(csv_path)
    print(f"[data] {len(d)} 个距离位置, {len(rssis_all)} 个原始样本")
    print(f"[data] 距离: {list(d)}")
    print(f"[data] 各位置中位 RSSI: {np.round(rssi, 2)}")

    # 方法 1：线性化最小二乘
    A_lin, n_lin = fit_linear(d, rssi)
    r2_lin, rmse_lin, mae_lin = evaluate_fit(d, rssi, A_lin, n_lin)
    print("\n[linear LS] A = {:.3f} dBm, n = {:.3f}".format(A_lin, n_lin))
    print("[linear LS] R^2 = {:.4f}, RMSE = {:.4f} dBm, MAE = {:.4f} dBm".format(r2_lin, rmse_lin, mae_lin))

    # 方法 2：非线性最小二乘（带不确定度）
    A_nl, n_nl, perr = fit_curve(d, rssi)
    r2_nl, rmse_nl, mae_nl = evaluate_fit(d, rssi, A_nl, n_nl)
    print("\n[curve_fit] A = {:.3f} +/- {:.3f} dBm, n = {:.3f} +/- {:.3f}".format(A_nl, perr[0], n_nl, perr[1]))
    print("[curve_fit] R^2 = {:.4f}, RMSE = {:.4f} dBm, MAE = {:.4f} dBm".format(r2_nl, rmse_nl, mae_nl))

    # 采用非线性结果作为最终模型（样本少时更稳健）
    A, n = A_nl, n_nl
    print("\n[final] 采用参数: A = {:.3f} dBm, n = {:.3f}".format(A, n))
    print("[final] 距离估计函数: d = 10^(({:.2f} - RSSI) / ({:.2f}))".format(A, 10.0 * n))

    # 验证距离估计精度
    est_d = estimate_distance(rssi, A, n)
    d_err = np.abs(est_d - d)
    print("[final] 各位置距离估计误差(m): {}".format(np.round(d_err, 3)))

    plot_fit(d, rssi, rssis_all, A, n, out_plot)

    # 保存拟合参数供后续步骤使用
    param_path = os.path.join(ROOT, "data", "path_loss_params.npz")
    np.savez(param_path, A=A, n=n, d0=1.0, unique_d=d, median_rssi=rssi)
    print(f"[save] 拟合参数已保存到 {param_path}")


if __name__ == "__main__":
    main()