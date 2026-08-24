# HANDOFF — 项目交接文档

> 目的：让**不知道上下文的 AI 或开发者**读完本文档，就能完全接管、运行、修改、扩展这个项目。
>
> 本文档面向 2026 年 8 月之后的维护者。所有路径、参数、结论均为当前最新状态。

---

## 0. 快速定位

| 你想知道… | 看这里 |
|-----------|--------|
| 项目是干什么的 | §1 项目背景 |
| 仓库在哪、怎么克隆 | §2 仓库信息 |
| 一条命令跑通全部 | §3 快速开始 |
| 每个脚本干什么、输入输出 | §4 脚本手册 |
| 关键参数在哪改、什么意思 | §5 关键参数 |
| 实验结果和结论 | §6 实验结果 |
| 怎么扩展 / 后续方向 | §7 可拓展方向 |
| AI 接管时的注意事项 | §8 接管指南 |
| 详细的算法报告（LaTeX PDF） | §9 详细报告 |

---

## 1. 项目背景

### 1.1 是什么

**面向汽车数字钥匙（CCC / ICCE 标准）的 BLE 定位技术原型与算法评估。**

将实习期间对 BLE AoA、UWB 数字钥匙技术的调研，转化为**可运行代码 + 实验数据 + 可视化结论**的完整项目，用于秋招面试展示。

### 1.2 两个子项目

| 子项目 | 内容 | 硬件依赖 |
|--------|------|----------|
| **子项目一：BLE RSSI 定位与滤波** | RSSI 采集 → 路径损耗拟合 → 三边定位 → 卡尔曼滤波 → 误差评估 | 无（合成模式）/ 手机 + 电脑 BLE（真实模式） |
| **子项目二：BLE AoA 算法仿真** | ULA 信号模型 → MUSIC → ESPRIT → 蒙特卡洛评估 | 无（纯软件仿真） |

### 1.3 技术栈

Python 3.9+、numpy、scipy、matplotlib、bleak、filterpy。

---

## 2. 仓库信息

| 项目 | 值 |
|------|-----|
| 仓库地址 | `https://github.com/Tjfancy/ble-automotive-key-positioning` |
| 当前分支 | `master` |
| 最新 commit | `4d1ce2c`（RSSI LaTeX 报告） |
| 本地路径 | `C:\Users\LiangFeng(CN-TT-U1)\Desktop\BLE\ble-automotive-key-positioning` |

### 2.1 目录结构

```
ble-automotive-key-positioning/
├── HANDOFF.md                     # 本文档
├── README.md                      # 项目文档（原理、步骤、结果、面试要点）
├── requirements.txt               # 5 个 Python 依赖
├── run_all.py                     # 一键运行全部流程
├── .gitignore
│
├── data/                          # 实验数据（已提交，可直接用）
│   ├── rssi_raw.csv               # 500~1030 个 RSSI 样本
│   ├── path_loss_params.npz       # 拟合参数 A, n
│   └── mc_results.npz             # 蒙特卡洛原始误差数据
│
├── results/                       # 7 张实验图表
│   ├── path_loss_fit.png          # 路径损耗拟合曲线 + 残差
│   ├── traj_compare.png           # 定位轨迹对比
│   ├── error_cdf.png              # 误差 CDF
│   ├── error_vs_time.png          # 误差 vs 时间
│   ├── music_spectrum.png         # MUSIC 空间谱
│   ├── mc_rmse_vs_snr.png         # RMSE vs SNR
│   └── mc_rmse_vs_M.png           # RMSE vs 阵元数
│
├── docs/
│   ├── aoa_simulation_report.md       # AoA 报告（Markdown）
│   ├── aoa_simulation_report.tex      # AoA 报告（LaTeX 源文件）
│   ├── aoa_simulation_report.pdf      # AoA 报告（编译后 PDF，12 页）
│   ├── rssi_positioning_report.tex    # RSSI 定位报告（LaTeX 源文件）
│   ├── rssi_positioning_report.pdf    # RSSI 定位报告（编译后 PDF，14 页）
│   └── resume_project_draft.md        # 简历项目描述草稿（3 版本 + 追问准备）
│
└── src/
    ├── subproject1_rssi/          # 子项目一
    │   ├── 01_collect_rssi.py     # RSSI 数据采集
    │   ├── 02_path_loss_fit.py    # 路径损耗模型拟合
    │   └── 03_trilateration_kalman.py  # 三边定位 + 卡尔曼滤波 + 评估
    │
    └── subproject2_aoa/           # 子项目二
        ├── 01_signal_model_music.py  # ULA 信号模型 + MUSIC
        ├── 02_esprit.py             # ESPRIT 算法
        └── 03_monte_carlo.py        # 蒙特卡洛评估
```

