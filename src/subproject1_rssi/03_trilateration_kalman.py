"""
03_trilateration_kalman.py —— 三边定位 + 卡尔曼滤波 + 误差评估

场景：
  3 个锚点（已知坐标）接收目标（手机）的 BLE 广播，
  各锚点把 RSSI 通过路径损耗模型转成距离估计，
  再用最小二乘三边定位解算目标二维坐标。

流程（每时间步）：
  1. 目标沿已知轨迹移动，锚点收到带噪声的 RSSI
  2. RSSI -> 距离估计 d_est（对数距离模型反函数）
  3. 【原始定位】用 d_est 直接三边定位 -> 位置 P_raw
  4. 【滤波定位】d_est 先过 1D 卡尔曼滤波 -> d_filt -> 三边定位 -> 位置 P_filt
  5. 对比 P_raw / P_filt 相对真值的误差，统计并画 CDF

关键函数：
  - trilaterate(anchors, distances) : 最小二乘三边定位
  - make_kalman_1d(dt, q, r)       : 构造 1D 恒速模型 KalmanFilter
  - run_simulation(...)            : 运动仿真 + 滤波对比
"""

import os
import sys

import numpy as np
from filterpy.kalman import KalmanFilter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))


# ---------------------------------------------------------------------------
# 三边定位（最小二乘）
# ---------------------------------------------------------------------------
def trilaterate(anchors, distances):
    """
    最小二乘三边定位（二维）。

    数学：对每个锚点 i 有 (x-xi)^2 + (y-yi)^2 = di^2。
    用锚点 0 作参考，消去二次项得到线性方程组 A @ [x, y] = b：
        2*(x1-x0)*x + 2*(y1-y0)*y = d0^2 - d1^2 + x1^2 - x0^2 + y1^2 - y0^2
        2*(x2-x0)*x + 2*(y2-y0)*y = d0^2 - d2^2 + x2^2 - x0^2 + y2^2 - y0^2
    超定方程用 lstsq 求最小二乘解（锚点>3 时同样适用）。

    参数：
      anchors  : (M, 2) 锚点坐标
      distances: (M,)   目标到各锚点的距离估计
    返回：
      (x, y) 估计坐标，残差 norm
    """
    anchors = np.asarray(anchors, dtype=float)
    distances = np.asarray(distances, dtype=float)
    a0 = anchors[0]
    d0 = distances[0]
    A_rows = []
    b_rows = []
    for i in range(1, len(anchors)):
        ai = anchors[i]
        di = distances[i]
        row = 2.0 * (ai - a0)           # [2*(xi-x0), 2*(yi-y0)]
        rhs = (d0 ** 2 - di ** 2 +      # d0^2 - di^2
               ai[0] ** 2 - a0[0] ** 2 +  # xi^2 - x0^2
               ai[1] ** 2 - a0[1] ** 2)   # yi^2 - y0^2
        A_rows.append(row)
        b_rows.append(rhs)
    A = np.array(A_rows)
    b = np.array(b_rows)
    # 最小二乘解
    xy, residuals, rank, sv = np.linalg.lstsq(A, b, rcond=None)
    pos = xy[:2]
    # 残差：方程组的拟合误差（衡量一致性）
    resid = np.linalg.norm(A @ xy - b)
    return pos, resid


# ---------------------------------------------------------------------------
# 1D 卡尔曼滤波（filterpy）
# ---------------------------------------------------------------------------
def make_kalman_1d(dt, q, r):
    """
    构造 1D 恒速模型卡尔曼滤波器（filterpy）。

    状态 x = [position, velocity]^T
      F = [[1, dt],      H = [[1, 0]]
           [0, 1]]
    过程噪声 Q：假设加速度不确定度，q 为加速度方差
      Q = q * [[dt^4/4, dt^3/2],
               [dt^3/2, dt^2]]
    测量噪声 R：RSSI 转距离的测量方差，r 为标量

    参数：
      dt : 采样间隔（秒）
      q  : 过程噪声强度（加速度方差），控制平滑度
      r  : 测量噪声方差，控制跟踪灵敏度
    """
    kf = KalmanFilter(dim_x=2, dim_z=1)
    kf.F = np.array([[1.0, dt],
                     [0.0, 1.0]])
    kf.H = np.array([[1.0, 0.0]])
    # 过程噪声 Q（离散白噪声加速度模型）
    kf.Q = np.array([[dt ** 4 / 4.0, dt ** 3 / 2.0],
                     [dt ** 3 / 2.0, dt ** 2]]) * q
    kf.R = np.array([[r]])
    kf.x = np.array([[0.0], [0.0]])  # 初始状态
    kf.P = np.array([[100.0, 0.0],
                     [0.0, 100.0]])  # 初始不确定度
    return kf


