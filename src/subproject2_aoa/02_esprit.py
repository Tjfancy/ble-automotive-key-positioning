"""
02_esprit.py —— ESPRIT 算法（利用阵列旋转不变性估计入射角）

原理：
  均匀线阵具有平移不变性：前 M-1 个阵元与后 M-1 个阵元的子阵列
  接收同一信号，仅相差一个与入射角相关的相位旋转。

  对信号子空间 Es（M x p，来自协方差矩阵特征分解的前 p 个特征向量）：
    Es1 = Es[0:M-1, :]   （前 M-1 行）
    Es2 = Es[1:M, :]     （后 M-1 行）
    存在 p x p 矩阵 Psi 满足：Es2 = Es1 @ Psi

  对 Psi 做特征分解，特征值 lambda_k = exp(j * pi * sin(theta_k))
  因此：theta_k = arcsin(angle(lambda_k) / pi)

  优点：不需要全角度搜索，直接代数求解，计算量远小于 MUSIC。
  代价：对信源数估计和子阵划分敏感，低 SNR 时稳定性略逊 MUSIC。

输出：
  - 单场景角度估计验证
  - 与 MUSIC 对比的空间谱（可选）
"""

import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

# 复用 01 中的信号模型与导向矢量（模块名以数字开头，用 importlib 动态加载）
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "signal_model_music",
    os.path.join(os.path.dirname(__file__), "01_signal_model_music.py"),
)
sm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sm)


def esprit_estimate(X, p=1, d_over_lambda=0.5):
    """
    ESPRIT 角度估计。

    参数：
      X             : (M, K) 接收数据
      p             : 信源数（默认 1）
      d_over_lambda : 阵元间距/波长（默认 0.5）
    返回：
      theta_est : 估计的入射角（度），升序排列
    """
    M, K = X.shape
    # 1. 协方差矩阵
    R = (X @ X.conj().T) / K

    # 2. 特征分解，取信号子空间（前 p 个特征向量）
    eigvals, eigvecs = np.linalg.eigh(R)
    idx = np.argsort(eigvals)[::-1]  # 降序
    eigvecs = eigvecs[:, idx]
    Es = eigvecs[:, :p]  # (M, p) 信号子空间

    # 3. 子阵划分（前 M-1 / 后 M-1）
    Es1 = Es[0:M - 1, :]  # (M-1, p)
    Es2 = Es[1:M, :]      # (M-1, p)

    # 4. 求解 Psi：Es2 = Es1 @ Psi  =>  Psi = pinv(Es1) @ Es2
    Psi = np.linalg.pinv(Es1) @ Es2  # (p, p)

    # 5. 特征分解 Psi，特征值 lambda_k = exp(j*pi*sin(theta_k))
    eigvals_psi = np.linalg.eigvals(Psi)

    # 6. 由特征值反解角度
    phases = np.angle(eigvals_psi)  # 弧度，取值 [-pi, pi]
    sin_theta = phases / (np.pi * 2.0 * d_over_lambda)  # sin(theta) = phase / (2*pi*d/lambda)
    # 由于 d=lambda/2，分母 = pi
    # 限制到 [-1, 1] 避免数值越界
    sin_theta = np.clip(sin_theta, -1.0, 1.0)
    theta_deg = np.rad2deg(np.arcsin(sin_theta))
    theta_deg = np.sort(np.real(theta_deg))
    return theta_deg


def main():
    """单场景验证：对比 ESPRIT 估计与真实角度。"""
    M = 8
    K = 200
    theta_true = 30.0
    snr_db = 10.0

    X, s, a = sm.generate_signal(theta_true, M, K, snr_db, seed=42)
    theta_est = esprit_estimate(X, p=1)
    print(f"[signal] M={M}, K={K}, SNR={snr_db} dB, theta_true={theta_true} deg")
    print(f"[ESPRIT] estimated angle = {theta_est[0]:.3f} deg, error = {theta_est[0] - theta_true:+.3f} deg")

    # 多次实验看稳定性
    errs = []
    for seed in range(50):
        X, _, _ = sm.generate_signal(theta_true, M, K, snr_db, seed=seed)
        est = esprit_estimate(X, p=1)[0]
        errs.append(est - theta_true)
    errs = np.array(errs)
    print(f"[ESPRIT] 50 trials: mean={np.mean(errs):.4f} deg, std={np.std(errs):.4f} deg, "
          f"RMSE={np.sqrt(np.mean(errs**2)):.4f} deg")


if __name__ == "__main__":
    main()