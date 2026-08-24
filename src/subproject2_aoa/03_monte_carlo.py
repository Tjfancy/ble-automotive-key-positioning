"""
03_monte_carlo.py —— AoA 算法蒙特卡洛评估

实验设计：
  固定单信源入射角 theta_true = 30 deg，快照数 K = 200。
  扫描：
    - SNR      : -10, -5, 0, 5, 10, 15, 20, 25, 30 dB
    - 阵元数 M : 4, 8, 16
  每组 (SNR, M) 运行 N_trials 次独立实验，统计角度估计 RMSE。

对比算法：
  - MUSIC：全角度网格搜索（0.5 deg 分辨率）
  - ESPRIT：子空间旋转不变性，直接代数求解

输出：
  - results/mc_rmse_vs_snr.png : RMSE vs SNR（不同 M 的曲线）
  - results/mc_rmse_vs_M.png   : RMSE vs 阵元数（不同 SNR 的曲线）
  - 结果数据保存到 data/mc_results.npz
"""

import os
import sys
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

import importlib.util

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

sm = _load("signal_model_music", os.path.join(os.path.dirname(__file__), "01_signal_model_music.py"))
esprit_mod = _load("esprit", os.path.join(os.path.dirname(__file__), "02_esprit.py"))


def run_monte_carlo(theta_true=30.0, K=200, snr_list=None, M_list=None,
                    n_trials=50, seed_start=0):
    """
    运行蒙特卡洛实验。

    返回：
      results : dict, results[snr][M] = {'music': [errs], 'esprit': [errs]}
    """
    if snr_list is None:
        snr_list = [-10, -5, 0, 5, 10, 15, 20, 25, 30]
    if M_list is None:
        M_list = [4, 8, 16]

    results = {}
    total = len(snr_list) * len(M_list)
    done = 0
    t0 = time.time()
    for snr in snr_list:
        results[snr] = {}
        for M in M_list:
            music_errs = []
            esprit_errs = []
            for trial in range(n_trials):
                seed = seed_start + trial
                X, _, _ = sm.generate_signal(theta_true, M, K, snr, seed=seed)

                # MUSIC
                _, _, est_music = sm.music_spectrum(X, p=1)
                music_errs.append(est_music - theta_true)

                # ESPRIT
                est_esprit = esprit_mod.esprit_estimate(X, p=1)[0]
                esprit_errs.append(est_esprit - theta_true)

            results[snr][M] = {
                "music": np.array(music_errs),
                "esprit": np.array(esprit_errs),
            }
            done += 1
            rmse_m = np.sqrt(np.mean(np.array(music_errs) ** 2))
            rmse_e = np.sqrt(np.mean(np.array(esprit_errs) ** 2))
            print(f"  [{done}/{total}] SNR={snr:>3} dB, M={M:>2}: "
                  f"MUSIC RMSE={rmse_m:.4f} deg, ESPRIT RMSE={rmse_e:.4f} deg")
    elapsed = time.time() - t0
    print(f"[monte carlo] 完成 {total} 组实验, 耗时 {elapsed:.1f} s")
    return results


def compute_rmse_table(results):
    """计算每个 (SNR, M) 下 MUSIC 和 ESPRIT 的 RMSE。"""
    table = {}
    for snr in results:
        table[snr] = {}
        for M in results[snr]:
            table[snr][M] = {
                "music": float(np.sqrt(np.mean(results[snr][M]["music"] ** 2))),
                "esprit": float(np.sqrt(np.mean(results[snr][M]["esprit"] ** 2))),
            }
    return table


