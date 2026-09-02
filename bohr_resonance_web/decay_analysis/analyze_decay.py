"""读取阻尼振动 CSV，并拟合指数衰减正弦模型。"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import csv
import re
import unicodedata

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


@dataclass(frozen=True)
class DecayFitResult:
    amplitude_A: float
    beta: float
    omega: float
    phase_phi: float
    offset_C: float
    amplitude_A_error: float
    beta_error: float
    omega_error: float
    phase_phi_error: float
    offset_C_error: float
    rmse: float
    r_squared: float


def damped_sine(
    time_s: np.ndarray,
    amplitude_A: float,
    beta: float,
    omega: float,
    phase_phi: float,
    offset_C: float,
) -> np.ndarray:
    """A(t) = C + A₀ exp(-βt) sin(ωt + φ)."""
    return offset_C + amplitude_A * np.exp(-beta * time_s) * np.sin(
        omega * time_s + phase_phi
    )


def _normalize_header(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    replacements = {"θ": "theta", "°": "deg", "（": "(", "）": ")"}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"[\s_\-—–·,，。:：;；/\\()\[\]{}]+", "", text)


def _decode_csv(payload: bytes) -> str:
    if not payload:
        raise ValueError("上传的 CSV 文件为空。")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV 编码无法识别，请另存为 UTF-8 或 GB18030 编码。")


def _find_header_row(text: str) -> int:
    time_aliases = {_normalize_header(item) for item in ("时间(s)", "时间", "time(s)", "time")}
    angle_aliases = {
        _normalize_header(item)
        for item in ("角度(°)", "角度", "振幅", "振幅角度", "amplitude", "angle")
    }
    for index, row in enumerate(csv.reader(StringIO(text))):
        normalized = {_normalize_header(cell) for cell in row}
        if normalized & time_aliases and normalized & angle_aliases:
            return index
        if index >= 20:
            break
    raise ValueError("找不到表头。CSV 必须包含时间列和角度/振幅列。")


def _find_column(frame: pd.DataFrame, aliases: tuple[str, ...], description: str) -> object:
    columns = {_normalize_header(column): column for column in frame.columns}
    for alias in aliases:
        normalized = _normalize_header(alias)
        if normalized in columns:
            return columns[normalized]
    available = "、".join(str(column) for column in frame.columns)
    raise ValueError(f"找不到{description}列；实际读取到的字段为：{available}。")


def load_decay_csv(payload: bytes, file_name: str) -> pd.DataFrame:
    if not str(file_name).lower().endswith(".csv"):
        raise ValueError("阻尼振动曲线拟合仅支持 .csv 文件。")
    text = _decode_csv(payload)
    header_row = _find_header_row(text)
    frame = pd.read_csv(StringIO(text), skiprows=header_row)
    frame = frame.dropna(axis=0, how="all").dropna(axis=1, how="all")
    if frame.empty:
        raise ValueError("CSV 中没有可用于拟合的数据。")

    time_column = _find_column(frame, ("时间(s)", "时间", "time(s)", "time"), "时间")
    angle_column = _find_column(
        frame,
        ("角度(°)", "角度", "振幅", "振幅角度", "amplitude", "angle"),
        "角度/振幅",
    )
    # 角速度列有意不读取、不校验，也不参与任何计算。
    time_values = pd.to_numeric(frame[time_column], errors="coerce")
    angle_values = pd.to_numeric(frame[angle_column], errors="coerce")
    invalid = time_values.isna() | angle_values.isna()
    if invalid.any():
        rows = (frame.index[invalid] + header_row + 2).tolist()
        raise ValueError(f"时间或角度列存在空值/非数值，CSV 行号：{rows}。")

    result = pd.DataFrame(
        {"time_s": time_values.astype(float), "amplitude_deg": angle_values.astype(float)}
    )
    if not np.isfinite(result.to_numpy()).all():
        raise ValueError("时间或角度列包含无穷大。")
    result = result.sort_values("time_s").reset_index(drop=True)
    if len(result) < 20:
        raise ValueError("阻尼振动拟合至少需要 20 个数据点。")
    if result["time_s"].duplicated().any():
        raise ValueError("时间列存在重复值，请保留每个采样时刻的一条记录。")
    if float(result["time_s"].max() - result["time_s"].min()) <= 0:
        raise ValueError("时间范围必须大于零。")
    return result


def _initial_omega(time_s: np.ndarray, amplitude: np.ndarray) -> float:
    relative_time = time_s - time_s[0]
    sample_interval = float(np.median(np.diff(relative_time)))
    if sample_interval <= 0:
        raise ValueError("时间采样间隔必须大于零。")
    uniform_time = np.arange(relative_time[0], relative_time[-1] + sample_interval / 2, sample_interval)
    uniform_amplitude = np.interp(uniform_time, relative_time, amplitude)
    centered = uniform_amplitude - np.mean(uniform_amplitude)
    spectrum = np.abs(np.fft.rfft(centered * np.hanning(len(centered))))
    frequencies = np.fft.rfftfreq(len(centered), d=sample_interval)
    if len(frequencies) < 2:
        raise ValueError("数据时间跨度不足，无法估计振动频率。")
    spectrum[0] = 0.0
    frequency_hz = float(frequencies[int(np.argmax(spectrum))])
    if frequency_hz <= 0:
        raise ValueError("无法从数据中识别有效振动频率。")
    return 2.0 * np.pi * frequency_hz


def fit_decay_model(data: pd.DataFrame) -> tuple[pd.DataFrame, DecayFitResult]:
    original_time = data["time_s"].to_numpy(dtype=float)
    time_s = original_time - original_time[0]
    amplitude = data["amplitude_deg"].to_numpy(dtype=float)
    duration = float(np.ptp(time_s))
    value_range = float(np.ptp(amplitude))
    if np.isclose(value_range, 0.0):
        raise ValueError("所有角度/振幅值均相同，无法拟合阻尼振动曲线。")

    omega_guess = _initial_omega(original_time, amplitude)
    offset_guess = float(np.mean(amplitude))
    amplitude_guess = max(value_range / 2.0, 1e-6)
    nyquist_omega = np.pi / float(np.median(np.diff(time_s)))
    beta_upper = max(10.0 / duration, 1.0)
    omega_lower = max(2.0 * np.pi / (duration * 4.0), omega_guess * 0.25)
    omega_upper = min(nyquist_omega * 0.95, omega_guess * 4.0)
    if omega_upper <= omega_lower:
        omega_upper = omega_lower * 4.0

    lower = [0.0, 0.0, omega_lower, -2.0 * np.pi, float(amplitude.min() - value_range)]
    upper = [value_range * 4.0, beta_upper, omega_upper, 2.0 * np.pi,
             float(amplitude.max() + value_range)]

    best: tuple[float, np.ndarray, np.ndarray] | None = None
    beta_seeds = sorted({0.0, 0.02, 0.06, 0.12, min(0.35, beta_upper * 0.7)})
    phase_seeds = np.linspace(-np.pi, np.pi, 9)
    for beta_seed in beta_seeds:
        for phase_seed in phase_seeds:
            initial = [amplitude_guess, min(beta_seed, beta_upper * 0.95), omega_guess,
                       float(phase_seed), offset_guess]
            try:
                parameters, covariance = curve_fit(
                    damped_sine,
                    time_s,
                    amplitude,
                    p0=initial,
                    bounds=(lower, upper),
                    maxfev=50000,
                )
            except (RuntimeError, ValueError, FloatingPointError):
                continue
            fitted = damped_sine(time_s, *parameters)
            residual_sum = float(np.sum(np.square(amplitude - fitted)))
            if best is None or residual_sum < best[0]:
                best = residual_sum, parameters, covariance

    if best is None:
        raise ValueError("阻尼振动非线性拟合未收敛，请检查数据是否包含清晰的衰减振荡。")

    _, parameters, covariance = best
    fitted = damped_sine(time_s, *parameters)
    residual = amplitude - fitted
    rmse = float(np.sqrt(np.mean(np.square(residual))))
    total_sum = float(np.sum(np.square(amplitude - np.mean(amplitude))))
    r_squared = 1.0 - float(np.sum(np.square(residual))) / total_sum
    errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))

    phase = float(parameters[3] % (2.0 * np.pi))
    processed = data.copy()
    processed["elapsed_time_s"] = time_s
    processed["fit_amplitude_deg"] = fitted
    processed["residual_deg"] = residual
    return processed, DecayFitResult(
        amplitude_A=float(parameters[0]),
        beta=float(parameters[1]),
        omega=float(parameters[2]),
        phase_phi=phase,
        offset_C=float(parameters[4]),
        amplitude_A_error=float(errors[0]),
        beta_error=float(errors[1]),
        omega_error=float(errors[2]),
        phase_phi_error=float(errors[3]),
        offset_C_error=float(errors[4]),
        rmse=rmse,
        r_squared=r_squared,
    )

