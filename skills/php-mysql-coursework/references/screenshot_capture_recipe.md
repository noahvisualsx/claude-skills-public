# 给报告截真实运行截图的方法

设计说明书里的"运行截图"必须是系统真的跑起来之后截的，不能拿设计稿或
草图凑数——评分标准里这类课程设计通常明确要求"主要代码及运行截图"，截图
就是证明代码真的能跑的证据。下面是一套不依赖手动点浏览器、可以批量出图的方法。

## 前提：本地站点已经用 PHP 内置服务器 + 隔离 MySQL 跑起来

见 `scripts/setup_isolated_mysql.sh`，配合 `php -S 127.0.0.1:端口` 起站点。

## 第一步：用 curl 模拟登录，拿到已登录的页面 HTML

系统大多是 session 鉴权，直接用无头浏览器打开某个受保护页面会被弹回登录页。
先用 curl 走一遍登录流程拿到 session cookie，再用同一个 cookie 把每个页面的
HTML 抓下来存成本地文件：

```bash
mkdir -p /tmp/report_shots
curl -s -c /tmp/pv.txt -b /tmp/pv.txt -d "username=admin&password=admin123" \
     http://127.0.0.1:8822/checkuser.php > /dev/null

curl -s -b /tmp/pv.txt "http://127.0.0.1:8822/index.php"      -o /tmp/report_shots/p_index.html
curl -s -b /tmp/pv.txt "http://127.0.0.1:8822/add_xxx.php"    -o /tmp/report_shots/p_add.html
curl -s -b /tmp/pv.txt "http://127.0.0.1:8822/result1.php" -d "id=xxx" -o /tmp/report_shots/p_result1.html
# ...其余页面同理，GET 用 -G，POST 用 -d

cp 项目目录/mystyle.css /tmp/report_shots/mystyle.css   # 页面里 <link href="mystyle.css"> 是相对路径
```

把 HTML 存成本地文件而不是直接截活页面，是因为这样截图跟"用户到底有没有
打开浏览器"完全解耦，可以一次性批量生成，出问题也方便反复重试。

## 第二步：用无头 Chrome 挨个截图

macOS 自带 Chrome 的话直接调用它的二进制，不需要装 Selenium/Playwright：

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless --disable-gpu --window-size=1280,900 \
  --screenshot="/tmp/report_shots/p_index.png" \
  "file:///tmp/report_shots/p_index.html"
```

## 坑：`min-height:100vh` 布局会在截图里留一大块空白

很多后台管理风格的 CSS 会给最外层容器设 `min-height:100vh` 撑满视口
（这样内容少的页面也能让侧边栏/页脚贴到浏览器窗口底部，正常浏览时体验更好）。
但截图时如果 `--window-size` 的高度设置得比页面实际内容高很多，就会在
内容和页脚之间截出一整块难看的空白——因为 flex 布局会把中间的可伸缩区域
撑满那多出来的高度。

**解决办法不是裁图，是给每个页面单独试一个合适的窗口高度**，量级大致是：
简单表单页 ~550-700px，普通列表/表格页 ~900-1100px，内容多的统计页
~950-1200px。可以先用一个偏大的高度截一次看看内容大概到哪一行结束，
再改小重截一次，两次就能定下来，比事后裁图省事也更好看。

```bash
"$CHROME" --headless --disable-gpu --window-size=1280,620 \
  --screenshot="p_result1.png" "file:///tmp/report_shots/p_result1.html"
```

## 第三步：把图片嵌进 docx 时要知道原始像素尺寸

`docx` 库的 `ImageRun` 需要显式给宽高（否则不显示或显示比例错误）。
不用额外装图片处理库，PNG 文件头里第 16-24 字节直接就是宽高（大端 32 位整数）：

```js
function readPngSize(buf) {
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}
// 显示宽度定一个页面能放下的值（比如 520px），高度按原图比例换算：
// dispHeight = Math.round(dispWidth * origHeight / origWidth)
```

`references/docx_report_toolkit.js` 里的 `figure()` 函数已经封装了这个逻辑，
直接传文件名和想要的显示宽度就行。

## 截图完成后记得清场

添加/删除类操作为了截"操作成功"的提示画面，往往需要真的往测试数据库里插
一条测试数据再截图。截完screenshot之后把这条测试数据删掉，或者干脆在测试
结束后把整个隔离 MySQL 实例连数据目录一起删掉（见
`scripts/setup_isolated_mysql.sh` 顶部注释的清理方法），确保交付的源代码和
数据库脚本本身没有被测试数据污染。
