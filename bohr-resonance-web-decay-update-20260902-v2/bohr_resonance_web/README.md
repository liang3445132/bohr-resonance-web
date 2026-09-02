# BohrLab · 波尔共振数据处理网站

这是由原 Python 项目完整迁移得到的 HTTP 网站。打开浏览器即可完成 Excel/CSV 上传、数据校验、参数计算、曲线预览与结果下载；原始文件不会被修改。

## 一键启动（Windows）

双击 `启动网站.bat`。首次启动会自动创建 `.venv` 并安装依赖，完成后浏览器访问：

- 本机：<http://localhost:8501>
- 同一局域网的其他设备：`http://这台电脑的局域网IP:8501`

终端窗口需要保持打开；关闭窗口即停止网站。若 Windows 防火墙询问是否允许 Python 访问网络，请按实际使用范围放行。

也可以在 PowerShell 中运行：

```powershell
.\start.ps1
```

## 网站功能

- 阻尼电流分析：上传 `.xlsx`，重新计算 `Id²`，执行 `β = kId² + β₀` 最小二乘拟合，计算 `R²`。
- 受迫振动分析：由最大振幅点自动确定 `ω₀`，重新计算 `ω/ω₀`，使用 `atan2` 计算正确象限的相位。
- 阻尼振动拟合：读取 CSV 的时间和角度/振幅列，拟合 `A(t)=C+A₀e^(-βt)sin(ωt+φ)`，给出参数标准误差、RMSE 和 `R²`；角速度列完全忽略。
- β 可直接输入，也可从阻尼表 `Id = 0.300 A` 的实测行读取。
- 支持自定义工作表名称，并为受迫表、阻尼表分别设置工作表。
- 支持内置示例数据，可不上传文件直接体验完整流程。
- 支持图表预览、处理后表格查看、PNG/CSV 单项下载及 ZIP 打包下载。
- 保留原命令行批处理入口 `main.py`。

## Excel 表头

默认工作表名为 `Sheet1`，网页中可以修改。系统兼容常见的全半角标点和字段别名。

阻尼电流表至少需要：

- `Id(A)`
- `β`

受迫振动表至少需要：

- `受迫频率（Hz)`
- `角频率ω`
- `振幅θ`

系统忽略表中已有的 `Id²` 和 `ω/ω₀`，始终根据原始列重新计算。

阻尼振动 CSV 至少需要：

- `时间(s)`（也兼容 `时间`、`time(s)`、`time`）
- `角度(°)`（也兼容 `角度`、`振幅`、`amplitude`、`angle`）

CSV 表头之前可以保留设备元数据。第三列角速度不读取、不校验，也不参与拟合。

## 部署成公网网址

项目包含 `Dockerfile`，可部署到支持 Docker 的服务器或云平台：

```bash
docker build -t bohrlab .
docker run --rm -p 8501:8501 bohrlab
```

随后通过服务器地址访问 `http://服务器IP:8501`。生产环境建议再用域名和 HTTPS 反向代理对外提供服务。健康检查地址为 `/_stcore/health`。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试使用项目自带的两份示例 Excel 和一份阻尼振动 CSV，验证三种分析、关键数值、角速度列排除和 PNG 生成。

## 主要文件

- `app.py`：网站页面入口。
- `platform_core.py`：上传解析、计算、绘图和导出服务。
- `common/data_utils.py`：Excel 清洗、表头识别和校验。
- `damping_analysis/`、`forced_analysis/`、`decay_analysis/`：三种分析模块。
- `启动网站.bat` / `start.ps1`：Windows 一键启动。
- `Dockerfile`：服务器部署入口。
