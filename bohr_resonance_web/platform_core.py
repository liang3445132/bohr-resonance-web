"""网页平台使用的纯数据处理服务：读取上传文件、计算、绘图并返回内存文件。"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common.data_utils import (
    configure_matplotlib_chinese_font,
    get_beta_at_current,
    load_damping_measurements,
    load_forced_measurements,
)
from damping_analysis.analyze_damping import (
    DampingFitResult,
    calculate_current_squared,
    fit_damping_model,
)
from decay_analysis.analyze_decay import DecayFitResult, fit_decay_model, load_decay_csv
from forced_analysis.analyze_forced import (
    calculate_frequency_ratio,
    calculate_phase_difference,
    find_omega0_from_peak,
)


@dataclass(frozen=True)
class DampingPlatformResult:
    source_name: str
    processed: pd.DataFrame
    fit: DampingFitResult
    beta_at_0300: float | None
    plot_png: bytes
    processed_csv: bytes


@dataclass(frozen=True)
class ForcedPlatformResult:
    source_name: str
    processed: pd.DataFrame
    beta: float
    omega0: float
    amplitude_max: float
    amplitude_png: bytes
    phase_png: bytes
    processed_csv: bytes


@dataclass(frozen=True)
class DecayPlatformResult:
    source_name: str
    processed: pd.DataFrame
    fit: DecayFitResult
    plot_png: bytes
    processed_csv: bytes


def _temporary_excel_path(payload: bytes, file_name: str) -> tuple[TemporaryDirectory, Path]:
    if not payload:
        raise ValueError("上传的 Excel 文件为空。")
    suffix = Path(file_name).suffix.lower()
    if suffix != ".xlsx":
        raise ValueError("当前平台仅支持 .xlsx 文件，请将数据表另存为 Excel 工作簿（.xlsx）。")
    temporary_dir = TemporaryDirectory(prefix="bohr_platform_")
    path = Path(temporary_dir.name) / "uploaded.xlsx"
    path.write_bytes(payload)
    return temporary_dir, path


def load_uploaded_damping(payload: bytes, file_name: str, sheet_name: str = "Sheet1") -> pd.DataFrame:
    temporary_dir, path = _temporary_excel_path(payload, file_name)
    try:
        return load_damping_measurements(path, sheet_name)
    finally:
        temporary_dir.cleanup()


def load_uploaded_forced(payload: bytes, file_name: str, sheet_name: str = "Sheet1") -> pd.DataFrame:
    temporary_dir, path = _temporary_excel_path(payload, file_name)
    try:
        return load_forced_measurements(path, sheet_name)
    finally:
        temporary_dir.cleanup()


def read_beta_from_damping_upload(
    payload: bytes,
    file_name: str,
    target_current: float = 0.300,
    sheet_name: str = "Sheet1",
) -> float:
    data = load_uploaded_damping(payload, file_name, sheet_name)
    return get_beta_at_current(data, target_current)


def _figure_bytes(fig: plt.Figure) -> bytes:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buffer.getvalue()


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def _decay_plot(data: pd.DataFrame, fit: DecayFitResult) -> bytes:
    configure_matplotlib_chinese_font()
    time_s = data["elapsed_time_s"].to_numpy(dtype=float)
    measured = data["amplitude_deg"].to_numpy(dtype=float)
    fitted = data["fit_amplitude_deg"].to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(9.2, 5.8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FBFDFF")
    ax.scatter(time_s, measured, s=10, color="#2563A6", alpha=0.72,
               edgecolors="none", zorder=2, label="实验数据")
    ax.plot(time_s, fitted, color="#D55E00", linewidth=2.2, zorder=3,
            label="阻尼正弦拟合")

    equation = (
        r"$A(t)=C+A_0e^{-\beta t}\sin(\omega t+\varphi)$"
        "\n"
        + rf"$A_0={fit.amplitude_A:.4f}\pm{fit.amplitude_A_error:.4f}$ deg"
        "\n"
        + rf"$\beta={fit.beta:.6f}\pm{fit.beta_error:.6f}$ s$^{{-1}}$"
        "\n"
        + rf"$\omega={fit.omega:.6f}\pm{fit.omega_error:.6f}$ rad/s"
        "\n"
        + rf"$\varphi={fit.phase_phi:.6f}\pm{fit.phase_phi_error:.6f}$ rad"
        "\n"
        + rf"$C={fit.offset_C:.4f}\pm{fit.offset_C_error:.4f}$ deg"
        "\n"
        + rf"RMSE={fit.rmse:.4f} deg, $R^2={fit.r_squared:.6f}$"
    )
    ax.text(0.985, 0.96, equation, transform=ax.transAxes, ha="right", va="top",
            fontsize=9.5, linespacing=1.35,
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "white",
                  "edgecolor": "#B9D4F0", "alpha": 0.96})
    ax.set_xlabel("时间 t (s)", fontsize=12)
    ax.set_ylabel("振幅角度 A (deg)", fontsize=12)
    ax.set_title("阻尼振动时域曲线拟合", fontsize=15, pad=14, color="#123A63")
    ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.35, color="#8EAFCB")
    ax.legend(frameon=True, facecolor="white", loc="lower right")
    for spine in ax.spines.values():
        spine.set_color("#B8CDE0")
    fig.tight_layout()
    return _figure_bytes(fig)


def analyze_decay_upload(payload: bytes, file_name: str) -> DecayPlatformResult:
    processed, fit = fit_decay_model(load_decay_csv(payload, file_name))
    export = processed[[
        "time_s", "elapsed_time_s", "amplitude_deg", "fit_amplitude_deg", "residual_deg"
    ]].copy()
    return DecayPlatformResult(
        source_name=file_name,
        processed=export,
        fit=fit,
        plot_png=_decay_plot(processed, fit),
        processed_csv=_csv_bytes(export),
    )


def _damping_plot(data: pd.DataFrame, fit: DampingFitResult) -> bytes:
    configure_matplotlib_chinese_font()
    x = data["Id_squared_A2"].to_numpy(dtype=float)
    y = data["beta_s-1"].to_numpy(dtype=float)
    x_line = np.linspace(float(x.min()), float(x.max()), 300)
    y_line = fit.slope_k * x_line + fit.intercept_beta0

    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FBFDFF")
    ax.scatter(x, y, s=58, color="#2563A6", edgecolor="white", linewidth=0.9,
               zorder=3, label="实验数据")
    ax.plot(x_line, y_line, color="#0EA5A4", linewidth=2.3, label="线性最小二乘拟合")
    sign = "+" if fit.intercept_beta0 >= 0 else "-"
    equation = (
        rf"$\beta={fit.slope_k:.4f}I_d^2{sign}{abs(fit.intercept_beta0):.4f}$"
        "\n" + rf"$R^2={fit.r_squared:.4f}$"
    )
    ax.text(0.045, 0.94, equation, transform=ax.transAxes, va="top", fontsize=11,
            bbox={"boxstyle": "round,pad=0.4", "facecolor": "white",
                  "edgecolor": "#B9D4F0", "alpha": 0.96})
    ax.set_xlabel(r"阻尼电流平方 $I_d^2$ (A$^2$)", fontsize=12)
    ax.set_ylabel(r"阻尼系数 $\beta$ (s$^{-1}$)", fontsize=12)
    ax.set_title("阻尼系数与阻尼电流平方的关系", fontsize=15, pad=14, color="#123A63")
    ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.35, color="#8EAFCB")
    ax.legend(frameon=True, facecolor="white")
    for spine in ax.spines.values():
        spine.set_color("#B8CDE0")
    fig.tight_layout()
    return _figure_bytes(fig)


def analyze_damping_upload(
    payload: bytes,
    file_name: str,
    sheet_name: str = "Sheet1",
) -> DampingPlatformResult:
    data = calculate_current_squared(load_uploaded_damping(payload, file_name, sheet_name))
    processed, fit = fit_damping_model(data)
    try:
        beta_at_0300 = get_beta_at_current(processed, 0.300)
    except ValueError:
        beta_at_0300 = None
    export = processed[[
        "Id_A", "Id_squared_A2", "beta_s-1", "beta_fit_s-1", "residual"
    ]].copy()
    return DampingPlatformResult(
        source_name=file_name,
        processed=export,
        fit=fit,
        beta_at_0300=beta_at_0300,
        plot_png=_damping_plot(processed, fit),
        processed_csv=_csv_bytes(export),
    )


def _forced_amplitude_plot(data: pd.DataFrame, omega0: float, amplitude_max: float) -> bytes:
    configure_matplotlib_chinese_font()
    ordered = data.sort_values("omega_ratio")
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FBFDFF")
    ax.plot(ordered["omega_ratio"], ordered["amplitude_deg"], color="#2563A6",
            linewidth=2.1, marker="o", markersize=6, markerfacecolor="white",
            markeredgewidth=1.4, label="实验数据")
    ax.axvline(1.0, color="#7B9AB8", linewidth=1.2, linestyle="--",
               label=r"$\omega/\omega_0=1$")
    ax.scatter([1.0], [amplitude_max], s=70, color="#0EA5A4", zorder=4,
               label="共振点")
    ax.annotate(
        "共振点\n"
        + rf"$\omega_0$ = {omega0:.3f} rad/s"
        + "\n"
        + rf"$\theta_{{max}}$ = {amplitude_max:.3f}°",
        xy=(1.0, amplitude_max), xytext=(20, -65), textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": "#456987"}, fontsize=10,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white",
              "edgecolor": "#B9D4F0", "alpha": 0.96},
    )
    ax.set_xlabel(r"无量纲频率比 $\omega/\omega_0$", fontsize=12)
    ax.set_ylabel(r"稳态振幅 $\theta$ (deg)", fontsize=12)
    ax.set_title("受迫振动幅频特性", fontsize=15, pad=14, color="#123A63")
    ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.35, color="#8EAFCB")
    ax.legend(frameon=True, facecolor="white")
    for spine in ax.spines.values():
        spine.set_color("#B8CDE0")
    fig.tight_layout()
    return _figure_bytes(fig)


def _forced_phase_plot(data: pd.DataFrame) -> bytes:
    configure_matplotlib_chinese_font()
    ordered = data.sort_values("omega_ratio")
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FBFDFF")
    ax.plot(ordered["omega_ratio"], ordered["phase_pi"], color="#0B7F85",
            linewidth=2.1, marker="o", markersize=6, markerfacecolor="white",
            markeredgewidth=1.4, label="计算相位差")
    ax.axvline(1.0, color="#7B9AB8", linewidth=1.2, linestyle="--",
               label=r"$\omega/\omega_0=1$")
    ax.axhline(-0.5, color="#A0B7CC", linewidth=1.2, linestyle=":",
               label=r"$\varphi/\pi=-0.5$")
    ax.scatter([1.0], [-0.5], s=65, color="#2563A6", zorder=4)
    ax.annotate("(1, -0.5)", xy=(1.0, -0.5), xytext=(13, 13),
                textcoords="offset points", fontsize=10,
                arrowprops={"arrowstyle": "->", "color": "#456987"})
    ax.set_xlabel(r"无量纲频率比 $\omega/\omega_0$", fontsize=12)
    ax.set_ylabel(r"相位差 $\varphi/\pi$", fontsize=12)
    ax.set_title("受迫振动相频特性", fontsize=15, pad=14, color="#123A63")
    ax.set_ylim(min(-1.03, float(ordered["phase_pi"].min()) - 0.04),
                max(0.03, float(ordered["phase_pi"].max()) + 0.04))
    ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.35, color="#8EAFCB")
    ax.legend(frameon=True, facecolor="white")
    for spine in ax.spines.values():
        spine.set_color("#B8CDE0")
    fig.tight_layout()
    return _figure_bytes(fig)


def analyze_forced_upload(
    payload: bytes,
    file_name: str,
    beta: float,
    sheet_name: str = "Sheet1",
) -> ForcedPlatformResult:
    if beta < 0 or not np.isfinite(beta):
        raise ValueError("阻尼系数 β 必须是大于等于零的有限数值。")
    data = load_uploaded_forced(payload, file_name, sheet_name)
    omega0, amplitude_max, _ = find_omega0_from_peak(data)
    processed = calculate_frequency_ratio(data, omega0)
    processed = calculate_phase_difference(processed, beta, omega0)
    export = processed[[
        "drive_frequency_label", "omega_rad_s", "omega_ratio", "amplitude_deg",
        "phase_rad", "phase_pi",
    ]].copy()
    return ForcedPlatformResult(
        source_name=file_name,
        processed=export,
        beta=float(beta),
        omega0=omega0,
        amplitude_max=amplitude_max,
        amplitude_png=_forced_amplitude_plot(processed, omega0, amplitude_max),
        phase_png=_forced_phase_plot(processed),
        processed_csv=_csv_bytes(export),
    )


def build_zip(files: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for file_name, content in files.items():
            archive.writestr(file_name, content)
    return buffer.getvalue()