# ---------------------------------------------------------------------------
# 绘图
# ---------------------------------------------------------------------------
def plot_rmse_vs_snr(results, M_list, out_path):
    """RMSE vs SNR，每条线对应一个 M。"""
    fig, ax = plt.subplots(figsize=(8, 5))
    snrs = sorted(results.keys())
    colors = {4: "C0", 8: "C1", 16: "C2"}
    markers = {4: "o", 8: "s", 8: "^", 16: "d"}
    for M in M_list:
        rmse_music = [np.sqrt(np.mean(results[snr][M]["music"] ** 2)) for snr in snrs]
        rmse_esprit = [np.sqrt(np.mean(results[snr][M]["esprit"] ** 2)) for snr in snrs]
        ax.plot(snrs, rmse_music, color=colors[M], marker=markers.get(M, "o"),
                linestyle="--", lw=1.8, label=f"MUSIC M={M}")
        ax.plot(snrs, rmse_esprit, color=colors[M], marker=markers.get(M, "o"),
                linestyle="-", lw=1.8, label=f"ESPRIT M={M}")
    ax.set_xlabel("SNR (dB)")
    ax.set_ylabel("Angle RMSE (deg)")
    ax.set_title("AoA Estimation RMSE vs SNR")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(snrs)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[plot] saved to {out_path}")


def plot_rmse_vs_M(results, snr_list, out_path):
    """RMSE vs 阵元数 M，每条线对应一个 SNR。"""
    fig, ax = plt.subplots(figsize=(8, 5))
    M_list = sorted(list(results[snr_list[0]].keys()))
    snrs_to_plot = [-10, 0, 10, 20, 30]
    snrs_to_plot = [s for s in snrs_to_plot if s in results]
    colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(snrs_to_plot)))
    for i, snr in enumerate(snrs_to_plot):
        rmse_music = [np.sqrt(np.mean(results[snr][M]["music"] ** 2)) for M in M_list]
        rmse_esprit = [np.sqrt(np.mean(results[snr][M]["esprit"] ** 2)) for M in M_list]
        ax.plot(M_list, rmse_music, color=colors[i], marker="s",
                linestyle="--", lw=1.8, label=f"MUSIC SNR={snr}dB")
        ax.plot(M_list, rmse_esprit, color=colors[i], marker="o",
                linestyle="-", lw=1.8, label=f"ESPRIT SNR={snr}dB")
    ax.set_xlabel("Number of elements M")
    ax.set_ylabel("Angle RMSE (deg)")
    ax.set_title("AoA Estimation RMSE vs Array Elements")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(M_list)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[plot] saved to {out_path}")


def main():
    snr_list = [-10, -5, 0, 5, 10, 15, 20, 25, 30]
    M_list = [4, 8, 16]
    n_trials = 50

    print(f"[monte carlo] theta_true=30 deg, K=200, trials={n_trials}")
    results = run_monte_carlo(theta_true=30.0, K=200, snr_list=snr_list,
                              M_list=M_list, n_trials=n_trials)

    rmse_table = compute_rmse_table(results)

    # 保存结果
    save_path = os.path.join(ROOT, "data", "mc_results.npz")
    save_dict = {}
    for snr in results:
        for M in results[snr]:
            save_dict[f"music_{snr}_{M}"] = results[snr][M]["music"]
            save_dict[f"esprit_{snr}_{M}"] = results[snr][M]["esprit"]
    np.savez(save_path, **save_dict)
    print(f"[save] 蒙特卡洛原始数据已保存到 {save_path}")

    # 绘图
    plot_rmse_vs_snr(results, M_list, os.path.join(ROOT, "results", "mc_rmse_vs_snr.png"))
    plot_rmse_vs_M(results, snr_list, os.path.join(ROOT, "results", "mc_rmse_vs_M.png"))

    # 打印关键结论
    print("\n=== 关键结论摘要 ===")
    for M in M_list:
        e_low = rmse_table[-10][M]
        e_high = rmse_table[30][M]
        print(f"  M={M}: SNR -10->30 dB, MUSIC {e_low['music']:.3f}->{e_high['music']:.3f} deg, "
              f"ESPRIT {e_low['esprit']:.3f}->{e_high['esprit']:.3f} deg")


if __name__ == "__main__":
    main()