---

## 3. 快速开始

### 3.1 克隆 + 安装（一条命令链）

```bash
git clone https://github.com/Tjfancy/ble-automotive-key-positioning.git
cd ble-automotive-key-positioning
pip install -r requirements.txt
```

> pip 慢时加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`（清华镜像）。

### 3.2 一键运行

```bash
python run_all.py                    # 完整流程（含蒙特卡洛，约 10 秒）
python run_all.py --skip-mc          # 跳过蒙特卡洛，快速验证
```

### 3.3 单步运行

```bash
# 子项目一
python src/subproject1_rssi/01_collect_rssi.py --synthetic --distance 1.0 --n-samples 80
python src/subproject1_rssi/02_path_loss_fit.py
python src/subproject1_rssi/03_trilateration_kalman.py

# 子项目二
python src/subproject2_aoa/01_signal_model_music.py
python src/subproject2_aoa/02_esprit.py
python src/subproject2_aoa/03_monte_carlo.py
```

### 3.4 真实硬件采集（可选）

```bash
# 手机安装 nRF Connect，开启 Advertiser，广播名设为 "PhoneKey"
python src/subproject1_rssi/01_collect_rssi.py --real --name "PhoneKey" --distance 1.0 --n-samples 80
```

---

## 4. 脚本手册

### 4.1 子项目一：RSSI 定位与滤波

#### `01_collect_rssi.py` — RSSI 数据采集

**作用**：扫描 BLE 广播，记录每个距离位置的 RSSI 样本。

**两种模式**：

| 模式 | 用途 | 硬件需求 |
|------|------|----------|
| `--synthetic` | 用路径损耗模型生成带噪声的仿真数据 | 无 |
| `--real` | 用 bleak 扫描真实 BLE 设备 | 电脑需有 BLE |

**常用参数**：

```bash
--distance 1.0     # 当前采集位置到发射端的距离（米），必填
--n-samples 80     # 每个位置采集的样本数，默认 80
--out data/rssi_raw.csv   # 输出 CSV 路径，默认 data/rssi_raw.csv
--name "PhoneKey" # 真实模式下的设备名过滤（real 模式）
--synthetic       # 使用合成数据模式
--real            # 使用真实扫描模式
```

**输出**：`data/rssi_raw.csv`，列：`distance_m`, `rssi_dbm`, `timestamp`, `name`, `address`。多位置采集时自动追加（不重复写表头）。

**关键函数**：

| 函数 | 作用 |
|------|------|
| `scan_once(duration_s, target_name)` | 异步扫描，返回 (name, rssi, address) 列表 |
| `collect_real(target_name, distance_m, n_samples, ...)` | 真实采集，多轮扫描凑够样本 |
| `collect_synthetic(distance_m, n_samples, ...)` | 合成数据生成 |
| `_append_csv(path, rows)` | 追加写入 CSV，自动判断是否写表头 |

**注意**：
- Windows 上脚本已内置 `WindowsSelectorEventLoopPolicy` 修复 asyncio 报错
- 控制台打印用英文，避免 cp1252 编码报错（`$env:PYTHONIOENCODING="utf-8"` 可省略）
- `import os` 在模块顶部，不在函数内部

---

#### `02_path_loss_fit.py` — 路径损耗模型拟合

**作用**：从 RSSI-距离数据拟合对数距离路径损耗模型，得到 A 和 n。

**模型**：

$$\text{RSSI}(d) = A - 10 \cdot n \cdot \log_{10}(d / d_0), \quad d_0 = 1\text{m}$$

**两种拟合方法**：

| 方法 | 函数 | 原理 |
|------|------|------|
| 线性化最小二乘 | `fit_linear(d, rssi)` | x=log10(d), y=RSSI → 一元线性回归 y = A − 10n·x |
| 非线性最小二乘 | `fit_curve(d, rssi)` | `scipy.optimize.curve_fit` 直接拟合，输出参数不确定度 |

**输出**：
- 终端打印：A, n, R², RMSE, MAE，各位置距离估计误差
- `results/path_loss_fit.png`：散点 + 拟合曲线 + 残差图
- `data/path_loss_params.npz`：保存 A, n, d0, unique_d, median_rssi

**关键函数**：

| 函数 | 作用 |
|------|------|
| `path_loss_model(d, A, n, d0=1.0)` | 模型正向计算 |
| `fit_linear(d, rssi)` | 线性化最小二乘，返回 (A, n) |
| `fit_curve(d, rssi)` | 非线性最小二乘，返回 (A, n, perr) |
| `estimate_distance(rssi, A, n, d0=1.0)` | RSSI → 距离反函数 |
| `evaluate_fit(d, rssi, A, n)` | 返回 R², RMSE, MAE |
| `load_data(csv_path)` | 读取 CSV，返回 (unique_d, median_rssi, all_rssi) |

**注意**：
- 每个距离位置取**中位数**作为代表值（抗多径离群点）
- 采用非线性结果作为最终模型（样本少时更稳健）
- 拟合参数被 `03_trilateration_kalman.py` 读取，改参数会影响定位结果

---

#### `03_trilateration_kalman.py` — 三边定位 + 卡尔曼滤波 + 误差评估

**作用**：模拟目标运动，3 锚点接收 RSSI → 测距 → 三边定位 → 卡尔曼滤波 → 对比原始/滤波定位误差。

**场景设定**（代码硬编码，可改）：

| 参数 | 值 | 含义 |
|------|-----|------|
| 锚点 0 | (0, 0) | 单位 m |
| 锚点 1 | (5, 0) | |
| 锚点 2 | (2.5, 4) | |
| 起点 | (1, 1) | 目标运动起点 |
| 终点 | (4, 2) | 目标运动终点 |
| 步数 | 60 | 仿真时间步数 |
| dt | 1.0 s | 采样间隔 |
| RSSI 噪声 σ | 4.0 dBm | 每步 RSSI 的噪声标准差 |

**关键函数**：

| 函数 | 作用 |
|------|------|
| `trilaterate(anchors, distances)` | 最小二乘三边定位，返回 (pos, resid) |
| `make_kalman_1d(dt, q, r)` | 构造 1D 恒速模型 KalmanFilter |
| `run_simulation(anchors, true_traj, dt, A, n, rssi_sigma, steps, seed)` | 运动仿真 + 滤波对比 |
| `compute_errors(true, est)` | 逐点欧氏误差 |
| `error_metrics(errors)` | mean/median/rmse/p90/p95/max |
| `plot_results(res, out_dir)` | 绘制轨迹对比、CDF、误差 vs 时间 |

**输出**：
- 终端：误差指标对比表（raw vs filt，含改善百分比）
- `results/traj_compare.png`：真实轨迹 / 原始定位 / 滤波定位 / 锚点
- `results/error_cdf.png`：原始 vs 滤波误差 CDF
- `results/error_vs_time.png`：误差随时间变化

**注意**：
- 卡尔曼滤波 Q/R 参数在 `run_simulation` 内部设定：
  - `q_proc = 0.05`：过程噪声（加速度方差），控制平滑度
  - `r_meas`：由 RSSI 噪声经模型传播得到，控制跟踪灵敏度
- 每个锚点独立运行一个 Kalman filter，滤波后再三边定位
- 改锚点坐标、运动轨迹、噪声水平都会影响结果

---

### 4.2 子项目二：BLE AoA 算法仿真

#### `01_signal_model_music.py` — ULA 信号模型 + MUSIC 算法

**作用**：生成均匀线阵接收信号，实现 MUSIC 算法估计入射角。

**信号模型**：

$$X = a(\theta) \cdot s + n$$

导向矢量：$a(\theta) = [1, e^{j\pi\sin\theta}, e^{j2\pi\sin\theta}, \ldots, e^{j(M-1)\pi\sin\theta}]^T$

**MUSIC 算法步骤**：

```
1. R = (1/K)·X·X^H                    协方差矩阵
2. 特征分解 R，特征值降序排列
3. Un = 后 M-p 个特征向量              噪声子空间
4. P(θ) = 1 / (aᴴ(θ)·Un·Unᴴ·a(θ))    MUSIC 空间谱
5. 搜索谱峰 → θ_est
```

**默认参数**（代码硬编码）：

| 参数 | 值 |
|------|-----|
| M | 8 |
| K | 200 |
| θ_true | 30.0° |
| SNR | 10.0 dB |
| 网格步长 | 0.5° |
| 搜索范围 | [-90°, 90°] |

**关键函数**：

| 函数 | 作用 |
|------|------|
| `steering_vector(theta_deg, M, d_over_lambda=0.5)` | 生成导向矢量 a(θ) |
| `generate_signal(theta_deg, M, K, snr_db, d_over_lambda=0.5, seed=None)` | 生成 (M,K) 接收矩阵 X |
| `music_spectrum(X, p=1, theta_grid=None)` | MUSIC 算法，返回 (theta_grid, P, theta_est) |
| `plot_spectrum(...)` | 绘制空间谱图 |

**输出**：
- 终端：估计角度和误差
- `results/music_spectrum.png`：归一化空间谱（dB），标记真值和估计值

**注意**：
- `p` 是信源数，默认 1。改多信源时需同时改 `p` 和信号生成逻辑
- 网格步长 0.5° 限制了高 SNR 下的理论精度
- `generate_signal` 的 `seed` 参数控制随机性，相同 seed 得到相同数据

---

#### `02_esprit.py` — ESPRIT 算法

**作用**：利用阵列旋转不变性，代数求解入射角（无需角度搜索）。

**算法步骤**：

```
1. R = (1/K)·X·X^H，特征分解
2. Es = 前 p 个特征向量                信号子空间 (M×p)
3. Es1 = Es[0:M-1], Es2 = Es[1:M]     子阵划分
4. Ψ = pinv(Es1)·Es2                  求解旋转矩阵
5. λ_k = eigvals(Ψ)                   特征值
6. θ_k = arcsin(angle(λ_k)/π)         反解角度
```

**关键函数**：

| 函数 | 作用 |
|------|------|
| `esprit_estimate(X, p=1, d_over_lambda=0.5)` | ESPRIT 算法，返回角度估计（度） |

**输出**：
- 终端：单次估计值 + 50 次实验的 mean/std/RMSE

**注意**：
- 复用 `01_signal_model_music.py` 的信号生成（通过 importlib 动态加载，因为文件名以数字开头）
- 子阵划分损失 1 个阵元自由度（M 元阵实际用 M-1 元做估计）
- 低 SNR 时稳定性略逊 MUSIC

---

#### `03_monte_carlo.py` — 蒙特卡洛评估

**作用**：扫描 SNR 和阵元数，批量运行 MUSIC 和 ESPRIT，统计 RMSE，绘制对比曲线。

**实验设计**（代码硬编码，可改）：

| 参数 | 值 |
|------|-----|
| θ_true | 30.0°（固定） |
| K | 200（固定） |
| SNR 列表 | [-10, -5, 0, 5, 10, 15, 20, 25, 30] dB |
| M 列表 | [4, 8, 16] |
| 每组试验次数 | 50 |
| 总实验组数 | 9 × 3 = 27 |

**关键函数**：

| 函数 | 作用 |
|------|------|
| `run_monte_carlo(theta_true, K, snr_list, M_list, n_trials, seed_start)` | 运行全部实验 |
| `compute_rmse_table(results)` | 计算每组的 RMSE |
| `plot_rmse_vs_snr(results, M_list, out_path)` | RMSE vs SNR 图 |
| `plot_rmse_vs_M(results, snr_list, out_path)` | RMSE vs M 图 |

**输出**：
- 终端：每组实验的 MUSIC/ESPRIT RMSE，关键结论摘要
- `results/mc_rmse_vs_snr.png`：6 条曲线（MUSIC/ESPRIT × M=4,8,16）
- `results/mc_rmse_vs_M.png`：多条曲线（不同 SNR）
- `data/mc_results.npz`：所有原始误差数据

**注意**：
- 改 SNR 范围、M 取值、试验次数都在 `main()` 函数开头改
- 同一 seed 序列保证实验可复现
- 蒙特卡洛约 4 秒完成 27 组，`run_all.py --skip-mc` 可跳过

---

## 5. 关键参数含义

### 5.1 子项目一参数

| 参数 | 含义 | 默认值 | 改了会怎样 |
|------|------|--------|-----------|
| A | 1m 参考距离处的 RSSI（dBm） | -39.4（拟合得到） | 反映发射功率；A 变大 → 同距离 RSSI 变大 → 测距偏小 |
| n | 路径损耗指数 | 3.02（拟合得到） | 自由空间≈2，室内≈3~4；n 变大 → 衰减变快 → 远距离测距偏小 |
| σ_RSSI | RSSI 噪声标准差 | 4.0 dBm | 实测典型值 3~5；越大 → 测距越不稳定 → 定位误差越大 |
| 锚点坐标 | 3 个锚点的 (x,y) | (0,0),(5,0),(2.5,4) | 改变几何布局 → 影响 GDOP → 定位精度变化 |
| q_proc | 卡尔曼过程噪声 | 0.05 | 大 → 平滑但迟钝；小 → 跟踪快但噪声大 |
| r_meas | 卡尔曼测量噪声 | 由 σ_RSSI 推导 | 大 → 信任模型；小 → 信任测量 |

### 5.2 子项目二参数

| 参数 | 含义 | 默认值 | 改了会怎样 |
|------|------|--------|-----------|
| M | 阵元数 | 4, 8, 16 | 越多 → 阵列孔径越大 → 分辨率越高 → RMSE 越小 |
| θ_true | 真实入射角 | 30.0° | 待估计量；接近端射（±90°）时精度下降 |
| K | 快照数 | 200 | 越多 → 协方差估计越准 → RMSE 越小，但采集时间变长 |
| SNR | 信噪比 | -10~30 dB | 越高 → 噪声越小 → RMSE 越小；<0dB 时误差急剧恶化 |
| p | 信源数 | 1 | 改多信源需同时改信号生成和算法 |
| d/λ | 阵元间距/波长 | 0.5 (λ/2) | 避免栅瓣；改大可能出现角度模糊 |
| 网格步长 | MUSIC 角度搜索步长 | 0.5° | 越小精度越高但计算量越大 |

---

## 6. 实验结果

### 6.1 子项目一结论

| 指标 | 原始定位 | 卡尔曼滤波 | 改善 |
|------|---------|-----------|------|
| 平均误差 | 0.98 m | 0.62 m | **36.8%** |
| P90 误差 | 1.78 m | 1.04 m | 41.7% |
| RMSE | 1.20 m | 0.83 m | 30.5% |

**核心结论**：卡尔曼滤波显著平滑定位轨迹，平均误差降低约 37%，P90 误差降低约 42%。

### 6.2 子项目二结论

| 规律 | 说明 |
|------|------|
| **SNR 提升改善精度** | -10dB → 0dB 精度急剧提升，>10dB 后饱和（阈值效应） |
| **MUSIC 低 SNR 更优** | -10dB 时 MUSIC RMSE 明显小于 ESPRIT（噪声子空间约束更强） |
| **阵元数越多精度越高** | M: 4→16，低 SNR 下 MUSIC RMSE 从 2.74° 降至 0.31°（改善 89%） |
| **ESPRIT 无需搜索** | 计算量小 O(M³)，适合实时系统，高 SNR 下无网格分辨率限制 |

---

## 7. 可拓展方向

### 7.1 子项目一

| 方向 | 说明 |
|------|------|
| 多锚点定位 | 从 3 锚点扩展到 4+ 锚点，用最小二乘超定方程求解 |
| EKF 融合 | 从 1D 卡尔曼升级到扩展卡尔曼，融合 RSSI + 惯导 |
| 真实数据采集 | 用 `--real` 模式采集手机广播的真实 RSSI |
| GDOP 分析 | 计算几何精度因子，优化锚点布局 |
| 滤波调参自动化 | Allan 方差法或网格搜索自动确定 Q/R |

### 7.2 子项目二

| 方向 | 说明 |
|------|------|
| 多信源（p>1） | 需信源数估计（AIC/MDL 准则）+ 多谱峰配对 |
| 相干信源 | 需空间平滑（SS-MUSIC）或最大似然（ML） |
| TLS-ESPRIT | 总最小二乘版本，低 SNR 更稳健 |
| 2D AoA | 均匀圆阵（UCA）或均匀面阵（URA），估计方位角 + 仰角 |
| 多径效应 | 信号模型从单径扩展到多径 |
| 真实硬件 | nRF53/54 + QM33110 天线阵列采集 I/Q 数据 |

---

## 8. 接管指南

### 8.1 环境要求

- Python 3.9+
- 已安装的依赖：numpy, scipy, matplotlib, bleak, filterpy（`pip install -r requirements.txt`）
- LaTeX（可选，仅用于重新编译 `docs/` 下的两份 PDF 报告）：需 `xelatex`（MiKTeX 自带 ctex 包）

### 8.2 常见修改场景

**场景 A：改实验参数重跑**

```bash
# 子项目一：改锚点坐标 → 编辑 03_trilateration_kalman.py 的 anchors 变量
# 子项目一：改 RSSI 噪声 → 编辑 03_trilateration_kalman.py 的 rssi_sigma 变量
# 子项目二：改 SNR/M 范围 → 编辑 03_monte_carlo.py 的 snr_list 和 M_list
# 子项目二：改入射角 → 编辑各脚本的 theta_true 变量
```

**场景 B：换真实数据**

```bash
# 1. 用 --real 模式采集 RSSI
python src/subproject1_rssi/01_collect_rssi.py --real --distance 0.5 --n-samples 80
# 2. 直接跑拟合和定位（自动读取 data/rssi_raw.csv）
python src/subproject1_rssi/02_path_loss_fit.py
python src/subproject1_rssi/03_trilateration_kalman.py
```

**场景 C：重新编译 LaTeX 报告**

```bash
cd docs
# 子项目一：RSSI 定位报告
xelatex -interaction=nonstopmode rssi_positioning_report.tex   # 跑两次
xelatex -interaction=nonstopmode rssi_positioning_report.tex

