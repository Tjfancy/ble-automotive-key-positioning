"""
01_collect_rssi.py —— BLE RSSI 数据采集脚本

用途：
  用手机（nRF Connect 广播 "PhoneKey"）作为发射端，
  电脑用 bleak 扫描并记录每个距离位置上的 RSSI 样本。
  同时提供 `--synthetic` 模式，无需硬件时用路径损耗模型生成带噪声的仿真数据，
  保证后续拟合/定位/滤波流水线能完整跑通。

输出 CSV 格式（每行一个样本）：
  distance_m, rssi_dbm, timestamp

用法：
  # 真实扫描（需要电脑有 BLE 且手机在广播）
  python 01_collect_rssi.py --real --name "PhoneKey" --distance 1.0 --n-samples 80 --out data/rssi_raw.csv

  # 合成数据（无硬件时的等效替代）
  python 01_collect_rssi.py --synthetic --distance 1.0 --n-samples 80 --out data/rssi_raw.csv
"""

import argparse
import asyncio
import csv
import datetime
import math
import os
import sys

import numpy as np


# ---------------------------------------------------------------------------
# 真实 BLE 扫描（基于 bleak）
# ---------------------------------------------------------------------------
async def scan_once(duration_s: float, target_name: str):
    """扫描 target_name 设备 duration_s 秒，返回 (name, rssi) 列表。"""
    from bleak import BleakClient, BleakScanner  # 惰性导入，便于无 BLE 环境运行

    found = []

    def callback(device, advertisement_data):
        # advertisement_data.local_name 可能为 None；device.name 作为兜底
        name = advertisement_data.local_name or device.name or ""
        if target_name.lower() in name.lower():
            found.append((name, advertisement_data.rssi, device.address))

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    await asyncio.sleep(duration_s)
    await scanner.stop()
    return found


def collect_real(target_name: str, distance_m: float, n_samples: int,
                 scan_duration_s: float = 15.0, out_path: str = "data/rssi_raw.csv"):
    """真实采集：持续扫描直到收集够 n_samples 个样本或达到扫描时长上限。"""
    import os
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    collected = []
    # 每次扫描时长自适应：至少 10s，样本多时适当延长
    per_round = max(10.0, n_samples * 0.2)
    max_rounds = max(3, n_samples // 20 + 2)

    print(f"[real] scanning '{target_name}', target {n_samples} samples at {distance_m} m")
    for rnd in range(max_rounds):
        if len(collected) >= n_samples:
            break
        res = asyncio.run(scan_once(per_round, target_name))
        for name, rssi, addr in res:
            collected.append({
                "distance_m": distance_m,
                "rssi_dbm": rssi,
                "timestamp": datetime.datetime.now().isoformat(),
                "name": name,
                "address": addr,
            })
        print(f"  round {rnd + 1}: got {len(res)} this round, {len(collected)} total")

    collected = collected[:n_samples]
    _append_csv(out_path, collected)
    print(f"[real] saved {len(collected)} samples to {out_path}")
    return collected


# ---------------------------------------------------------------------------
# 合成数据生成（等效于真实采集，用于无硬件跑通流水线）
# ---------------------------------------------------------------------------
def collect_synthetic(distance_m: float, n_samples: int, out_path: str = "data/rssi_raw.csv",
                      A: float = -40.0, n: float = 3.0, sigma: float = 4.0, seed: int = 42):
    """
    用对数距离路径损耗模型生成带噪声的 RSSI 样本：
        RSSI(d) = A - 10*n*log10(d) + noise,  noise ~ N(0, sigma^2)
    默认 A=-40 (1m 参考), n=3.0 (典型室内路径损耗指数), sigma=4 (RSSI 波动)。
    """
    import os
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    rng = np.random.default_rng(seed)

    rows = []
    for _ in range(n_samples):
        true_rssi = A - 10.0 * n * math.log10(distance_m)
        noisy_rssi = true_rssi + rng.normal(0.0, sigma)
        rows.append({
            "distance_m": distance_m,
            "rssi_dbm": round(float(noisy_rssi), 2),
            "timestamp": datetime.datetime.now().isoformat(),
            "name": "PhoneKey(synthetic)",
            "address": "synthetic",
        })
    _append_csv(out_path, rows)
    print(f"[synthetic] generated {len(rows)} samples (d={distance_m}m) -> {out_path}")
    return rows


def _append_csv(path, rows):
    """追加写入 CSV（首次写入带表头）。"""
    fieldnames = ["distance_m", "rssi_dbm", "timestamp", "name", "address"]
    write_header = not (os.path.exists(path) and os.path.getsize(path) > 0) if os.path.exists(path) else True
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="BLE RSSI 数据采集")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--real", action="store_true", help="真实 BLE 扫描")
    mode.add_argument("--synthetic", action="store_true", help="合成数据（无硬件）")
    parser.add_argument("--name", default="PhoneKey", help="广播设备名称（real 模式）")
    parser.add_argument("--distance", type=float, required=True, help="当前采集位置到发射端的距离（米）")
    parser.add_argument("--n-samples", type=int, default=80, help="每个位置采集的样本数")
    parser.add_argument("--out", default="data/rssi_raw.csv", help="输出 CSV 路径")
    args = parser.parse_args()

    if args.real:
        collect_real(args.name, args.distance, args.n_samples, out_path=args.out)
    else:
        collect_synthetic(args.distance, args.n_samples, out_path=args.out)


if __name__ == "__main__":
    # Windows 上 asyncio 需要策略修复；macOS/Linux 无需
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()