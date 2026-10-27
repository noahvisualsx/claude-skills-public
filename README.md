# Claude Skills

> 生图、视频类 skill（提示词、照片复刻、视频复刻等）在 [noahvisualsx-skill](https://github.com/noahvisualsx/noahvisualsx-skill)。

我自己做的 Claude / Claude Code skill 合集。

## 新电脑一键安装

```bash
git clone https://github.com/noahvisualsx/claude-skills-public.git ~/claude-skills-public
cd ~/claude-skills-public && ./install.sh
```

装完重开 Claude Code 会话即可使用。`install.sh` 会：

- 把 `skills/` 下每个 skill 软链接到 `~/.claude/skills/`，以后 `git pull` 就自动更新；已有同名 skill 会先备份到 `~/.claude/skills-backup-<时间>/`
- 在 `wechat-miniprogram-lab-report/scripts` 里 `npm ci` 装 `miniprogram-automator`
- `pip install --user -r requirements.txt`（python-docx、pillow、numpy、opencv-python-headless）
- 检查 python3 / node / swift / expect / 微信开发者工具 是否就绪

常用参数：

```bash
./install.sh node-ops 嵌入式   # 只装部分 skill
./install.sh --copy            # 复制而不是软链接（之后可删掉仓库）
./install.sh --no-deps         # 跳过 npm / pip
./install.sh --uninstall       # 移除本仓库装进去的 skill
```

> `refimg-prompt-cn`、`faceswap-prompt-cn`、`pose-expression-prompt-cn`、`platform-article-writer`、`x-article-pipeline`、`x-viral-writer`、`code-tutor` 原本是 claude.ai 上的 skill。同一账号登录 Claude 桌面版时它们也会自动同步，本地再装一份可能出现重复；只想要本地那 5 个时：
> `./install.sh apple-ui-design node-ops php-mysql-coursework wechat-miniprogram-lab-report 嵌入式`

### 外部依赖（脚本不会自动装）

| Skill | 需要 |
|---|---|
| wechat-miniprogram-lab-report | macOS、Node.js、Xcode 命令行工具（swift）、微信开发者工具（登录 + 设置→安全设置→服务端口 开启） |
| php-mysql-coursework | 本地验证时需要 MySQL / PHP（`brew install mysql php`）；生成 docx 时临时 `npm install docx` |
| node-ops | `ssh`、`expect`（macOS 自带）；SSH 密钥 `~/.ssh/jp_vps` 不在仓库里，首次使用会按 SKILL.md 现生成 |
| 嵌入式 | python3 |

## 列表

| Skill | 说明 |
|---|---|
| [`apple-ui-design`](skills/apple-ui-design) | 按 Apple 最新设计规范（HIG 2026 / Liquid Glass / iOS·macOS 26–27）设计、实现、审查 Apple 平台界面。用户说… |
| [`code-tutor`](skills/code-tutor) | 一对一教编程的方法，重点是 C 语言和中国专升本 / 期末考备考。当用户贴代码问"这是什么意思"、贴报错截图、说"看不懂 / 没听懂 / 好难 / 我才刚入门"… |
| [`faceswap-prompt-cn`](skills/faceswap-prompt-cn) | 为 ChatGPT Image / Nano Banana / 即梦等模型编写中文换脸提示词——把用户「母图」里角色的脸，移植到另一张「场景图」的画面里，身份不… |
| [`github-gems-cn`](skills/github-gems-cn) | 在 GitHub 上找刚火起来的开源项目（付费软件平替、Mac 小工具、AI 创作工具），核对星数、协议、安装包大小，写成中文推荐短推… |
| [`node-ops`](skills/node-ops) | 自建代理 VPS 节点的搭建、巡检、排查、订阅运维（Xray VLESS-Reality + Cloudflare WARP 解锁 + Hysteria2 + … |
| [`php-mysql-coursework`](skills/php-mysql-coursework) | 完成"PHP动态网站开发"一类的课程设计/上机/补考任务，包括两种形态——(1) 老师给一个 DEMO 参考网站（PHP+MySQL，通常是图书/学生管理之类的… |
| [`platform-article-writer`](skills/platform-article-writer) | 为今日头条、百家号、微信公众号、小红书、知乎、X/推特等平台写文章或帖子，按平台排版，逻辑清楚、像真人写的、没有AI味。用户说“写一篇头条/百家号/公众号/推文… |
| [`pose-expression-prompt-cn`](skills/pose-expression-prompt-cn) | 人物拍照姿势表情动作——基于一张已有照片写中文微调提示词，锁死身份/服装/场景/机位，只改表情与手部动作，一次出多张成组图。当用户说「按这张图换个表情」「换个姿… |
| [`refimg-prompt-cn`](skills/refimg-prompt-cn) | 用多张参考图（人脸 / 背景 / 服装妆造）撰写中文 AI 生图提示词，锁定人物身份一致性。当用户要复刻某张照片、用参考图生成人物写真、做古风妆造或 cos 系… |
| [`wechat-miniprogram-lab-report`](skills/wechat-miniprogram-lab-report) | 自动完成"微信小程序"课程的实验报告（docx）——读懂报告里的实验内容，按题目在本机用微信开发者工具新建无模板项目、写代码、自动运行并截模拟器/开发者工具截图… |
| [`x-article-pipeline`](skills/x-article-pipeline) | 把一个热门话题（新模型、新产品、科技新闻）做成一整套 X（推特）长文发布物料的完整流程：联网调研 → 写中文长文正文 → 按 X Articles 编辑器排版 … |
| [`x-article-standard`](skills/x-article-standard) | 推特 / X 长文（Articles）写作规范和图文工作台对接：按 X 官方 Creator Academy 规范和 @noahvisualsx 的风格写长文、教程… |
| [`x-viral-writer`](skills/x-viral-writer) | 给 @noahvisualsx 写推特/X 内容：长文 Article、短推、串推、发布文案和首评，含每日选题。用户说写推特、推文、X 长文、教程帖、羊毛帖、发… |
| [`嵌入式`](skills/嵌入式) | 填写"嵌入式技术实验"（STM32CubeMX + Keil + Proteus，STM32F103C6）实验报告 docx 里的「4．实验方法和步骤（含设计）… |