# ---------------------------------------------------------------------------
# 仿真
# ---------------------------------------------------------------------------
def rssi_to_distance(rssi, A, n, d0=1.0):
    """路径损耗模型反函数：RSSI -> 距离。"""
    return d0 * 10.0 ** ((A - rssi) / (10.0 * n))


def run_simulation(anchors, true_traj, dt, A, n, rssi_sigma, steps, seed=42):
    """
    运动仿真 + 卡尔曼滤波对比。

    参数：
      anchors      : (M,2) 锚点坐标
      true_traj    : (T,2) 目标真实轨迹
      dt           : 采样间隔
      A, n         : 路径损耗模型参数
      rssi_sigma   : RSSI 噪声标准差（dBm）
      steps        : 仿真步数（T）
      seed         : 随机种子
    返回：
      dict 包含 raw/filt 位置序列、距离序列、误差序列
    """
    rng = np.random.default_rng(seed)
    M = len(anchors)

    # 为每个锚点准备一个卡尔曼滤波器
    # 测量噪声 r：由 RSSI 噪声经模型传播得到（近似线性化）
    #   d = 10^((A-RSSI)/(10n)) -> dd/dRSSI = -ln(10)/(10n) * d
    #   r ≈ (d * ln(10)/(10n) * rssi_sigma)^2，取典型距离处的值
    d_typical = 3.0
    r_meas = (d_typical * np.log(10) / (10.0 * n) * rssi_sigma) ** 2
    q_proc = 0.05  # 过程噪声：目标速度变化较小

    kfs = [make_kalman_1d(dt, q_proc, r_meas) for _ in range(M)]

    raw_positions = []
    filt_positions = []
    true_positions = []
    d_ests = []
    d_filts = []

    for t in range(steps):
        true_pos = true_traj[t]
        true_positions.append(true_pos)

        # 各锚点的真值距离 + RSSI 噪声 -> 距离估计
        d_true = np.linalg.norm(anchors - true_pos, axis=1)
        rssi_noisy = A - 10.0 * n * np.log10(d_true) + rng.normal(0, rssi_sigma, size=M)
        d_est = rssi_to_distance(rssi_noisy, A, n)
        d_ests.append(d_est)

        # 原始定位（用原始距离估计）
        pos_raw, _ = trilaterate(anchors, d_est)
        raw_positions.append(pos_raw)

        # 卡尔曼滤波：每个锚点独立滤波距离序列
        d_filt = np.zeros(M)
        for i, kf in enumerate(kfs):
            kf.predict()
            kf.update(np.array([[d_est[i]]]))
            d_filt[i] = kf.x[0, 0]
        d_filts.append(d_filt)

        # 滤波后定位
        pos_filt, _ = trilaterate(anchors, d_filt)
        filt_positions.append(pos_filt)

    return {
        "true": np.array(true_positions),
        "raw": np.array(raw_positions),
        "filt": np.array(filt_positions),
        "d_est": np.array(d_ests),
        "d_filt": np.array(d_filts),
    }


# ---------------------------------------------------------------------------
# 评估
# ---------------------------------------------------------------------------
def compute_errors(true, est):
    """计算逐点欧氏误差。"""
    return np.linalg.norm(true - est, axis=1)


def error_metrics(errors):
    """统计误差指标。"""
    return {
        "mean": float(np.mean(errors)),
        "median": float(np.median(errors)),
        "rmse": float(np.sqrt(np.mean(errors ** 2))),
        "p90": float(np.percentile(errors, 90)),
        "p95": float(np.percentile(errors, 95)),
        "max": float(np.max(errors)),
    }


