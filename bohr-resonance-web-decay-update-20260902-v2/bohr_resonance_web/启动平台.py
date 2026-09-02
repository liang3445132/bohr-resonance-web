"""在 PyCharm 中直接运行此文件，自动启动本地网页平台。"""

from pathlib import Path
import os
import sys

from streamlit.web import cli as streamlit_cli


if __name__ == "__main__":
    app_file = Path(__file__).resolve().parent / "app.py"
    sys.argv = [
        "streamlit",
        "run",
        str(app_file),
        "--server.address=0.0.0.0",
        f"--server.port={os.environ.get('PORT', '8501')}",
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
    ]
    raise SystemExit(streamlit_cli.main())