# 子项目二：AoA 报告
xelatex -interaction=nonstopmode aoa_simulation_report.tex    # 跑两次
xelatex -interaction=nonstopmode aoa_simulation_report.tex
```

### 8.3 已知问题和注意事项

| 问题 | 说明 |
|------|------|
| 控制台中文编码 | Windows 控制台默认 cp1252，打印中文会报错。脚本已改为英文输出，或用 `$env:PYTHONIOENCODING="utf-8"` |
| Python 模块名以数字开头 | `01_signal_model_music.py` 等无法用普通 import 加载，`02_esprit.py` 和 `03_monte_carlo.py` 用 `importlib.util` 动态加载 |
| `&&` 不可用 | Windows PowerShell 不支持 `&&`，用 `;` 分隔命令 |
| `tail`/`grep`/`head`/`wc` 不可用 | 这些是 Linux 命令，PowerShell 中用 `Select-String`、`Get-Content` 等替代 |
| pip 慢 | 用 `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| LaTeX 编译 | 必须用 `xelatex`（不能用 `pdflatex`），因为报告是中文的 |
| 蒙特卡洛随机性 | `seed_start=0` 控制，相同参数可复现 |

### 8.4 项目所有者信息

- GitHub 用户名：`Tjfancy`
- Git 配置：LiangFeng <feng.liang@iav.cn>
- 仓库：`https://github.com/Tjfancy/ble-automotive-key-positioning`

