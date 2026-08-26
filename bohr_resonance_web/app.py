"""波尔共振实验数据处理平台（Streamlit 页面入口）。"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from platform_core import (
    DampingPlatformResult,
    ForcedPlatformResult,
    analyze_damping_upload,
    analyze_forced_upload,
    build_zip,
    read_beta_from_damping_upload,
)


st.set_page_config(
    page_title="波尔共振数据处理平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PROJECT_ROOT = Path(__file__).resolve().parent
DAMPING_DEMO = PROJECT_ROOT / "damping_analysis" / "data" / "阻尼电流原始数据.xlsx"
FORCED_DEMO = PROJECT_ROOT / "forced_analysis" / "data" / "受迫振动原始数据.xlsx"


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root { --blue:#1F5F9E; --deep:#123A63; --cyan:#0EA5A4; --line:#D6E6F5; }
        .stApp { background: linear-gradient(180deg, #F5F9FE 0%, #FFFFFF 42%); }
        [data-testid="stHeader"] { height: 2.25rem; background: rgba(255,255,255,0.72); }
        [data-testid="stToolbar"] { visibility: hidden; }
        [data-testid="stSidebar"] { background: #F0F6FC; border-right: 1px solid #D9E7F4; }
        .main .block-container { max-width: 1500px; padding-top: .35rem; padding-bottom: 1rem; }
        .main [data-testid="stVerticalBlock"] { gap: .55rem; }
        .main hr { margin: .25rem 0 .45rem !important; }
        .hero {
            padding: .72rem 1.15rem; border-radius: 14px;
            background: linear-gradient(115deg, #123A63 0%, #1F67A8 58%, #2F8EBC 100%);
            color: white; box-shadow: 0 8px 22px rgba(30, 82, 132, .14);
            margin-bottom: .35rem;
        }
        .hero h1 { margin: 0; font-size: clamp(1.24rem, 1.75vw, 1.62rem); letter-spacing: .02em; }
        .hero p { margin: .18rem 0 0; color: #DDEEFF; font-size: .84rem; }
        .section-title { color: #123A63; font-size: 1rem; font-weight: 700; margin: .05rem 0 .3rem; }
        .placeholder {
            min-height: 230px; border: 1.5px dashed #AFCBE3; border-radius: 14px;
            display: flex; align-items: center; justify-content: center; text-align: center;
            color: #6887A5; background: rgba(255,255,255,.72); padding: 1rem;
        }
        .status-note {
            border-left: 4px solid #2B77B8; background: #EDF6FF; color: #254D70;
            padding: .72rem .9rem; border-radius: 8px; margin: .4rem 0 .9rem;
        }
        [data-testid="stFileUploader"] section {
            background: #FFFFFF; border: 1.5px dashed #89B5D9; border-radius: 14px;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(90deg, #1F5F9E, #267AB7); border: 0;
            border-radius: 10px; font-weight: 700; min-height: 2.8rem;
        }
        .stDownloadButton > button { border-color: #8CB8DB; border-radius: 10px; }
        div[data-testid="stMetric"] {
            background: white; border: 1px solid #D9E7F4; border-radius: 12px;
            padding: .38rem .65rem;
        }
        div[data-testid="stMetricLabel"] { font-size: .78rem; }
        div[data-testid="stMetricValue"] { font-size: 1.42rem; line-height: 1.15; }
        [data-testid="stImage"] { margin-top: .1rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_header() -> None:
    st.markdown(
        """
        <div class="hero">
          <h1>BohrLab · 波尔共振数据处理平台</h1>
          <p>上传原始 Excel，一键完成参数计算、曲线绘制与图片导出。全部数据仅在本机处理。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_sidebar() -> None:
    with st.sidebar:
        st.markdown("### 使用说明")
        st.markdown(
            """
            1. 选择分析模式  
            2. 上传 `.xlsx` 原始表格  
            3. 点击“生成分析图”  
            4. 在右侧预览并下载
            """
        )
        st.divider()
        st.markdown("#### 表头要求")
        st.caption("阻尼电流：`Id(A)`、`β`")
        st.caption("受迫振动：`受迫频率（Hz)`、`角频率ω`、`振幅θ`")
        st.divider()
        st.caption("原始文件不会被修改。计算结果只在当前页面会话中保存。")


