# 本地复现步骤

## 1. 环境

解压后在含 README 的项目根目录执行。基础入口要求 Python 3.10+；本次实际验证环境为 Python 3.13、NumPy 2.4.4、pandas 3.0.2、openpyxl 3.1.5。

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`requirements.txt` 为基础依赖范围；`requirements-tested.txt` 记录实际验证版本，不声称跨所有Python版本已测试。原 Notebook 的 Matplotlib／SciPy／Plotly／Jupyter 依赖在 `requirements-notebooks.txt`，基础入口无需它们。

## 2. 数据

行情 CSV／Excel 长表：`date,symbol,open,high,low,close`。symbol 采用 `510300.SSE`／`159915.SZSE` 等 vn.py 格式。
每天需覆盖配置中全部标的；日期不带时区或盘中时间；重复或无效OHLC报错，不前向填充。
配置包含 `symbols,setting,capital,rate,slippage,profile`，可复制现有 JSON 制作自己的配置。
`rate` 是成交金额费率；`slippage` 是每份绝对价格单位。原参数文件不被命令行修改。

轻量适配器仅支持当前原策略使用的 API，在独立 Python 进程中注册兼容模块，绝不写入已安装的 vn.py。
按后续OHLC撮合限价单，全量成交，调仓时撤换未成交委托；没有部分成交、实盘接口、保证金、分红或现金约束。
信号与状态更新继续由原策略产生。初始化按业务日切片数处理；与原生引擎的日历及初始化边界尚未做等价验证。
轻量结果和原生结果不能混称，报告分别标注。

风险平价原类需要300根全标的 K 线才能初始化；建议提供远多于300天的数据。人工示例提供640天。

## 3. 运行

```bash
python -m local.run --demo --output runs/demo
python -m local.run --prices /path/to/prices.csv --config config/notebook_primary.json --output runs/local_csv
```

通过 `python -m local.run --help` 查看完整参数。
## 原生 vn.py 无 GUI 运行

建议在单独虚拟环境安装，保留轻量环境的可复现依赖：

```bash
python -m venv .venv-vnpy
# macOS / Linux
source .venv-vnpy/bin/activate
# Windows PowerShell: .venv-vnpy\Scripts\Activate.ps1
python -m pip install -r requirements-vnpy.txt
python -m local.run_vnpy --demo --output runs/native_demo
python -m local.run_vnpy --prices /path/to/prices.csv --output runs/native_real
```

该入口直接调用原生 BacktestingEngine，加载包内原策略，以 `history_data[(datetime,vt_symbol)]` 和 `dts`
注入 CSV，不调用数据库 `load_data()`，不启动 GUI，也不修改第三方安装目录。
新增入口依据 [官方回测引擎源码](https://github.com/vnpy/vnpy_portfoliostrategy/blob/main/vnpy_portfoliostrategy/backtesting.py)
的接口编写；原生依赖与数据本次环境不具备，所以 **原生完整运行未验证**。
如不同安装版本改变接口，请依报错核对版本；不要用轻量结果替代原生验证结果。
安装成功后把 `python -m pip freeze` 保存为自己的环境锁定文件。


## 4. 阅读输出

用浏览器直接打开所选 `runs/.../report.html`。报告为表格式，不额外生成未审核图像。

- `equity.csv`：每日权益，加展示字段 `normalized_equity` 与 `drawdown`。
- `trades.csv`：原引擎或相应适配器的交易记录。
- `summary.json`：配置、数据种类、依赖版本、输入与原源码SHA-256。
- `run.log`：原策略运行日志。
- `strategy_states.json`／`pending_orders.json`：轻量模式逐日状态和期末未成交委托。
- `native_daily.csv`／`native_statistics.json`：原生模式原引擎结果。

不会强制清空期末持仓；报告记录仍持有仓位。重复运行请指定新输出目录，不覆盖前一轮结果。如需核验原文件，运行 `python -m local.verify_originals`。

## 验证新增边界与保留内容

```bash
python -m local.verify_originals
python -m unittest discover -s tests -v
```
