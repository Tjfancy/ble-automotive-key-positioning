"""
run_all.py —— 一键运行整个项目（无需硬件，纯合成数据）

等价于按顺序执行：
  1. python src/subproject1_rssi/01_collect_rssi.py --synthetic ...
  2. python src/subproject1_rssi/02_path_loss_fit.py
  3. python src/subproject1_rssi/03_trilateration_kalman.py
  4. python src/subproject2_aoa/01_signal_model_music.py
  5. python src/subproject2_aoa/02_esprit.py
  6. python src/subproject2_aoa/03_monte_carlo.py

用法：
  python run_all.py            # 默认参数，生成合成数据并跑完全部
  python run_all.py --skip-mc  # 跳过耗时的蒙特卡洛，快速验证
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")


def run(cmd, label):
    """运行子进程命令，打印步骤标签。"""
    print(f"\n{'=' * 60}")
    print(f">>> {label}")
    print(f"{'=' * 60}")
    result = subprocess.run(cmd, cwd=ROOT, shell=True)
    if result.returncode != 0:
        print(f"[ERROR] 步骤失败: {label}")
        sys.exit(result.returncode)


def main():
    skip_mc = "--skip-mc" in sys.argv

    # 1. 生成合成 RSSI 数据（7 个距离位置）
    run(f"{sys.executable} src/subproject1_rssi/01_collect_rssi.py "
        f"--synthetic --distance 0.5 --n-samples 50 --out data/rssi_raw.csv",
        "Step 1/6: RSSI 数据采集 (synthetic)")

    for d in [1.0, 1.5, 2.0, 3.0, 4.0, 5.0]:
        run(f"{sys.executable} src/subproject1_rssi/01_collect_rssi.py "
            f"--synthetic --distance {d} --n-samples 80 --out data/rssi_raw.csv",
            f"  -> 距离 {d}m")

    # 2. 路径损耗模型拟合
    run(f"{sys.executable} src/subproject1_rssi/02_path_loss_fit.py",
        "Step 2/6: 路径损耗模型拟合")

    # 3. 三边定位 + 卡尔曼滤波
    run(f"{sys.executable} src/subproject1_rssi/03_trilateration_kalman.py",
        "Step 3/6: 三边定位 + 卡尔曼滤波")

    # 4. MUSIC 算法
    run(f"{sys.executable} src/subproject2_aoa/01_signal_model_music.py",
        "Step 4/6: MUSIC 算法")

    # 5. ESPRIT 算法
    run(f"{sys.executable} src/subproject2_aoa/02_esprit.py",
        "Step 5/6: ESPRIT 算法")

    # 6. 蒙特卡洛评估
    if not skip_mc:
        run(f"{sys.executable} src/subproject2_aoa/03_monte_carlo.py",
            "Step 6/6: 蒙特卡洛评估")
    else:
        print("\n[skip] 蒙特卡洛已跳过 (--skip-mc)")

    print("\n" + "=" * 60)
    print("全部完成！图表保存在 results/ 目录")
    print("=" * 60)


if __name__ == "__main__":
    main()