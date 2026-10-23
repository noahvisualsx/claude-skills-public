---
name: wechat-miniprogram-lab-report
description: 自动完成"微信小程序"课程的实验报告（docx）——读懂报告里的实验内容，按题目在本机用微信开发者工具新建无模板项目、写代码、自动运行并截模拟器/开发者工具截图，再把步骤/代码/截图/实验分析与体会填回原报告，按学号姓名命名保存。当用户丢来一份或多份微信小程序实验报告/实验任务 docx，或说"帮我做实验N""这里面有几个实验报告你开始做""把这个实验报告填好""小程序实验截图""把头像换成xx重新截图"时使用。
---

# 微信小程序实验报告自动完成

目标：用户给空白（或半填）的实验报告 docx → 交回**代码真的能跑、截图是真实截图**、格式与原模板一致的完整报告，外加每个实验对应的小程序项目文件夹。可一次处理多份报告（每份独立走一遍流程）。

## 0. 先确定是谁的报告
可能有多个同学在用，每人一份固定信息放在 `references/profiles/<姓名>.md`（格式见 `示例同学.md`：姓名、学号、班级、老师、AppID、目录、命名规则）。

表头只有 XX 占位时，**不要按指导老师猜是谁**（同一个老师可能带好几个学生），先问。

看报告表头的姓名/学号或文件名来匹配。**以报告表头为准**；表头是 "XXX" 占位就用 profile 填（见第 4 步 `cells`）。
新同学：照已有 profile 新建一份（姓名、学号、班级、老师、AppID、目录、命名规则），AppID 可从其已有项目的 `project.config.json` 里找，找不到就问。

## 1. 读报告
```bash
S=~/.claude/skills/wechat-miniprogram-lab-report/scripts
python3 $S/read_report.py "报告.docx"
```
输出每个单元格文字，并把内嵌图片导出到 `报告_media/`（image1 一般是校徽，不用管）。**用 Read 逐张看效果图**，照着颜色、文字、布局、tabBar 做。
列出"2．实验内容"里的每一小题；第 1 题通常是"文档命名/提交"，**不作答**。

## 2. 建项目 —— 每个实验都新建，不使用模板、不用云服务
```bash
python3 $S/new_project.py "<实验目录>/miniprogram-<N>" --appid <AppID> --name "<项目名>" --pages index,about
```
实验目录、成品报告放哪按 profile 里的目录约定（例如 `实验报告/实验N/`，成品报告放 `实验报告/`）。
- 这是最小骨架，没有 navigation-bar 组件等模板残留。用户旧项目里带模板残留的，**不要拿来改**，新建后只把有用的页面代码拷过来。
- 按题目写 `app.json`（pages/window/tabBar/networkTimeout…）、`sitemap.json` 和每页四件套。代码**学生水平、简洁、少量中文注释**，只写题目要求的东西，可适度个性化（题目常写"可个性化修改"）。
- 需要下拉刷新/上拉触底的，页面 js 里写 `onPullDownRefresh`（toast + stopPullDownRefresh）和 `onReachBottom`（toast），截图才看得出效果。
- 宽度百分比 + padding/border 的元素记得 `box-sizing: border-box`（否则两列/三列会挤成一列少一格）。

### 图片素材
没有老师素材、**不能用真人照片**，用 `make_assets.py` 生成：
```bash
python3 $S/make_assets.py tab  images intro=👩 youth=🌸 film=🎬 campus=🧡   # tabBar 灰/彩两套 81x81
python3 $S/make_assets.py icon images icon1=🍜 icon2=⚽ ...                  # 九宫格等彩色图标
python3 $S/make_assets.py banner images/banner1.jpg "我的大学生活" 🏫 "#4285F4" "#A0C8FF"
python3 $S/make_assets.py avatar images/avatar.jpg      # 卡通头像占位
python3 $S/make_assets.py doraemon images/avatar.jpg    # 多啦A梦头像（用户点名要时）
```
背景图、场景插画这类特殊图直接用 PIL 现画（渐变 + 简单几何形状）。生成后用 Read 看一眼。

## 3. 自动运行 + 截图
前置（只需一次）：微信开发者工具已登录（`cli islogin` → `{"login":true}`），且 **设置 → 安全设置 → 服务端口 = 开启**。

### 3a. 模拟器截图
写 plan.json（格式见 `scripts/shoot.js` 顶部注释），每个要"运行结果截图"的小题至少一张；有交互的要真的执行再截：
- 输入查找：`{"input":["input","PHP"]}`；跳转：`navigateTo` / `switchTab`
- 下拉刷新：`{"pullDown":true,"wait":700}`（toast 还在时截）
- 上拉触底：`{"evaluate":"wx.pageScrollTo({scrollTop: 5000, duration: 0})","wait":700}`
- 点第 n 个格子：`page.$` 只取第一个元素，用 `{"callMethod":["onTap",{"currentTarget":{"dataset":{"index":2,"name":"运动"}}}]}`
- 首个页面 `wait` 给 3000（图片加载）
```bash
cd $S && node shoot.js /abs/plan.json
```
shoot.js 会先 `cli quit` 关掉已开的开发者工具再启动（否则报 `timeout waiting for automator response`），失败自动重试一次，截完自动去掉圆角外残影。重试后仍报 "please make sure http port is open" 才是端口没开，让用户去开。
第一次运行缺 node_modules：`cd $S && npm install`。

