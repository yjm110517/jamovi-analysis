# Jamovi 自动化分析引擎 (Jamovi Analysis)

> 🇺🇸 [View English README](README.md)

Jamovi Analysis 是一个专为自动化调用本地 [jamovi](https://www.jamovi.org/) 统计软件而设计的集成工具库。它作为一个中间层，允许外部脚本或 AI Agent 通过程序化代码或**自然语言**的方式触发高级统计分析，无需打开 jamovi 的图形用户界面（GUI），即可直接生成规范的 `.omv` 项目文件与统计报告。

---

## 项目结构

```
jamovi-analysis/
├── agents/
│   └── openai.yaml          # OpenAI Agent 接口配置
├── references/
│   ├── analysis-map.md      # jmv 函数映射表 & 项目模式分析覆盖范围
│   ├── install-layout.md    # 本地 jamovi 安装路径参考
│   └── project-mode.md      # 结构化规格契约、度量规则 & 生命周期
├── scripts/
│   ├── find-jamovi.ps1              # 自动寻址 jamovi 安装目录
│   ├── invoke-jamovi-project.ps1    # 核心入口：生成 .omv 工程文件 + Markdown 报告
│   ├── invoke-jamovi-r.ps1          # 通过 jamovi 内置 R 环境执行批量统计
│   ├── run-jamovi-project.py        # 核心 Python 执行器（勿直接调用）
│   └── start-jamovi-server.ps1      # 启动交互式 jamovi.server 进程
├── SKILL.md                 # AI Agent 技能清单（Skill Manifest）
├── README.md                # 英文版说明文档
└── README_zh.md             # 本文件（中文版）
```

---

## 核心功能与运行模式

项目根据不同的业务场景和输出诉求，提供三种核心处理模式：

### 1. 核心项目模式（`scripts/invoke-jamovi-project.ps1`）

这是本工具最强大、生命周期最完整的核心工作流。通过底层调用 jamovi 内置 Python 引擎实现：

- **极简调用**：同时支持结构化 JSON 配置和自然语言指令（例如：*"帮我跑一下年龄和分数的描述性统计"*）。
- **智能校验**：自动接管数据流，在执行分析前检查并修正各列的"度量类型"（连续型、名义/分类型等），避免运行时崩溃。
- **高可用容错**：对各项统计任务进行串行调度，内置单任务超时监控。如果某个运算锁死，系统自动重启内部计算引擎并继续下一个任务。
- **双轨产物落盘**：分析完成后，生成带时间戳的 jamovi 工程文件（`.omv`）及自动提取核心统计指标的 Markdown 快速阅读报告。

**v1 已支持的分析类型：**

| 分析名称 | `jmv` 函数 |
|---|---|
| 描述性统计 | `descriptives` |
| 独立样本 T 检验 | `ttestIS` |
| 单因素方差分析（One-Way ANOVA） | `anovaOneW` |
| 相关矩阵 | `corrMatrix` |
| 线性回归 | `linReg` |
| 二元逻辑回归 | `logRegBin` |
| 列联表卡方检验 | `contTables` |
| 信度分析（Cronbach α） | `reliability` |

> v1 项目模式暂不支持 PCA、EFA 及 CFA。

### 2. R 语言批处理模式（`scripts/invoke-jamovi-r.ps1`）

当你不需要保存 `.omv` 工程文件、只想在终端快速获取统计结论时使用。流程将绕过应用层，直接挂载 jamovi 内部绑定的 R 环境及 `jmv` 核心统计包执行 R 脚本。

### 3. 交互式服务模式（`scripts/start-jamovi-server.ps1`）

在后台启动 jamovi 服务进程（`python -m jamovi.server`），并暴露动态分配的端口和 Access Key。适用于需要通过浏览器或定制前端进行可视化数据交互的场景。

---

## 环境依赖与运行时隔离

- 必须安装本地台式机版本的 **jamovi**。封装脚本具备**全盘动态寻址**能力，会自动检索 Windows 注册表及标准应用目录，无缝支持自定义安装路径（C、D、E 盘等）。
- 执行入口为 **Windows PowerShell**。
- **环境强隔离**：为避免与系统中的 Python、Conda 等外部环境冲突，脚本在每次启动前会清理 `PYTHONHOME`、`PYTHONPATH`、`VIRTUAL_ENV` 及所有继承的 `CONDA_*` 环境变量，**严格锁定使用 jamovi 闭环内绑定的解释器**进行作业。

---

## 快速上手

### 1. 项目模式 — 生成 `.omv` 工程文件 + Markdown 报告

**自然语言驱动：**
```powershell
& '.\scripts\invoke-jamovi-project.ps1' `
  -DataPath 'C:\data\study.csv' `
  -Request 'Run descriptives for score and age'
```

**结构化 JSON（单个分析）：**
```powershell
& '.\scripts\invoke-jamovi-project.ps1' `
  -DataPath 'C:\data\study.csv' `
  -SpecJson '{"analysis_type":"ttestIS","variables":{"vars":["score"],"group":"group"}}'
```

**结构化 JSON（批量分析）：**
```powershell
& '.\scripts\invoke-jamovi-project.ps1' `
  -DataPath 'C:\data\study.csv' `
  -SpecJson '{
    "output_basename": "study-report",
    "analyses": [
      {"analysis_type": "descriptives", "variables": {"vars": ["score", "age"]}},
      {"analysis_type": "ttestIS", "variables": {"vars": ["score"], "group": "group"}}
    ]
  }'
```

可选参数：`-OutputDir`、`-OutputBasename`、`-AnalysisTimeoutSeconds`、`-PollIntervalMs`、`-JamoviHome`。

### 2. R 批处理模式 — 终端快速统计

```powershell
& '.\scripts\invoke-jamovi-r.ps1' -Code 'library(jmv); descriptives(data.frame(x=c(1,2,3,4,5)), vars="x")'
```

### 3. 交互式服务模式

```powershell
& '.\scripts\start-jamovi-server.ps1'
```

---

## 自然语言模式说明

NL 模式采用确定性、快速失败的解析器，返回严格的 JSON 契约：

```json
{
  "is_executable": true,
  "missing_info": "",
  "analysis_spec": {
    "analysis_type": "corrMatrix",
    "variables": { "vars": ["score", "age"] }
  }
}
```

若指令不明确，`is_executable` 将为 `false`，并在 `missing_info` 字段中说明缺失内容。建议使用精确列名和明确的动词结构，例如：

- `Run descriptives for score and age`（for 后接变量名）
- `Run an independent samples t-test for score by group`（by 后接分组变量）
- `Run one-way ANOVA for score by condition`
- `Predict outcome from age and score`

---

## AI Agent 集成

`agents/openai.yaml` 定义了本工具的 OpenAI 兼容 Agent 接口：

- **显示名称**：Jamovi Analysis
- **描述**：协助完成 jamovi 统计工作流并生成 `.omv` 项目文件

配合 `SKILL.md` 中的技能清单，AI Agent（如 OpenAI tool-use API）可直接程序化调用本工具的全部能力。

---

## 参考文档

| 文件 | 用途 |
|---|---|
| [`references/install-layout.md`](references/install-layout.md) | 已验证的本地 jamovi 安装路径（Python、R、模块目录） |
| [`references/analysis-map.md`](references/analysis-map.md) | `jmv` 函数映射表与项目模式分析覆盖范围 |
| [`references/project-mode.md`](references/project-mode.md) | 结构化规格契约、度量类型规则、生命周期与超时处理 |

---

## 输出验证

在修改 Python 执行器后，可以不启动 jamovi GUI 而直接验证 `.omv` 产物的合法性：

```python
from zipfile import ZipFile

with ZipFile("report.omv") as archive:
    names = archive.namelist()
    assert "metadata.json" in names
    assert any(name.endswith("/analysis") for name in names)
```

每次修改执行器后，务必通过 `invoke-jamovi-project.ps1` 执行真实的冒烟测试。
