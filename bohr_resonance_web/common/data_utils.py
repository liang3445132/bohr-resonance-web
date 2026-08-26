"""Excel 数据清洗、字段识别及绘图字体设置。"""

from __future__ import annotations

import re
import sys
import unicodedata
import warnings
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


def configure_console_utf8() -> None:
    """在 Windows 重定向终端中安全输出中文、β、ω、R² 等字符。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def _normalize_header(value: object) -> str:
    """统一全半角、希腊字母、上下标和标点，便于兼容不同表头。"""
    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    replacements = {
        "β": "beta",
        "ω": "omega",
        "θ": "theta",
        "φ": "phi",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"[\s_\-—–·,，。:：;；/\\()（）\[\]{}]+", "", text)


def _find_column(
    frame: pd.DataFrame,
    aliases: Iterable[str],
    field_description: str,
) -> object:
    normalized_columns = {_normalize_header(column): column for column in frame.columns}
    normalized_aliases = [_normalize_header(alias) for alias in aliases]

    for alias in normalized_aliases:
        if alias in normalized_columns:
            return normalized_columns[alias]

    available = "、".join(str(column) for column in frame.columns)
    expected = "、".join(aliases)
    raise ValueError(
        f"找不到{field_description}列。可识别名称包括：{expected}；"
        f"实际读取到的字段为：{available}。"
    )


def _load_clean_sheet(file_path: Path, sheet_name: str) -> pd.DataFrame:
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Excel 文件不存在：{file_path}")

    try:
        excel_file = pd.ExcelFile(file_path, engine="openpyxl")
    except Exception as exc:
        raise ValueError(f"无法打开 Excel 文件 {file_path}：{exc}") from exc

    try:
        if sheet_name not in excel_file.sheet_names:
            raise ValueError(
                f"Excel 文件 {file_path.name} 中不存在工作表 {sheet_name!r}；"
                f"实际工作表为：{excel_file.sheet_names}。"
            )
        frame = pd.read_excel(excel_file, sheet_name=sheet_name)
    finally:
        # Windows 下必须显式关闭，否则网页上传产生的临时文件会一直被锁定。
        excel_file.close()
    frame = frame.dropna(axis=0, how="all").dropna(axis=1, how="all")
    frame.columns = [str(column).strip() for column in frame.columns]

    if frame.empty or len(frame.columns) == 0:
        raise ValueError(f"Excel 文件 {file_path.name} 的 {sheet_name} 为空。")
    if frame.columns.duplicated().any():
        duplicated = frame.columns[frame.columns.duplicated()].tolist()
        raise ValueError(f"Excel 表头存在重复字段：{duplicated}。")

    print(f"读取数据文件：{file_path}")
    print(f"工作表：{sheet_name}")
    print(f"删除全空行、全空列后数据行数：{len(frame)}")
    print(f"识别到的原始字段：{list(frame.columns)}")
    return frame


def _numeric_column(series: pd.Series, field_name: str, file_path: Path) -> pd.Series:
    converted = pd.to_numeric(series, errors="coerce")
    invalid = series.notna() & converted.isna()
    missing = converted.isna()
    if invalid.any():
        details = [
            f"Excel 第 {index + 2} 行：{series.loc[index]!r}"
            for index in series.index[invalid]
        ]
        raise ValueError(
            f"文件 {file_path.name} 的“{field_name}”列包含无法转换为数值的内容："
            + "；".join(details)
        )
    if missing.any():
        rows = [str(index + 2) for index in series.index[missing]]
        raise ValueError(
            f"文件 {file_path.name} 的“{field_name}”列存在空值，Excel 行号："
            + "、".join(rows)
        )
    values = converted.astype(float)
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError(f"文件 {file_path.name} 的“{field_name}”列包含无穷大。")
    return values


def _report_duplicates(frame: pd.DataFrame, subset: list[str], file_name: str) -> None:
    duplicate_mask = frame.duplicated(subset=subset, keep=False)
    if duplicate_mask.any():
        rows = (frame.index[duplicate_mask] + 2).tolist()
        warnings.warn(f"{file_name} 存在重复记录，Excel 行号：{rows}", stacklevel=2)
    else:
        print("重复值检查：未发现重复记录")
    print("NaN 检查：必需字段均无缺失值")


def load_damping_measurements(file_path: Path, sheet_name: str = "Sheet1") -> pd.DataFrame:
    """读取阻尼数据并标准化为 Id_A、beta_s-1 两列。"""
    file_path = Path(file_path)
    raw = _load_clean_sheet(file_path, sheet_name)
    current_column = _find_column(
        raw,
        ["Id(A)", "Id", "I_d(A)", "I_d", "阻尼电流(A)", "阻尼电流"],
        "阻尼电流 Id",
    )
    beta_column = _find_column(
        raw,
        ["β", "beta", "beta(s-1)", "阻尼系数β", "阻尼系数"],
        "阻尼系数 β",
    )

    result = pd.DataFrame(
        {
            "Id_A": _numeric_column(raw[current_column], "阻尼电流 Id", file_path),
            "beta_s-1": _numeric_column(raw[beta_column], "阻尼系数 β", file_path),
        }
    ).reset_index(drop=True)

    if (result["Id_A"] < 0).any():
        raise ValueError("阻尼电流 Id 不应为负数。")
    if (result["beta_s-1"] < 0).any():
        raise ValueError("阻尼系数 β 不应为负数。")
    _report_duplicates(result, ["Id_A", "beta_s-1"], file_path.name)
    return result


def load_forced_measurements(file_path: Path, sheet_name: str = "Sheet1") -> pd.DataFrame:
    """读取受迫振动数据并标准化字段；不使用表内已有的频率比。"""
    file_path = Path(file_path)
    raw = _load_clean_sheet(file_path, sheet_name)
    label_column = _find_column(
        raw,
        ["受迫频率（Hz)", "受迫频率(Hz)", "受迫频率", "驱动频率", "频率标签"],
        "受迫频率标签",
    )
    omega_column = _find_column(
        raw,
        ["角频率ω", "角频率", "ω", "omega", "omega(rad/s)"],
        "实际驱动角频率 ω",
    )
    amplitude_column = _find_column(
        raw,
        ["振幅θ", "振幅", "theta", "theta(deg)", "稳态振幅"],
        "稳态振幅 θ",
    )

    labels = raw[label_column].astype("string").str.strip()
    if labels.isna().any() or (labels == "").any():
        rows = (labels.index[labels.isna() | (labels == "")] + 2).tolist()
        raise ValueError(f"受迫频率标签存在空值，Excel 行号：{rows}")

    result = pd.DataFrame(
        {
            "drive_frequency_label": labels,
            "omega_rad_s": _numeric_column(raw[omega_column], "角频率 ω", file_path),
            "amplitude_deg": _numeric_column(raw[amplitude_column], "振幅 θ", file_path),
        }
    ).reset_index(drop=True)

    if (result["omega_rad_s"] <= 0).any():
        raise ValueError("角频率 ω 必须大于零。")
    _report_duplicates(result, ["drive_frequency_label", "omega_rad_s", "amplitude_deg"], file_path.name)
    return result


def get_beta_at_current(
    damping_source: Path | pd.DataFrame,
    current_A: float,
    sheet_name: str = "Sheet1",
    *,
    rtol: float = 1e-7,
    atol: float = 1e-9,
) -> float:
    """返回指定电流下的实测 β；不拟合、不插值。"""
    if isinstance(damping_source, pd.DataFrame):
        data = damping_source
    else:
        data = load_damping_measurements(Path(damping_source), sheet_name)

    matches = np.isclose(data["Id_A"].to_numpy(), current_A, rtol=rtol, atol=atol)
    matched_beta = data.loc[matches, "beta_s-1"].to_numpy(dtype=float)
    if len(matched_beta) == 0:
        raise ValueError(
            f"未在阻尼数据中找到 Id = {current_A:.3f} A 对应的阻尼系数。"
        )
    if not np.allclose(matched_beta, matched_beta[0], rtol=rtol, atol=atol):
        raise ValueError(
            f"Id = {current_A:.3f} A 对应多个不一致的阻尼系数：{matched_beta.tolist()}。"
        )
    return float(matched_beta[0])


def configure_matplotlib_chinese_font() -> str | None:
    """依次寻找常见中文字体；找不到时仅警告，不中断程序。"""
    import matplotlib as mpl
    from matplotlib import font_manager

    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"]
    for font_name in candidates:
        try:
            font_manager.findfont(font_name, fallback_to_default=False)
        except ValueError:
            continue
        mpl.rcParams["font.sans-serif"] = [font_name, "DejaVu Sans"]
        mpl.rcParams["axes.unicode_minus"] = False
        return font_name

    mpl.rcParams["axes.unicode_minus"] = False
    warnings.warn(
        "未找到 Microsoft YaHei、SimHei、Noto Sans CJK SC 或 Arial Unicode MS；"
        "中文可能显示为方框，但数据处理仍将继续。",
        stacklevel=2,
    )
    return None