### 3b. 开发者工具界面截图（"了解开发界面""对项目配置文件截图"这类题）
```bash
bash $S/ide_shot.sh <项目目录> <输出.png>
```
打开项目并用 `screencapture -l <窗口ID>` 截整个开发者工具窗口（窗口 ID 由 `window_id.swift` 取）。编辑器里显示的是该项目上次打开的文件。
要让编辑器显示某个文件（如 app.json）、收起底部调试面板：用 computer-use（`request_access` 微信开发者工具，bundle `com.github.Electron`）：
1. `app_screenshot` 看窗口；若窗口在别的桌面空间且点不动，`request_full_control` 后用 `computer_batch` 按 `cmd+p` → 输入 `app.json` → `Return`（IDE 在前台时按键能送达）。
2. 回到 `app_*`：`app_click` 可访问性元素"切换面板 (⌘J)"收起调试器；`app_scroll` 滚动编辑器看后半段。
3. 截图：`WID=$(swift $S/window_id.swift); screencapture -x -o -l $WID out.png`。配置文件长就滚动后再截一张。
4. 用完 `app_release`。

**每张截图都用 Read 检查**：内容对不对、有无报错/空白/残影。不对就改代码重截。
开发者工具实在用不了（没登录、没开端口且用户不在）：仍写好代码，截图位置写"【此处插入 xx 截图】"并告诉用户哪几处要手动截。**绝不伪造截图**。

## 4. 填报告
写 content.json（格式见 `scripts/fill_report.py` 顶部注释），代码块直接从项目文件读（写个小 Python 脚本组装 JSON，别手抄代码）：
- `cells`：表头是 "XXX / 24级XX班" 这类占位时，按 `read_report.py` 显示的 `[T0 Rr Cc]` 坐标填本人信息（replace 分不开重复的 XXX）。
- `replace`：表头"时间:""周次"空的/旧的才更新（时间 = 上课当天，如 `2026-9-24`）。
- `sections.4` "实验方法和步骤"：**按题目序号**写（`2、` `3、`…；小题 `（1）（2）`），每题 1~3 句步骤说明 + 该题相关代码（`label` 用 `app.json` / `index.wxml` …）。
- `sections.5` "程序及测试结果"：按题号放截图。手机截图用 `imgs` 同一行并排 2~3 张（width_cm 4.5~5）；开发者工具窗口截图用 `img` width_cm 14.5；AppID 这类直接写文本（`2、AppID：wx...`）。
- `sections.6` "实验分析与体会"：一段 120~200 字，第一人称，"本次实验……"开头：学到了什么 + 一个具体小问题及解决 + 收获。优先写**这次真实碰到的问题**；编的要在交付时告诉用户。
- `date`：实验日期。
- 字体：fill_report.py 填入的所有文字（正文、标题、代码、表头）一律**宋体**（中英文都是），代码只是字号小一号（9pt）。
```bash
python3 $S/fill_report.py 原报告.docx content.json "<profile 约定的成品位置>/<按 profile 命名>.docx"
```
**不覆盖用户给的原文件**，按 profile 的目录约定输出。改了素材要重截时：重截 → 用同一个 content.json 重新 fill 即可。

## 5. 检查并交付
- `read_report.py` 读输出文件确认表头和各部分到位；可 `soffice --headless --convert-to pdf`（LibreOffice 在 `/Applications/LibreOffice.app/Contents/MacOS/soffice`）+ `pdftoppm -r 40` 看版式。PDF 里中文可能显示不出来，是 LibreOffice 字体问题，docx 本身没事。
- 中间脚本放 scratchpad，别留在用户目录。
- 告诉用户：报告路径、项目路径、哪些是自动截图、哪些图是生成的占位（可换成本人照片）、模板里发现的问题（如实验名称抄错）、需要本人做的事（注册账号、扫码登录、提交学生端）。

## 注意
- 只有用户本人能做的事（注册公众平台账号、扫码登录、提交到学生端）不要代做，报告里写结果即可。
- 报告模板每个大项是一个合并单元格，脚本按"4．""5．""6．"开头定位；换了模板定位失败先 read_report 看结构再调脚本。
- `portable/通用提示词-模板.md` 是给豆包 / ChatGPT 用的提示词，把括号里的个人信息换成自己的再用。改流程时两边保持一致。
