"""依次运行阻尼振动和受迫振动分析。"""

import sys

import matplotlib.pyplot as plt

from common.data_utils import configure_console_utf8
from config import SHOW_PLOTS
from damping_analysis.analyze_damping import run_damping_analysis
from forced_analysis.analyze_forced import run_forced_analysis


def main() -> None:
    configure_console_utf8()
    print("开始波尔共振实验数据处理。\n")
    run_damping_analysis()
    run_forced_analysis()
    print("全部分析完成。")
    if SHOW_PLOTS:
        print("已打开图像窗口；关闭所有图像窗口后程序结束。")
        plt.show()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"数据处理失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