def damping_page() -> None:
    left, right = st.columns([0.92, 1.48], gap="large")
    with left:
        st.markdown('<div class="section-title">01 · 放入阻尼电流原始表</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "阻尼电流原始数据",
            type=["xlsx"],
            key="damping_upload",
            help="工作表名称默认为 Sheet1。",
        )
        use_demo = st.checkbox("使用平台内置示例数据", key="damping_demo")
        sheet_name = st.text_input("工作表名称", value="Sheet1", key="damping_sheet")
        if uploaded is not None:
            st.markdown(
                f'<div class="status-note">已选择：{uploaded.name}<br>大小：{uploaded.size / 1024:.1f} KB</div>',
                unsafe_allow_html=True,
            )
        source_available = uploaded is not None or use_demo
        generate = st.button(
            "确认并生成拟合图",
            type="primary",
            width="stretch",
            disabled=not source_available,
            key="generate_damping",
        )
        if generate:
            try:
                with st.spinner("正在读取、校验并拟合数据……"):
                    if use_demo:
                        payload, source_name = DAMPING_DEMO.read_bytes(), DAMPING_DEMO.name
                    else:
                        assert uploaded is not None
                        payload, source_name = uploaded.getvalue(), uploaded.name
                    result = analyze_damping_upload(payload, source_name, sheet_name)
                    st.session_state["damping_result"] = result
                    if result.beta_at_0300 is not None:
                        st.session_state["latest_beta"] = result.beta_at_0300
                st.success("拟合完成，图片已生成。")
            except Exception as exc:
                st.session_state.pop("damping_result", None)
                st.error(str(exc))

        st.markdown("##### 计算规则")
        st.caption("平台重新计算 Id²，执行 β = kId² + β₀ 线性最小二乘拟合，并计算 R²。")

    with right:
        st.markdown('<div class="section-title">02 · 生成图片与导出</div>', unsafe_allow_html=True)
        result: DampingPlatformResult | None = st.session_state.get("damping_result")
        if result is None:
            st.markdown(
                '<div class="placeholder">拟合图将在这里显示<br>请先上传阻尼电流原始数据并确认生成</div>',
                unsafe_allow_html=True,
            )
            return

        metric_cols = st.columns(3)
        metric_cols[0].metric("拟合斜率 k", f"{result.fit.slope_k:.6f}")
        metric_cols[1].metric("截距 β₀", f"{result.fit.intercept_beta0:.6f}")
        metric_cols[2].metric("决定系数 R²", f"{result.fit.r_squared:.6f}")
        preview_cols = st.columns([0.2, 0.6, 0.2])
        with preview_cols[1]:
            st.image(result.plot_png, width="stretch")

        zip_bytes = build_zip({
            "01_阻尼系数拟合图.png": result.plot_png,
            "阻尼数据处理结果.csv": result.processed_csv,
        })
        download_cols = st.columns(3)
        download_cols[0].download_button(
            "下载拟合图 PNG", result.plot_png, "01_阻尼系数拟合图.png", "image/png",
            width="stretch",
        )
        download_cols[1].download_button(
            "下载处理数据 CSV", result.processed_csv, "阻尼数据处理结果.csv", "text/csv",
            width="stretch",
        )
        download_cols[2].download_button(
            "打包下载 ZIP", zip_bytes, "阻尼分析结果.zip", "application/zip",
            width="stretch",
        )
        with st.expander("查看处理后的数据"):
            st.dataframe(result.processed, hide_index=True, width="stretch")