def plot_results(res, out_dir):
    """绘制定位轨迹 + 误差 CDF。"""
    os.makedirs(out_dir, exist_ok=True)

    # ---- 轨迹对比 ----
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(res["true"][:, 0], res["true"][:, 1], "k-", lw=2, label="Ground truth")
    ax.scatter(res["true"][0, 0], res["true"][0, 1], color="green", s=80, zorder=5, label="Start")
    ax.scatter(res["true"][-1, 0], res["true"][-1, 1], color="red", s=80, zorder=5, label="End")
    ax.plot(res["raw"][:, 0], res["raw"][:, 1], "r--", lw=1.5, alpha=0.7, label="Raw trilateration")
    ax.plot(res["filt"][:, 0], res["filt"][:, 1], "b-", lw=1.5, alpha=0.8, label="Kalman filtered")
    # 锚点
    ax.scatter(res.get("anchors", [])[:, 0], res.get("anchors", [])[:, 1],
               marker="^", s=120, color="darkorange", zorder=4, label="Anchors")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("Trilateration: Raw vs Kalman Filtered")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "traj_compare.png"), dpi=150)
    plt.close(fig)

    # ---- 误差 CDF ----
    err_raw = compute_errors(res["true"], res["raw"])
    err_filt = compute_errors(res["true"], res["filt"])

    fig, ax = plt.subplots(figsize=(7, 6))
    for errs, label, color in [
        (err_raw, "Raw", "red"),
        (err_filt, "Kalman filtered", "blue"),
    ]:
        sorted_e = np.sort(errs)
        cdf = np.arange(1, len(sorted_e) + 1) / len(sorted_e)
        ax.step(sorted_e, cdf, where="post", lw=2, color=color, label=label)
    ax.set_xlabel("Position error (m)")
    ax.set_ylabel("CDF")
    ax.set_title("Position Error CDF")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, None)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "error_cdf.png"), dpi=150)
    plt.close(fig)

    # ---- 误差随时间变化 ----
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(err_raw, "r--", lw=1.2, alpha=0.7, label="Raw error")
    ax.plot(err_filt, "b-", lw=1.2, alpha=0.8, label="Filtered error")
    ax.set_xlabel("Time step")
    ax.set_ylabel("Position error (m)")
    ax.set_title("Position Error vs Time")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "error_vs_time.png"), dpi=150)
    plt.close(fig)


def main():
    # 加载拟合参数
    param_path = os.path.join(ROOT, "data", "path_loss_params.npz")
    params = np.load(param_path)
    A = float(params["A"])
    n = float(params["n"])
    print(f"[model] A={A:.3f} dBm, n={n:.3f}")

    # ---- 场景定义 ----
    # 3 个锚点（已知坐标，单位 m）
    anchors = np.array([
        [0.0, 0.0],
        [5.0, 0.0],
        [2.5, 4.0],
    ])
    print(f"[anchors]\n{anchors}")

    # 目标沿直线匀速运动（从 (1,1) 到 (4,2)）
    steps = 60
    dt = 1.0  # 秒
    start = np.array([1.0, 1.0])
    end = np.array([4.0, 2.0])
    t = np.linspace(0, 1, steps)
    true_traj = start[None, :] + (end - start)[None, :] * t[:, None]

    # RSSI 噪声标准差（实测典型值 3~5 dBm）
    rssi_sigma = 4.0

    # 运行仿真
    res = run_simulation(anchors, true_traj, dt, A, n, rssi_sigma, steps, seed=42)
    res["anchors"] = anchors

    # ---- 误差评估 ----
    err_raw = compute_errors(res["true"], res["raw"])
    err_filt = compute_errors(res["true"], res["filt"])

    print("\n=== 误差指标对比 ===")
    m_raw = error_metrics(err_raw)
    m_filt = error_metrics(err_filt)
    for k in m_raw:
        print(f"  {k:>6}: raw={m_raw[k]:.4f} m, filt={m_filt[k]:.4f} m, "
              f"改善={100*(m_raw[k]-m_filt[k])/m_raw[k]:.1f}%")

    # 改善总结
    print(f"\n[结论] 平均定位误差从 {m_raw['mean']:.3f} m 降至 {m_filt['mean']:.3f} m "
          f"(改善 {100*(m_raw['mean']-m_filt['mean'])/m_raw['mean']:.1f}%)")
    print(f"[结论] P90 误差从 {m_raw['p90']:.3f} m 降至 {m_filt['p90']:.3f} m")

    plot_results(res, os.path.join(ROOT, "results"))


if __name__ == "__main__":
    main()