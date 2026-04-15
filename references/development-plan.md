# Development Plan: Template-Driven Optimization

> 本文档记录 jamovi-analysis 项目的优化实施计划。核心目标是以"输入/输出模板"为优先，让整个 Skill 的调用流程更规范、输出更符合教育研究论文的 APA 7th 格式。

---

## 核心思路

不再只是"能跑通"，而是要做到：

1. **输入标准化**：用户拿到 CSV/Excel 模板就知道数据该怎么列、怎么命名
2. **输出论文化**：生成的 Markdown/DOCX 表格和文本直接符合 APA 7th 教育论文规范
3. **AI 调用更准确**：`SKILL.md` 和代码通过模板约束，降低歧义，提升输出稳定性

---

## Phase 1：输入数据模板与规范（优先）

### 1.1 创建 `templates/input/` 目录

为每种常用教育研究场景提供**可直接填写的 Excel/CSV 模板**：

| 模板文件 | 适用场景 | 数据组织要求 |
|---|---|---|
| `prepost_scale_study.csv` | 前测后测量表研究 | `user_id`, `group`, `pre_q01~q12`, `post_q01~q12` |
| `cross_sectional_survey.csv` | 横断面问卷研究 | `user_id`, `gender`, `age`, `q01~q20` |
| `ttest_two_group.csv` | 两组独立样本比较 | `group`, `score` |
| `reliability_scale.csv` | 信度分析 | `q01~q15`（无分组） |
| `regression_study.csv` | 回归分析 | `y`, `x1`, `x2`, `gender` |

每个模板附带：
- **README 说明**：每列的含义、允许的缺失值表示方式、反向题的标记方法
- **数据校验规则**：如量表数据必须是 1~5 或 1~7 的整数，性别列必须是 `男/女` 或 `1/2`

### 1.2 强化预处理层的"模板感知"

在 `run-jamovi-project.py`（或拆分后的 `preprocess.py`）中：
- 当用户指定 `template_hint`（如 `"prepost_scale_study"`）时，自动执行更严格的列名和数值范围校验
- 如果检测到数据格式与模板不符，返回**具体错误**（如 `"检测到 pre_q01 列存在小数，量表题应为整数"`）

---

## Phase 2：输出报告模板（APA 7th 教育论文格式）

基于 APA 第7版和教育心理学论文规范，设计严格的输出模板。

### 2.1 创建 `templates/output/` 目录

定义每种分析的标准输出格式文档：

#### 描述统计（Descriptives）

**APA 表格规范：**

```markdown
Table 1
Descriptive Statistics for Study Variables (N = 120)

| Variable          | M     | SD   | Min  | Max  |
|-------------------|-------|------|------|------|
| Creativity        | 3.82  | 0.71 | 1.00 | 5.00 |
| Algorithmic Thinking | 3.45 | 0.89 | 1.00 | 5.00 |

Note. Scores range from 1 to 5.
```

**分组描述统计：**

```markdown
Table 2
Descriptive Statistics for Creativity by Teaching Method

| Variable   | Traditional (n = 25) | Experimental (n = 25) |
|------------|----------------------|-----------------------|
|            | M         | SD       | M         | SD        |
| Pretest    | 72.40     | 8.60     | 71.80     | 9.20      |
| Posttest   | 78.20     | 7.90     | 85.60     | 6.40      |
```

#### 独立样本 t 检验（ttestIS）

**文本报告规范：**

> 实验组（*M* = 85.00，*SD* = 10.00）的测试成绩显著高于对照组（*M* = 80.00，*SD* = 15.00），*t*(49) = 2.17，*p* = .021，*d* = 0.53。

**表格规范：**

```markdown
Table 3
Independent Samples t-Test for Test Scores by Group

| Variable   | Group 1 (n = 25) | Group 2 (n = 25) | t(48) | p    | Cohen's d | 95% CI       |
|------------|------------------|------------------|-------|------|-----------|--------------|
|            | M      | SD       | M      | SD       |       |      |           |              |
| Test Score | 80.00  | 15.00    | 85.00  | 10.00    | 2.17  | .021 | 0.53      | [0.10, 1.05] |
```

#### 配对样本 t 检验（ttestPS）

**文本报告规范：**

> 后测成绩（*M* = 85.60，*SD* = 6.40）显著高于前测成绩（*M* = 71.80，*SD* = 9.20），*t*(24) = 4.25，*p* < .001，*d* = 1.05。

#### 方差分析（ANOVA）

**文本报告规范：**

> 噪声条件对反应时的主效应显著，*F*(3, 27) = 5.94，*p* = .007，*η*²p = .40。

#### 相关分析（Correlation Matrix）

**表格规范：**

```markdown
Table 4
Correlation Matrix for Study Variables

| Variable          | 1      | 2      | 3      |
|-------------------|--------|--------|--------|
| 1. Creativity     | —      |        |        |
| 2. Algorithmic    | .45**  | —      |        |
| 3. Critical Thinking | .32* | .28    | —      |

Note. *p < .05. **p < .01.
```

#### 回归分析（Linear Regression）

**表格规范：**

```markdown
Table 5
Summary of Linear Regression Analysis

| Variable   | b     | SE   | β    | t(116) | p    | 95% CI       |
|------------|-------|------|------|--------|------|--------------|
| Intercept  | 2.10  | 0.45 | —    | 4.67   | <.001| [1.21, 2.99] |
| Age        | 0.15  | 0.05 | 0.25 | 3.00   | .003 | [0.05, 0.25] |
| Gender     | -0.30 | 0.12 | -.18 | -2.50  | .014 | [-0.54, -0.06]|

Note. R² = .18, Adjusted R² = .16, F(2, 117) = 12.45, p < .001.
```

