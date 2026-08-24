# BLE 汽车数字钥匙定位技术原型与算法评估

> 面向汽车数字钥匙（CCC/ICCE 标准）的 BLE 定位技术完整闭环项目。
> 从真实 RSSI 采集 → 测距建模 → 三边定位 → 卡尔曼滤波 → AoA 仿真 → MUSIC/ESPRIT → 蒙特卡洛评估。

## 项目概览

本项目将实习期间对 BLE AoA / UWB 数字钥匙技术的调研，转化为**可运行代码 + 实验数据 + 可视化结论**的完整作品，用于秋招面试展示。

**硬件约束**：不购买额外硬件，仅用手机（nRF Connect 广播）+ 电脑（Python 扫描/仿真）。

**技术栈**：Python 3.9+ / numpy / scipy / matplotlib / bleak / filterpy

### 项目结构

```
ble-automotive-key-positioning/
├── README.md
├── requirements.txt
├── data/                # 采集的 RSSI 数据 + 拟合参数 + 蒙特卡洛原始结果
├── results/             # 实验图表
├── docs/                # 补充文档（简历描述草稿）
└── src/
    ├── subproject1_rssi/          # 子项目一：BLE RSSI 定位与滤波
    │   ├── 01_collect_rssi.py     #   RSSI 数据采集（真实/合成）
    │   ├── 02_path_loss_fit.py    #   对数距离路径损耗模型拟合
    │   └── 03_trilateration_kalman.py  # 三边定位 + 卡尔曼滤波 + 误差评估
    └── subproject2_aoa/           # 子项目二：BLE AoA 算法仿真
        ├── 01_signal_model_music.py  # ULA 信号模型 + MUSIC 算法
        ├── 02_esprit.py             # ESPRIT 算法
        └── 03_monte_carlo.py        # 蒙特卡洛评估（SNR/阵元数）
```

---

## 子项目一：BLE RSSI 定位与滤波（基于真实数据）

### 1.1 数据采集

手机安装 nRF Connect 开启 Advertiser 模式（广播名 "PhoneKey"），电脑用 `bleak` 扫描。

**采集方案**：在 0.5 / 1 / 1.5 / 2 / 3 / 4 / 5 m 等位置，每位置采集 80 个 RSSI 样本，记录到 `data/rssi_raw.csv`。

脚本 `01_collect_rssi.py` 支持两种模式：
- `--real`：真实 BLE 扫描（需电脑有 BLE 且手机在广播）
- `--synthetic`：用路径损耗模型生成等效仿真数据（无硬件时跑通流水线）

```bash
# 真实采集
python src/subproject1_rssi/01_collect_rssi.py --real --name "PhoneKey" --distance 1.0 --n-samples 80

# 合成数据（无硬件）
python src/subproject1_rssi/01_collect_rssi.py --synthetic --distance 1.0 --n-samples 80
```

### 1.2 路径损耗模型拟合

对数距离路径损耗模型：

$$\text{RSSI}(d) = A - 10 \cdot n \cdot \log_{10}(d / d_0), \quad d_0 = 1\,\text{m}$$

- **A**：1m 参考距离处的 RSSI（dBm），反映发射功率与天线增益
- **n**：路径损耗指数（自由空间≈2，室内≈3~4）

脚本 `02_path_loss_fit.py` 实现两种拟合：
1. **线性化最小二乘**：令 x=log10(d)，y=RSSI，一元线性回归 y = A − 10n·x
2. **非线性最小二乘**：`scipy.optimize.curve_fit` 直接拟合非线性模型，输出参数不确定度

**拟合结果**（合成数据，真值 A=-40, n=3.0）：

| 参数 | 真值 | 拟合值 | R² | RMSE |
|------|------|--------|-----|------|
| A (dBm) | -40 | -39.51 | 1.0000 | 0.0011 dBm |
| n | 3.0 | 3.000 | | |

距离估计函数：$d = 10^{(A - \text{RSSI}) / (10n)}$

输出图表：`results/path_loss_fit.png`（散点 + 拟合曲线 + 残差）

### 1.3 三边定位 + 卡尔曼滤波

**三边定位**：3 个已知锚点，用最小二乘解算二维坐标。以锚点 0 为参考消去二次项，得线性方程组 A·[x,y] = b，`np.linalg.lstsq` 求解。

**卡尔曼滤波**（filterpy，1D 恒速模型）：
- 状态 x = [距离, 速度]ᵀ
- 过程噪声 Q 由加速度不确定度 q 控制（控制平滑度）
- 测量噪声 R 由 RSSI 噪声经模型传播得到（控制跟踪灵敏度）
- 每个锚点独立运行一个 Kalman filter，滤波后再三边定位

脚本 `03_trilateration_kalman.py`：目标沿直线匀速运动 60 步，每步 3 锚点各收到带噪声 RSSI。

**定位误差对比**（目标从 (1,1)→(4,2)，RSSI 噪声 σ=4 dBm）：

| 指标 | 原始定位 | 卡尔曼滤波 | 改善 |
|------|---------|-----------|------|
| 平均误差 | 0.987 m | 0.623 m | **36.9%** |
| 中位误差 | 0.854 m | 0.510 m | 40.3% |
| P90 误差 | 1.799 m | 1.046 m | 41.8% |
| RMSE | 1.211 m | 0.841 m | 30.6% |