---

## 9. 详细报告（LaTeX PDF）

两个子项目各有一份独立的详细报告，包含完整的公式推导、算法步骤、实验数据分析和可拓展方向。适合面试前系统复习或直接打印。

| 报告 | 源文件 | 编译后 PDF | 页数 |
|------|--------|-----------|------|
| 子项目一：RSSI 定位与滤波 | `docs/rssi_positioning_report.tex` | `docs/rssi_positioning_report.pdf` | 14 页 |
| 子项目二：BLE AoA 算法仿真 | `docs/aoa_simulation_report.tex` | `docs/aoa_simulation_report.pdf` | 12 页 |

### 报告覆盖内容

**子项目一报告**（9 章）：
数据采集 → 路径损耗模型（A, n 拟合）→ 三边定位（最小二乘）→ 卡尔曼滤波（1D 恒速模型 + Q/R 调参）→ 实验结果（轨迹/CDF/误差 vs 时间）→ 可拓展方向 → 代码导航

**子项目二报告**（7 章）：
信号模型（导向矢量 + SNR 推导）→ MUSIC 算法（噪声子空间正交性）→ ESPRIT 算法（旋转不变性）→ 蒙特卡洛评估（27 组实验 + RMSE 曲线）→ 可拓展方向 → 代码导航

### 重新编译

```bash
cd docs
xelatex -interaction=nonstopmode rssi_positioning_report.tex   # 跑两次
xelatex -interaction=nonstopmode rssi_positioning_report.tex
xelatex -interaction=nonstopmode aoa_simulation_report.tex    # 跑两次
xelatex -interaction=nonstopmode aoa_simulation_report.tex
```

> 注意：图片路径在 `../results/`（LaTeX 在 docs/ 目录编译），已内置。必须用 `xelatex`（不能用 `pdflatex`），因为报告是中文的。

---

*最后更新：2026-08-24 | commit `4d1ce2c` | 本文档面向无上下文的 AI 接管者*