# GitHub 与 Streamlit 更新说明

本版本在原网站上新增“阻尼振动拟合模式”，原有两项功能保留不变。

## 最少操作步骤

1. 解压最终交付的 ZIP。
2. 打开 GitHub 仓库 `liang3445132/bohr-resonance-web`。
3. 点击 **Add file → Upload files**。
4. 把解压后的 `bohr_resonance_web` 整个文件夹拖入上传区；同名文件选择覆盖，同时会新增 `decay_analysis` 文件夹。
5. 在页面底部点击 **Commit changes**。
6. 等待 Streamlit Community Cloud 自动重新部署，通常无需重新创建应用。

仓库根目录现有的 `packages.txt` 保持为 `fonts-noto-cjk` 即可，不需要修改。

## 本次必须更新的内容

- `bohr_resonance_web/app.py`
- `bohr_resonance_web/platform_core.py`
- `bohr_resonance_web/requirements.txt`
- `bohr_resonance_web/README.md`
- `bohr_resonance_web/tests/test_platform_core.py`
- 新增整个 `bohr_resonance_web/decay_analysis/` 文件夹

## 部署后检查

打开网站，选择“阻尼振动拟合模式”，勾选“使用平台内置示例数据”，点击“确认并生成阻尼拟合图”。若页面显示 `β ≈ 0.029864 s⁻¹`、`ω ≈ 3.864358 rad/s`、`R² ≈ 0.995585`，说明部署成功。