输出图表：
- `results/traj_compare.png` — 定位轨迹对比
- `results/error_cdf.png` — 误差 CDF 曲线
- `results/error_vs_time.png` — 误差随时间变化

---

## 子项目二：BLE AoA 算法仿真（纯软件）

### 2.1 信号模型

均匀线阵（ULA），M 个阵元，阵元间距 d = λ/2，载波 2.4 GHz。远场单源入射。

导向矢量：

$$a(\theta) = [1, e^{j\pi\sin\theta}, e^{j2\pi\sin\theta}, \ldots, e^{j(M-1)\pi\sin\theta}]^T$$

接收信号（K 快照）：X = a(θ)·s + n，n ~ CN(0, σ²I)

脚本 `01_signal_model_music.py` 实现信号生成，支持可调 SNR、阵元数、入射角。

### 2.2 MUSIC 算法

1. 协方差矩阵 R = (1/K)·X·Xᴴ
2. 特征分解，按特征值降序排列
3. 噪声子空间 Un = 后 M−p 个特征向量（p=信源数）
4. 空间谱：P_MUSIC(θ) = 1 / (aᴴ(θ)·Un·Unᴴ·a(θ))
5. 谱峰搜索 → 角度估计

**验证**：M=8, K=200, SNR=10 dB, θ=30° → 估计 30.000°，误差 0.000°
输出图表：`results/music_spectrum.png`

### 2.3 ESPRIT 算法

利用阵列旋转不变性：前 M−1 阵元与后 M−1 阵元子阵满足 Es2 = Es1·Ψ。
对 Ψ 特征分解，特征值 λ_k = exp(jπ·sinθ_k)，直接代数求解角度。

脚本 `02_esprit.py`：**验证** M=8, SNR=10 dB → 估计 30.006°，50 次实验 RMSE=0.055°

### 2.4 蒙特卡洛评估

实验设计：θ_true=30°, K=200 快照，扫描 SNR∈[-10,30] dB、M∈{4,8,16}，每组 50 次独立试验。

脚本 `03_monte_carlo.py` 输出：

**关键结果**：

| M | SNR=-10 (MUSIC/ESPRIT) | SNR=30 (MUSIC/ESPRIT) |
|---|------------------------|------------------------|
| 4 | 2.74° / 3.64° | 0.00° / 0.02° |
| 8 | 0.78° / 1.18° | 0.00° / 0.01° |
| 16 | 0.31° / 0.50° | 0.00° / 0.00° |

**结论**：
1. **SNR 提升显著改善精度**：从 -10 到 0 dB 精度急剧提升，>10 dB 后趋于饱和
2. **阵元数越多精度越高**：M 从 4→16，低 SNR 下精度提升约 9 倍（2.74°→0.31°）
3. **MUSIC 在低 SNR 下优于 ESPRIT**（噪声子空间约束更强），高 SNR 两者接近
4. ESPRIT 无需角度搜索，计算量小，适合实时系统

输出图表：
- `results/mc_rmse_vs_snr.png` — RMSE vs SNR
- `results/mc_rmse_vs_M.png` — RMSE vs 阵元数

---

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 子项目一：RSSI 定位
python src/subproject1_rssi/01_collect_rssi.py --synthetic --distance 1.0 --n-samples 80
python src/subproject1_rssi/02_path_loss_fit.py
python src/subproject1_rssi/03_trilateration_kalman.py

# 子项目二：AoA 仿真
python src/subproject2_aoa/01_signal_model_music.py
python src/subproject2_aoa/02_esprit.py
python src/subproject2_aoa/03_monte_carlo.py
```

> 注：Windows 上若遇 asyncio 策略报错，脚本已内置 `WindowsSelectorEventLoopPolicy` 修复。

---

## 面试讲解要点

1. **从 RSSI 到距离**：对数距离模型的物理意义（A=参考值，n=环境因子），线性化最小二乘 vs 非线性拟合的适用场景
2. **三边定位**：为什么用最小二乘而非解析解（锚点>3 时超定），几何精度因子（GDOP）概念可拓展
3. **卡尔曼滤波**：Q/R 调参直觉（Q 大→平滑但迟钝，R 大→跟踪但噪声大），滤波对离群点的局限
4. **MUSIC vs ESPRIT**：子空间分解的核心思想，噪声子空间正交性，ESPRIT 的旋转不变性优势
5. **实验设计**：控制变量法（固定 K，扫 SNR 和 M），RMSE 作为精度指标，饱和效应的物理解释

---

## 后续可拓展方向

- 多信源（p>1）MUSIC/ESPRIT + 信源数估计（AIC/MDL 准则）
- 均匀圆阵（UCA）/ 均面阵（URA）的 2D AoA 估计
- RSSI 与 AoA 融合定位（扩展卡尔曼滤波 EKF）
- 真实硬件实验：BLE AoA 芯片（如 nRF53/54 + QM33110）的 I/Q 数据采集
- 定位精度与数字钥匙安全（中继攻击防护）的关联讨论