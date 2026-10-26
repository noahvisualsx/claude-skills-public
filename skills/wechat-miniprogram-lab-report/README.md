# 微信小程序实验报告 skill

一个 Claude Code skill：把《微信小程序》课程的实验报告 docx 交给它，它会读懂实验题目，在本机用微信开发者工具新建项目、写代码、运行并截真实截图，再把步骤、代码、截图、实验分析与体会填回原报告，按学号姓名命名保存。

## 安装（macOS）

这个 skill 收在 [claude-skills-public](https://github.com/noahvisualsx/claude-skills-public) 里，只装它一个：

```bash
git clone https://github.com/noahvisualsx/claude-skills-public.git ~/claude-skills-public
cd ~/claude-skills-public && ./install.sh wechat-miniprogram-lab-report
```

还需要：微信开发者工具（设置 › 安全设置里打开服务端口）、Node.js、python3。装完重开 Claude Code 会话即可。

## 第一次用

1. 照 `references/profiles/示例同学.md` 新建一份自己的 `references/profiles/<姓名>.md`，填上姓名、学号、班级、老师、AppID、工作目录和报告命名规则。
2. 在 Claude Code 里把实验报告 docx 拖进来，说"帮我做这个实验报告"。

不用 Claude Code 的话，`portable/通用提示词-模板.md` 是给豆包、ChatGPT、Kimi 用的提示词，把括号里的信息换成自己的再用（它们不能操作电脑，代码要自己复制进开发者工具运行截图）。

## 文件

- `SKILL.md`：完整流程
- `scripts/`：读报告、建项目、生成素材图、自动截图、填报告的脚本
- `references/profiles/`：每个同学的固定信息
- `portable/`：给其他 AI 用的提示词模板
