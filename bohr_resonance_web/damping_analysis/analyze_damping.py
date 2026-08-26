"""阻尼电流平方与阻尼系数关系的拟合、绘图和结果导出。"""

from __future__ import annotations

import sys
from dataclasses import dataclass
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
    load_damping_measurements,
)
from config import (
    DAMPING_DATA_FILE,
    DAMPING_OUTPUT_DIR,
    FIGURE_SIZE,
    PLOT_DPI,
    SHEET_NAME,
    SHOW_PLOTS,
    TARGET_DAMPING_CURRENT_A,
)


@dataclass(frozen=True)
class DampingFitResult:
    slope_k: float
    intercept_beta0: float
    r_squared: float


def load_damping_data(file_path: Path = DAMPING_DATA_FILE) -> pd.DataFrame:
    return load_damping_measurements(file_path, SHEET_NAME)


def calculate_current_squared(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    result["Id_squared_A2"] = np.square(result["Id_A"].to_numpy(dtype=float))
    return result


def calculate_r_squared(observed: np.ndarray, fitted: np.ndarray) -> float:
    residual_sum = float(np.sum(np.square(observed - fitted)))
    total_sum = float(np.sum(np.square(observed - np.mean(observed))))
    if np.isclose(total_sum, 0.0):
        raise ValueError("所有阻尼系数均相同，无法计算 R²。")
    return 1.0 - residual_sum / total_sum


def fit_damping_model(data: pd.DataFrame) -> tuple[pd.DataFrame, DampingFitResult]:
    if len(data) < 2:
        raise ValueError("阻尼拟合至少需要 2 个有效数据点。")

    x = data["Id_squared_A2"].to_numpy(dtype=float)
    y = data["beta_s-1"].to_numpy(dtype=float)
    if np.unique(x).size < 2:
        raise ValueError("阻尼电流平方至少需要两个不同取值。")

    slope_k, intercept_beta0 = np.polyfit(x, y, 1)
    fitted = slope_k * x + intercept_beta0
    r_squared = calculate_r_squared(y, fitted)

    result = data.copy()
    result["beta_fit_s-1"] = fitted
    result["residual"] = y - fitted
    return result, DampingFitResult(
        slope_k=float(slope_k),
        intercept_beta0=float(intercept_beta0),
        r_squared=float(r_squared),
    )


def _equation_text(fit: DampingFitResult) -> str:
    sign = "+" if fit.intercept_beta0 >= 0 else "-"
    return (
        rf"$\beta={fit.slope_k:.4f}I_d^2{sign}{abs(fit.intercept_beta0):.4f}$"
        "\n"
        rf"$R^2={fit.r_squared:.4f}$"
    )


def plot_damping_relation(
    data: pd.DataFrame,
    fit: DampingFitResult,
    output_dir: Path = DAMPING_OUTPUT_DIR,
) -> tuple[Path, Path]:
    configure_matplotlib_chinese_font()
    output_dir.mkdir(parents=True, exist_ok=True)

    x = data["Id_squared_A2"].to_numpy(dtype=float)
    y = data["beta_s-1"].to_numpy(dtype=float)
    x_line = np.linspace(float(x.min()), float(x.max()), 300)
    y_line = fit.slope_k * x_line + fit.intercept_beta0

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    ax.set_facecolor("white")
    ax.scatter(x, y, s=48, color="#2F6B8A", edgecolor="white", linewidth=0.7,
               zorder=3, label="实验数据")
    ax.plot(x_line, y_line, color="#C56A32", linewidth=2.0, label="线性最小二乘拟合")
    ax.text(0.04, 0.95, _equation_text(fit), transform=ax.transAxes, va="top",
            fontsize=11, bbox={"boxstyle": "round,pad=0.35", "facecolor": "white",
                               "edgecolor": "#AAB7C4", "alpha": 0.92})
    ax.set_xlabel(r"阻尼电流平方 $I_d^2$ (A$^2$)", fontsize=12)
    ax.set_ylabel(r"阻尼系数 $\beta$ (s$^{-1}$)", fontsize=12)
    ax.set_title("阻尼系数与阻尼电流平方的关系", fontsize=14, pad=12)
    ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.45)
    ax.legend(frameon=True)
    ax.tick_params(labelsize=10)
    fig.tight_layout()

    png_path = output_dir / "01_damping_beta_vs_current_squared.png"
    pdf_path = output_dir / "01_damping_beta_vs_current_squared.pdf"
    fig.savefig(png_path, dpi=PLOT_DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    if not SHOW_PLOTS:
        plt.close(fig)
    return png_path, pdf_path


def run_damping_analysis(
    data_file: Path = DAMPING_DATA_FILE,
    output_dir: Path = DAMPING_OUTPUT_DIR,
) -> tuple[pd.DataFrame, DampingFitResult, float]:
    data = calculate_current_squared(load_damping_data(data_file))
    processed, fit = fit_damping_model(data)
    measured_beta = get_beta_at_current(processed, TARGET_DAMPING_CURRENT_A)

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "damping_processed.csv"
    processed[["Id_A", "Id_squared_A2", "beta_s-1", "beta_fit_s-1", "residual"]].to_csv(
        csv_path, index=False, encoding="utf-8-sig"
    )
    png_path, pdf_path = plot_damping_relation(processed, fit, output_dir)

    sign = "+" if fit.intercept_beta0 >= 0 else "-"
    print("\n========== 阻尼振动拟合结果 ==========")
    print(f"数据点数：{len(processed)}")
    print(f"拟合斜率 k：{fit.slope_k:.8f} A^-2 s^-1")
    print(f"拟合截距 beta0：{fit.intercept_beta0:.8f} s^-1")
    print(
        f"拟合方程：beta = {fit.slope_k:.4f} Id^2 "
        f"{sign} {abs(fit.intercept_beta0):.4f}"
    )
    print(f"R²：{fit.r_squared:.8f}")
    print(f"300 mA 对应的实测 beta：{measured_beta:.6f} s^-1")
    print(f"处理结果：{csv_path}")
    print(f"图像：{png_path}")
    print(f"矢量图：{pdf_path}")
    print("=====================================\n")
    return processed, fit, measured_beta


def main() -> None:
    configure_console_utf8()
    run_damping_analysis()
    if SHOW_PLOTS:
        print("已打开图像窗口；关闭图像窗口后程序结束。")
        plt.show()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"阻尼振动数据处理失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
