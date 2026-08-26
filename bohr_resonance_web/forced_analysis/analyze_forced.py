"""受迫振动幅频、相频特性的计算、绘图和结果导出。"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common.data_utils import (
    configure_console_utf8,
    configure_matplotlib_chinese_font,
    get_beta_at_current,
    load_forced_measurements,
)
from config import (
    DAMPING_DATA_FILE,
    FIGURE_SIZE,
    FORCED_DATA_FILE,
    FORCED_OUTPUT_DIR,
    PLOT_DPI,
    SHEET_NAME,
    SHOW_PLOTS,
    TARGET_DAMPING_CURRENT_A,
)


def load_forced_data(file_path: Path = FORCED_DATA_FILE) -> pd.DataFrame:
    return load_forced_measurements(file_path, SHEET_NAME)


def find_omega0_from_peak(data: pd.DataFrame) -> tuple[float, float, int]:
    if data.empty:
        raise ValueError("受迫振动数据为空。")
    if data["amplitude_deg"].nunique(dropna=False) <= 1:
        raise ValueError("所有振幅相同，无法由最大振幅点唯一确定 omega0。")

    peak_index = int(data["amplitude_deg"].idxmax())
    omega0 = float(data.loc[peak_index, "omega_rad_s"])
    amplitude_max = float(data.loc[peak_index, "amplitude_deg"])
    if np.isclose(omega0, 0.0):
        raise ValueError("最大振幅点对应的 omega0 为零，无法计算频率比。")
    return omega0, amplitude_max, peak_index


def calculate_frequency_ratio(data: pd.DataFrame, omega0: float) -> pd.DataFrame:
    if np.isclose(omega0, 0.0):
        raise ValueError("omega0 为零，无法计算 omega/omega0。")
    result = data.copy()
    result["omega_ratio"] = result["omega_rad_s"].to_numpy(dtype=float) / omega0
    return result


def calculate_phase_difference(data: pd.DataFrame, beta: float, omega0: float) -> pd.DataFrame:
    """用 atan2 正确处理高频区相位所在象限。"""
    omega = data["omega_rad_s"].to_numpy(dtype=float)
    phase_rad = np.arctan2(-2.0 * beta * omega, omega0**2 - omega**2)
    result = data.copy()
    result["phase_rad"] = phase_rad
    result["phase_pi"] = phase_rad / np.pi
    return result


def plot_amplitude_frequency(
    data: pd.DataFrame,
    omega0: float,
    amplitude_max: float,
    output_dir: Path = FORCED_OUTPUT_DIR,
) -> tuple[Path, Path]:
    configure_matplotlib_chinese_font()
    output_dir.mkdir(parents=True, exist_ok=True)
    ordered = data.sort_values("omega_ratio")

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    ax.set_facecolor("white")
    ax.plot(ordered["omega_ratio"], ordered["amplitude_deg"], color="#2F6B8A",
            linewidth=1.8, marker="o", markersize=5.5, markerfacecolor="white",
            markeredgewidth=1.2, label="实验数据")
    ax.axvline(1.0, color="#8796A5", linewidth=1.1, linestyle="--",
               label=r"$\omega/\omega_0=1$")
    ax.scatter([1.0], [amplitude_max], s=62, color="#C56A32", zorder=4,
               label="共振点")
    ax.annotate(
        f"Resonance point\n$\\omega_0$ = {omega0:.2f} rad/s\n"
        f"$\\theta_{{max}}$ = {amplitude_max:.1f}°",
        xy=(1.0, amplitude_max), xytext=(18, -58), textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": "#566573"}, fontsize=10,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.9,
              "edgecolor": "#AAB7C4"},
    )
    ax.set_xlabel(r"无量纲频率比 $\omega/\omega_0$", fontsize=12)
    ax.set_ylabel(r"稳态振幅 $\theta$ (deg)", fontsize=12)
    ax.set_title("受迫振动幅频特性", fontsize=14, pad=12)
    ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.45)
    ax.legend(frameon=True)
    ax.tick_params(labelsize=10)
    fig.tight_layout()

    png_path = output_dir / "02_forced_amplitude_frequency.png"
    pdf_path = output_dir / "02_forced_amplitude_frequency.pdf"
    fig.savefig(png_path, dpi=PLOT_DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    if not SHOW_PLOTS:
        plt.close(fig)
    return png_path, pdf_path


def plot_phase_frequency(
    data: pd.DataFrame,
    output_dir: Path = FORCED_OUTPUT_DIR,
) -> tuple[Path, Path]:
    configure_matplotlib_chinese_font()
    output_dir.mkdir(parents=True, exist_ok=True)
    ordered = data.sort_values("omega_ratio")

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    ax.set_facecolor("white")
    ax.plot(ordered["omega_ratio"], ordered["phase_pi"], color="#486F55",
            linewidth=1.8, marker="o", markersize=5.5, markerfacecolor="white",
            markeredgewidth=1.2, label="计算相位差")
    ax.axvline(1.0, color="#8796A5", linewidth=1.1, linestyle="--",
               label=r"$\omega/\omega_0=1$")
    ax.axhline(-0.5, color="#AAB7C4", linewidth=1.1, linestyle=":",
               label=r"$\varphi/\pi=-0.5$")
    ax.scatter([1.0], [-0.5], s=58, color="#C56A32", zorder=4)
    ax.annotate("(1, -0.5)", xy=(1.0, -0.5), xytext=(12, 12),
                textcoords="offset points", fontsize=10,
                arrowprops={"arrowstyle": "->", "color": "#566573"})
    ax.set_xlabel(r"无量纲频率比 $\omega/\omega_0$", fontsize=12)
    ax.set_ylabel(r"相位差 $\varphi/\pi$", fontsize=12)
    ax.set_title("受迫振动相频特性", fontsize=14, pad=12)
    ax.set_ylim(min(-1.03, float(ordered["phase_pi"].min()) - 0.04),
                max(0.03, float(ordered["phase_pi"].max()) + 0.04))
    ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.45)
    ax.legend(frameon=True)
    ax.tick_params(labelsize=10)
    fig.tight_layout()

    png_path = output_dir / "03_forced_phase_frequency.png"
    pdf_path = output_dir / "03_forced_phase_frequency.pdf"
    fig.savefig(png_path, dpi=PLOT_DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    if not SHOW_PLOTS:
        plt.close(fig)
    return png_path, pdf_path


def _print_phase_checkpoints(data: pd.DataFrame, peak_index: int) -> None:
    indices = [int(data["omega_rad_s"].idxmin()), peak_index, int(data["omega_rad_s"].idxmax())]
    print("相位数值检查：")
    for index in dict.fromkeys(indices):
        row = data.loc[index]
        print(
            f"  omega = {row['omega_rad_s']:.2f} rad/s -> "
            f"phi/pi = {row['phase_pi']:.5f}"
        )


def run_forced_analysis(
    forced_data_file: Path = FORCED_DATA_FILE,
    damping_data_file: Path = DAMPING_DATA_FILE,
    output_dir: Path = FORCED_OUTPUT_DIR,
) -> tuple[pd.DataFrame, float, float]:
    beta = get_beta_at_current(damping_data_file, TARGET_DAMPING_CURRENT_A, SHEET_NAME)
    data = load_forced_data(forced_data_file)
    omega0, amplitude_max, peak_index = find_omega0_from_peak(data)
    processed = calculate_frequency_ratio(data, omega0)
    processed = calculate_phase_difference(processed, beta, omega0)

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "forced_processed.csv"
    processed[[
        "drive_frequency_label", "omega_rad_s", "omega_ratio", "amplitude_deg",
        "phase_rad", "phase_pi",
    ]].to_csv(csv_path, index=False, encoding="utf-8-sig")
    amplitude_png, amplitude_pdf = plot_amplitude_frequency(
        processed, omega0, amplitude_max, output_dir
    )
    phase_png, phase_pdf = plot_phase_frequency(processed, output_dir)

    print("\n========== 受迫振动参数 ==========")
    print(f"阻尼数据文件：{damping_data_file}")
    print(f"受迫振动数据文件：{forced_data_file}")
    print(f"受迫振动实验阻尼电流：Id = {TARGET_DAMPING_CURRENT_A:.3f} A")
    print(f"从阻尼原始数据读取：beta = {beta:.6f} s^-1")
    print(f"最大振幅：theta_max = {amplitude_max:.1f} deg")
    print(f"最大振幅对应角频率：omega0 = {omega0:.2f} rad/s")
    print("=================================")
    _print_phase_checkpoints(processed, peak_index)
    print(f"处理结果：{csv_path}")
    print(f"幅频图：{amplitude_png}")
    print(f"幅频矢量图：{amplitude_pdf}")
    print(f"相频图：{phase_png}")
    print(f"相频矢量图：{phase_pdf}\n")
    return processed, beta, omega0


def main() -> None:
    configure_console_utf8()
    run_forced_analysis()
    if SHOW_PLOTS:
        print("已打开图像窗口；关闭所有图像窗口后程序结束。")
        plt.show()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"受迫振动数据处理失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
