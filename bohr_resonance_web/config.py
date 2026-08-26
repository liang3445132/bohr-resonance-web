"""项目级配置：集中管理路径和实验设置。"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

DAMPING_DATA_FILE = PROJECT_ROOT / "damping_analysis" / "data" / "阻尼电流原始数据.xlsx"
DAMPING_OUTPUT_DIR = PROJECT_ROOT / "damping_analysis" / "output"

FORCED_DATA_FILE = PROJECT_ROOT / "forced_analysis" / "data" / "受迫振动原始数据.xlsx"
FORCED_OUTPUT_DIR = PROJECT_ROOT / "forced_analysis" / "output"

SHEET_NAME = "Sheet1"
TARGET_DAMPING_CURRENT_A = 0.300

PLOT_DPI = 300
FIGURE_SIZE = (7.4, 5.2)

# True：运行结束后弹出全部图像窗口；False：只保存图像文件。
SHOW_PLOTS = False
