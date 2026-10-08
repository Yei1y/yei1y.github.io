# yei1y.github.io

叶伟丰的个人主页（中文 / English 双语）。纯手写 HTML + CSS + JavaScript，无框架、无构建步骤、无追踪。

[yei1y.github.io](https://yei1y.github.io)

## 目录

```
index.html               首页：首屏 / 关于 / 精选项目（6 个）/ 技能 / 荣誉 / 联系
projects/index.html      项目全集：三维评分三线表 / 按岗位裁剪 / 8 张项目卡 / 技能矩阵
assets/css/style.css     设计系统（tokens → 组件 → 响应式 → 打印）
assets/js/main.js        主题、语言、导航、滚动揭示、阅读进度、图像查看器
assets/figures/          由各项目结果文件生成的数据图
tools/make_figures.py    生成 assets/figures/*.png
tools/check_site.py      发布前静态自检
```

## 设计约定

改样式时请一并遵守三条规则：

1. **界面只用一个强调色**（`--deep-mint`）。颜色不承担"区分区块"的职责，所以导航、区块编号、卡片顶边、页脚取同一个色。
2. **颜色只用于编码数据**。六个色相（mint / sky / lav / pink / peach / lemon）只出现在图元里——条形、区间、漏斗段——并且语义固定：mint = 主体，peach = 对照或问题，sky = 稳健性检验。
3. **数字可核验**。正文与图中的每个数都来自对应仓库的结果文件（`results/`、`output/tables/`）。图里的原始数值直接标在条上或写进图注，画布上的长度只做视觉映射，映射方式在注里写明。

## 页面结构约定

每个项目条目按固定顺序排列，便于横向比较，也让读者知道下一个数字在哪里：

```
编号 + 类别短语  →  标题  →  方法与角色（meta）  →  一段说明
→  三个关键数字（.stats）  →  数据图（.fig 手绘 / .media 渲染图）  →  标签 + 链接
```

数据图有两类，视觉上刻意区分：

- `.fig`：用 CSS 画的条形、区间、漏斗，与正文同色，适合表达"顺序 / 占比 / 区间"。
- `.media`：`tools/make_figures.py` 生成的 PNG，配 `data-zoom` 按钮点击放大。

## 生成数据图

```bash
python tools/make_figures.py                     # 默认读 D:\codes\项目，输出 assets/figures
python tools/make_figures.py --root <项目根目录> --out <输出目录>
```

脚本只从结果文件取数（`test_probabilities.csv`、`scad_selected_features.csv`、`robustness_results.csv`、`economic_scenarios.csv` 等），不手抄数值。运行时会顺手复核关键数字并打印，例如由测试概率重算 ROC-AUC 与仓库报告的 0.9380 对照。

配色以十六进制字面量写在脚本顶部，与 `assets/css/style.css` 的 token 一一对应；**改色时两处需同步**。

## 发布前自检

```bash
python tools/check_site.py .
```

检查项：标签配平与嵌套、**zh/en 容器级配对**、无残留内联颜色、本地资源存在、`<img>` 标注的宽高与文件一致（避免加载跳动）、图片体积上限、无过期文案与旧仓库名。全部通过输出 `RESULT: PASS`。

## 双语与无障碍

- 每段文案成对提供 `<span class="zh">` / `<span class="en">`，由 `html[data-lang]` 切换；两侧数量必须相等（自检会验）。图注遵循同一约定；图内的文字标签本身是中文，因此中英模式共用同一张图。
- 语言按钮的标签与查看器图注都会跟随当前语言更新。
- 内容不会因动画失效而不可见：滚动揭示带 2.5 秒兜底。

## 部署

GitHub Pages，`main` 分支根目录直接发布。推送后约一分钟生效。
