"""
01_signal_model_music.py —— 均匀线阵 AoA 信号模型 + MUSIC 算法

物理模型：
  均匀线阵（ULA），M 个阵元，阵元间距 d = lambda/2，载波 2.4 GHz。
  远场单源入射，方向 theta（与阵法线夹角）。

  导向矢量（steering vector）：
    a(theta) = [1, e^{j*pi*sin(theta)}, e^{j*2*pi*sin(theta)}, ...,
                e^{j*(M-1)*pi*sin(theta)}]^T
    （因为 d=lambda/2，相邻阵元相位差 = pi*sin(theta)）

  接收信号（K 个快照）：
    X = a(theta) * s + n,   X: (M, K), n ~ CN(0, sigma^2*I)

MUSIC 算法（Multiple Signal Classification）：
  1. 计算协方差矩阵 R = (1/K) * X @ X^H
  2. 特征分解 R = V @ Lambda @ V^H，按特征值降序排列
  3. 划分信号子空间（前 p 个特征向量）与噪声子空间（后 M-p 个）
     p = 信源数（本例 p=1）
  4. 噪声子空间 Un = [v_{p+1}, ..., v_M]
  5. MUSIC 空间谱：P_MUSIC(theta) = 1 / (a^H(theta) @ Un @ Un^H @ a(theta))
  6. 在 theta in [-90, 90] deg 搜索谱峰 -> 角度估计

输出：
  - 空间谱图（验证角度估计正确性）
  - 不同 SNR 下的角度估计误差
"""

import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))


# ---------------------------------------------------------------------------
# 信号模型
# ---------------------------------------------------------------------------
def steering_vector(theta_deg, M, d_over_lambda=0.5):
    """
    ULA 导向矢量 a(theta)。

    参数：
      theta_deg     : 入射角（度），相对阵法线
      M             : 阵元数
      d_over_lambda : 阵元间距/波长（默认 0.5 = lambda/2）
    返回：
      a : (M,) 复数导向矢量
    """
    theta = np.deg2rad(theta_deg)
    m = np.arange(M)
    phase = 2.0 * np.pi * d_over_lambda * m * np.sin(theta)
    return np.exp(1j * phase)


def generate_signal(theta_deg, M, K, snr_db, d_over_lambda=0.5, seed=None):
    """
    生成 ULA 接收信号快照。

    参数：
      theta_deg : 入射角（度）
      M         : 阵元数
      K         : 快照数
      snr_db    : 信噪比（dB）
      seed      : 随机种子
    返回：
      X : (M, K) 复数接收数据矩阵
      s : (K,)   复数源信号（单位功率）
      a : (M,)   导向矢量
    """
    rng = np.random.default_rng(seed)
    a = steering_vector(theta_deg, M, d_over_lambda)

    # 源信号：复高斯，单位功率 E[|s|^2] = 1
    s = (rng.standard_normal(K) + 1j * rng.standard_normal(K)) / np.sqrt(2.0)

    # 噪声功率由 SNR 决定：SNR = 10*log10(Ps/Pn), Ps=1 -> Pn = 10^(-snr/10)
    noise_power = 10.0 ** (-snr_db / 10.0)
    noise = np.sqrt(noise_power / 2.0) * (
        rng.standard_normal((M, K)) + 1j * rng.standard_normal((M, K))
    )

    X = np.outer(a, s) + noise
    return X, s, a


# ---------------------------------------------------------------------------
# MUSIC 算法
# ---------------------------------------------------------------------------
def music_spectrum(X, p=1, theta_grid=None):
    """
    计算 MUSIC 空间谱。

    参数：
      X         : (M, K) 接收数据
      p         : 信源数（默认 1）
      theta_grid: 角度搜索网格（度），默认 -90:0.5:90
    返回：
      theta_grid : 搜索角度（度）
      P          : 对应的 MUSIC 谱值
      theta_est  : 谱峰对应的角度估计
    """
    M, K = X.shape
    # 1. 协方差矩阵
    R = (X @ X.conj().T) / K

    # 2. 特征分解
    eigvals, eigvecs = np.linalg.eigh(R)  # eigh 返回升序特征值

    # 3. 按特征值降序排列
    idx = np.argsort(eigvals)[::-1]
    eigvals = eigvals[idx]
    eigvecs = eigvecs[:, idx]

    # 4. 噪声子空间：后 M-p 个特征向量
    Un = eigvecs[:, p:]  # (M, M-p)

    # 5. 空间谱
    if theta_grid is None:
        theta_grid = np.arange(-90.0, 90.01, 0.5)
    P = np.zeros_like(theta_grid)
    for i, th in enumerate(theta_grid):
        a = steering_vector(th, M)
        denom = a.conj().T @ Un @ Un.conj().T @ a
        P[i] = 1.0 / np.real(denom)

    # 6. 谱峰搜索
    peak_idx = np.argmax(P)
    theta_est = theta_grid[peak_idx]
    return theta_grid, P, theta_est


# ---------------------------------------------------------------------------
# 可视化
# ---------------------------------------------------------------------------
def plot_spectrum(theta_grid, P, theta_true, theta_est, M, snr_db, out_path):
    """绘制 MUSIC 空间谱。"""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    # 归一化到 0dB 便于观察
    P_db = 10.0 * np.log10(P / np.max(P) + 1e-12)
    ax.plot(theta_grid, P_db, "b-", lw=1.5, label="MUSIC spectrum")
    ax.axvline(theta_true, color="green", ls="--", lw=1.5, label=f"True = {theta_true} deg")
    ax.axvline(theta_est, color="red", ls="-.", lw=1.5, label=f"Est = {theta_est:.2f} deg")
    ax.set_xlabel("Angle (deg)")
    ax.set_ylabel("Normalized spectrum (dB)")
    ax.set_title(f"MUSIC Spatial Spectrum (M={M}, SNR={snr_db} dB, K=200)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[plot] saved to {out_path}")


# ---------------------------------------------------------------------------
# 主流程：单场景验证
# ---------------------------------------------------------------------------
def main():
    M = 8            # 阵元数
    K = 200          # 快照数
    theta_true = 30.0  # 真实入射角
    snr_db = 10.0    # 信噪比

    # 生成信号
    X, s, a = generate_signal(theta_true, M, K, snr_db, seed=42)
    print(f"[signal] M={M} elements, K={K} snapshots, SNR={snr_db} dB, theta_true={theta_true} deg")

    # MUSIC 估计
    theta_grid, P, theta_est = music_spectrum(X, p=1)
    err = theta_est - theta_true
    print(f"[MUSIC] estimated angle = {theta_est:.3f} deg, error = {err:+.3f} deg")

    # 绘图
    out_plot = os.path.join(ROOT, "results", "music_spectrum.png")
    plot_spectrum(theta_grid, P, theta_true, theta_est, M, snr_db, out_plot)


if __name__ == "__main__":
    main()