#### 信度分析（Reliability）

**表格规范：**

```markdown
Table 6
Reliability Analysis (Cronbach's α)

| Scale/Subscale   | Items | α    |
|------------------|-------|------|
| Creativity       | 5     | .82  |
| Algorithmic      | 4     | .76  |
| Critical Thinking| 6     | .79  |
| Total Scale      | 15    | .85  |
```

### 2.2 代码层面：让提取器输出 APA 格式

当前代码中的 `build_*_sections` 函数需要重构，使其输出严格匹配上述模板：

- **统计符号斜体化**：在 Markdown 中用 `*M*`、`*SD*`、`*t*`、`*p*`、`*r*`、`*F*`、`*β*`
- **小数位统一**：保留两位小数（p 值可保留三位，但 APA 常规两位）
- **表格只使用横线**：Markdown 表格天然符合这一点
- **相关系数去掉前导零**：`.45` 而非 `0.45`
- **效应量强制输出**：t 检验必须输出 Cohen's d；ANOVA 输出 η²p；回归输出 R² 和 Adjusted R²

### 2.3 增强 `table_style: "apa"` 模式

当前 `output.table_style` 支持 `gfm`（默认）和 `apa`。需要把 `apa` 模式做得更"严格"：
- `gfm`：通用 GitHub Markdown，保留当前格式
- `apa`：完全按照上述 APA 7th 教育论文模板输出表格和文本
- （可选）新增 `apa_strict`：如果提取不到某个 APA 要求的字段（如 Cohen's d），标记为 missing 而不是省略

---

## Phase 3：示例与文档（用模板驱动）

### 3.1 `examples/` 目录与模板绑定

每个 example 直接关联一个输入模板和一个输出模板：

```
examples/
├── prepost_scale_study/
│   ├── input.csv              # 基于 templates/input/prepost_scale_study.csv
│   ├── jobfile.json
│   ├── expected_output.md     # 严格按 APA 格式的预期输出
│   └── expected_output.docx
├── ttest_study/
├── regression_study/
└── reliability_study/
```

### 3.2 重写 `SKILL.md`

增加"数据准备指南"和"输出格式规范"两个大章节：

- **数据准备**：告诉用户"你的数据必须是宽格式（wide format），每行一个被试，每列一个变量"
- **输入模板速查**：列出 5 种模板，用户可直接下载 `templates/input/*.csv` 填写
- **输出格式速查**：列出每种分析对应的 APA 报告格式示例
- **常见错误**：
  - 量表题用了小数 → 预处理报错
  - 分组变量有 3 个水平但做了 t 检验 → 自动拒绝或提示改用 ANOVA
  - 反向题命名不规范 → 给出正确命名示例（如 `q24_rev`）

### 3.3 新增 `references/output-templates.md`

作为开发文档，定义每种分析类型的**提取器输出规范**。以后改代码时对照这个文档，确保输出不变形。

---

## Phase 4：代码结构优化（支撑模板落地）

### 4.1 拆分 `run-jamovi-project.py`（同原计划，但优先级后置）

将巨型文件拆分为：
- `preprocess.py` — 新增模板校验逻辑
- `extract/` 包 — **这是本次修改的核心**，每个分析类型一个 extractor 文件
- `reporters/` 包 — Markdown / DOCX 生成器，按 `table_style` 选择模板引擎
- `schema.py` — 增加 `template_hint` 和输出格式配置校验

### 4.2 提取器重构（重点）

当前所有 `build_*_sections` 混在一起。建议改成：

```
extractors/
├── __init__.py
├── base.py           # 通用提取工具
├── descriptives.py
├── ttest_is.py
├── ttest_ps.py
├── anova.py
├── correlation.py
├── regression.py
├── reliability.py
└── contingency.py
```

每个 extractor 的职责：
1. 从 jamovi 结果树中提取原始数据
2. 按 APA 格式组装成字典
3. 如果某个字段缺失，返回明确的 `missing_reason`

### 4.3 报告生成器增强

`report.py` 中新增 `APATableFormatter` 类：
- 自动添加 `Table 1`, `Table 2...` 编号
- 表名斜体
- Note 区域自动拼接
- DOCX 输出时使用 APA 模板渲染

---

## Phase 5：测试（以模板为断言基准）

### 5.1 模板回归测试

对 `examples/*/expected_output.md` 和实际生成的 `.md` 做文本比对：
- 关键表格结构一致
- APA 符号（`*M*`, `*SD*`）存在
- 数值在容差范围内一致

### 5.2 提取器单元测试

为每个 `extractors/*.py` 写测试，用 mock 的 jamovi 结果树验证输出字典格式严格匹配模板规范。

---

## 修改后的成功标准

- [ ] `templates/input/` 含 5+ 可直接填写的数据模板文件
- [ ] `templates/output/` 含 8 种分析类型的 APA 格式规范文档
- [ ] `table_style: "apa"` 输出的表格和文本严格符合 APA 7th 教育论文规范
- [ ] t 检验输出包含 Cohen's d；ANOVA 输出包含 η²p；回归输出包含 R²/Adjusted R²/β
- [ ] `SKILL.md` 有完整的"数据准备"和"输出格式"章节
- [ ] 每种 example 都绑定一个输入模板和预期的 APA 格式输出
- [ ] 预处理层能根据 `template_hint` 做格式校验并给出具体错误提示
- [ ] `run-jamovi-project.py` 拆分完成，extractors 独立成包

---

## 说明

这个计划的核心变化是：把"代码重构"从最高优先级降了一级，把"输入/输出模板规范"提到了最前面。这样可以在改动核心代码之前，先建立起"正确输出应该长什么样"的共识，减少后续返工。