def forced_page() -> None:
    left, right = st.columns([0.92, 1.48], gap="large")
    with left:
        st.markdown('<div class="section-title">01 · 放入受迫振动原始表</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "受迫振动原始数据",
            type=["xlsx"],
            key="forced_upload",
            help="工作表名称默认为 Sheet1。",
        )
        use_demo = st.checkbox("使用平台内置示例数据", key="forced_demo")
        sheet_name = st.text_input("工作表名称", value="Sheet1", key="forced_sheet")
        if uploaded is not None:
            st.markdown(
                f'<div class="status-note">已选择：{uploaded.name}<br>大小：{uploaded.size / 1024:.1f} KB</div>',
                unsafe_allow_html=True,
            )

        st.markdown("##### 相位计算参数")
        beta_method = st.radio(
            "β 获取方式",
            ["直接输入 β", "从阻尼表读取 0.300 A 的 β"],
            horizontal=False,
            key="beta_method",
        )
        damping_upload = None
        if beta_method == "直接输入 β":
            beta_default = float(st.session_state.get("latest_beta", 0.109))
            beta = st.number_input(
                "阻尼系数 β (s⁻¹)", min_value=0.0, value=beta_default,
                step=0.001, format="%.6f", key="manual_beta",
            )
        else:
            damping_upload = st.file_uploader(
                "阻尼电流原始数据（用于读取 β）",
                type=["xlsx"],
                key="forced_damping_upload",
            )
            use_demo_damping = st.checkbox(
                "使用平台内置阻尼示例数据", key="forced_damping_demo"
            )
            damping_sheet_name = st.text_input(
                "阻尼表工作表名称", value="Sheet1", key="forced_damping_sheet"
            )
            beta = None

        forced_source_available = uploaded is not None or use_demo
        damping_source_available = beta_method == "直接输入 β" or (
            damping_upload is not None or use_demo_damping
        )
        can_generate = forced_source_available and damping_source_available
        generate = st.button(
            "确认并生成两张图",
            type="primary",
            width="stretch",
            disabled=not can_generate,
            key="generate_forced",
        )
        if generate:
            try:
                with st.spinner("正在识别共振点并计算幅频、相频特性……"):
                    if beta_method == "从阻尼表读取 0.300 A 的 β":
                        if use_demo_damping:
                            damping_payload = DAMPING_DEMO.read_bytes()
                            damping_name = DAMPING_DEMO.name
                        else:
                            assert damping_upload is not None
                            damping_payload = damping_upload.getvalue()
                            damping_name = damping_upload.name
                        beta = read_beta_from_damping_upload(
                            damping_payload, damping_name, 0.300, damping_sheet_name
                        )
                    assert beta is not None
                    if use_demo:
                        forced_payload, forced_name = FORCED_DEMO.read_bytes(), FORCED_DEMO.name
                    else:
                        assert uploaded is not None
                        forced_payload, forced_name = uploaded.getvalue(), uploaded.name
                    result = analyze_forced_upload(
                        forced_payload, forced_name, float(beta), sheet_name
                    )
                    st.session_state["forced_result"] = result
                st.success("两张分析图已生成。")
            except Exception as exc:
                st.session_state.pop("forced_result", None)
                st.error(str(exc))

        st.markdown("##### 计算规则")
        st.caption("最大振幅点自动确定 ω₀；频率比重新计算；相位使用 atan2，保证高频区象限正确。")

    with right:
        st.markdown('<div class="section-title">02 · 生成图片与导出</div>', unsafe_allow_html=True)
        result: ForcedPlatformResult | None = st.session_state.get("forced_result")
        if result is None:
            st.markdown(
                '<div class="placeholder">幅频图和相频图将在这里显示<br>请上传数据、设置 β 并确认生成</div>',
                unsafe_allow_html=True,
            )
            return

        metric_cols = st.columns(3)
        metric_cols[0].metric("阻尼系数 β", f"{result.beta:.6f} s⁻¹")
        metric_cols[1].metric("共振角频率 ω₀", f"{result.omega0:.6f} rad/s")
        metric_cols[2].metric("最大振幅 θmax", f"{result.amplitude_max:.6f}°")

        amplitude_tab, phase_tab = st.tabs(["幅频特性图", "相频特性图"])
        with amplitude_tab:
            preview_cols = st.columns([0.2, 0.6, 0.2])
            with preview_cols[1]:
                st.image(result.amplitude_png, width="stretch")
        with phase_tab:
            preview_cols = st.columns([0.2, 0.6, 0.2])
            with preview_cols[1]:
                st.image(result.phase_png, width="stretch")

        zip_bytes = build_zip({
            "02_受迫振动幅频特性.png": result.amplitude_png,
            "03_受迫振动相频特性.png": result.phase_png,
            "受迫振动数据处理结果.csv": result.processed_csv,
        })
        download_cols = st.columns(3)
        download_cols[0].download_button(
            "下载幅频图", result.amplitude_png, "02_受迫振动幅频特性.png", "image/png",
            width="stretch",
        )
        download_cols[1].download_button(
            "下载相频图", result.phase_png, "03_受迫振动相频特性.png", "image/png",
            width="stretch",
        )
        download_cols[2].download_button(
            "全部打包下载", zip_bytes, "受迫振动分析结果.zip", "application/zip",
            width="stretch",
        )
        st.download_button(
            "下载处理数据 CSV", result.processed_csv, "受迫振动数据处理结果.csv", "text/csv",
            width="stretch",
        )
        with st.expander("查看处理后的数据"):
            st.dataframe(result.processed, hide_index=True, width="stretch")


apply_styles()
show_header()
show_sidebar()

mode = st.radio(
    "分析模式",
    ["阻尼电流模式", "受迫振动模式"],
    horizontal=True,
    label_visibility="collapsed",
)
st.divider()

if mode == "阻尼电流模式":
    damping_page()
else:
    forced_page()
