# WampServer / SQLyog 远程排障手册

用户在自己的 Windows 电脑上操作，你看不到屏幕、进不去终端，只能靠用户贴的截图和报错文字来判断。
这里整理的是已经实际遇到过、按图索骥能快速定位的几条故障链。诊断思路是**层层剥洋葱**：
先确认服务起没起来，再确认扩展/配置文件对不对，最后才是代码和数据库内容本身的问题——
不要一上来就怀疑代码写错了。

## 故障链 1：SQLyog / 网页报 "2003 Can't connect to MySQL server on 'localhost'"

这个错误只说明"连不上"，本身不指向具体原因，按下面顺序排查：

1. **先看 WampServer 托盘图标颜色**。不是纯绿色，说明 Apache/MySQL 至少有一个没启动，后面几步都不用做了，先解决图标不绿的问题。
2. **图标绿了还连不上**：去 `wamp\logs\` 目录下找 `mysqlxxxx.err`（有的版本叫 `mysql.log`），看最后几十行的真实报错，比瞎猜快得多。
3. **常见次生原因**：
   - 端口 3306 被别的 MySQL/程序占用了（`netstat -ano | findstr :3306` 能看到）
   - 装了多个 PHP/MySQL 版本，当前激活的版本跟预期的不是同一个
   - 刚编辑过 `my.ini` 引入了语法错误或指向了不存在的路径（比如改 `lc-messages` 却没有对应的语言文件夹）

## 故障链 2：WampServer 主日志里全是 symlink / chmod Permission denied

```
Impossible to modify the file C:\WINDOWS\system32\drivers\etc\hosts to be writable
symlink(): Cannot create symlink, error code(1314)
```

**错误代码 1314 = ERROR_PRIVILEGE_NOT_HELD，几乎总是"WampServer 没有用管理员权限运行"。**
修改 hosts 文件、创建版本切换用的符号链接都需要管理员权限。

修复：完全退出 WampServer（托盘图标 → Exit，不是关窗口） → 找到启动图标/exe 右键"以管理员身份运行"。
一劳永逸：右键快捷方式 → 属性 → 兼容性 → 勾选"以管理员身份运行此程序"。

这个问题解决后，之前连带出现的 MySQL 连不上等问题往往也会一起消失，因为版本切换用的符号链接
没建成功可能导致服务压根没指向正确的可执行文件。

## 故障链 3：`Call to undefined function mysqli_report()` / `mysqli_xxx()`

先看 WampServer 托盘菜单 **PHP → PHP extensions** 里 `php_mysqli` 是否已经打勾。

- **如果没打勾**：勾上，然后**必须手动点一次 "Restart All Services"**，光打勾不重启不会生效。
- **如果已经打勾但还是报错**：说明勾选状态和实际生效的配置对不上，几乎总是因为 **Apache 实际加载的
  `php.ini` 是空文件或损坏**。这个文件不是 PHP 安装目录里那份，而是：
  ```
  C:\wamp\bin\apache\apache<版本号>\bin\php.ini
  ```
  用 WampServer 托盘菜单里的 **php.ini** 菜单项直接打开它（比自己找路径快），如果打开是全空白、
  编辑器状态栏显示"0个字符"，那就是真的是空文件——**这就是根因**，跟代码没关系。

  修复：去 `C:\wamp\bin\php\php<版本号>\` 目录下找 `phpForApache.ini`（WampServer 的标准模板文件，
  正常应该有完整内容），把它的内容整个复制粘贴进那个空的 `php.ini`，保存，重启所有服务。
  如果这个模板文件也找不到或者也是空的，说明这次 WampServer 安装本身不完整，直接重装最快
  （重装前先备份 `wamp\bin\mysql\mysql<版本>\data\<数据库名>\` 目录，重装后把 SQL 脚本重新跑一遍
  比试图恢复备份更省事可靠，因为重装通常会重置数据目录）。

  确认扩展是否真的加载了，最直接的办法是让用户建一个 `phpinfo.php`（内容 `<?php phpinfo(); ?>`）
  访问后 Ctrl+F 搜 "mysqli"，搜得到才算数，菜单打勾只代表"配置文件应该写了这一行"，不代表"Apache
  真的读到了这一行"。

## 故障链 4：`mysqli_stmt_bind_param() expects parameter 1 to be mysqli_stmt, boolean given`
（以及后面跟着一串 `mysqli_stmt_execute`/`get_result`/`num_rows` 的同类警告）

这一串警告的根源都是同一个：**`mysqli_prepare($conn, $sql)` 返回了 `false`**，因为项目里
`mysqli_report(MYSQLI_REPORT_OFF)` 关掉了异常，prepare 失败会静默返回 false 而不是报错，
false 一路传给后面的函数就变成这一串"expects mysqli_stmt/mysqli_result, boolean/null given"。

`mysqli_prepare` 失败通常不是语法问题（除非刚改过 SQL），而是**当前连接实际操作的数据库里，
SQL 里引用的表根本不存在**。按这个顺序查：

1. 确认 `$conn` 本身连接成功（如果 conn.php 里 `mysqli_connect(...) or die(...)` 都没触发
   die，说明连接对象是有效的，问题在后面）
2. **重点检查 `conn.php` 里连的数据库名，是不是这个项目该连的那个库**。如果用户机器上
   `www` 目录下同时放着好几个课程项目，各自都有一份 `conn.php`，**很容易在复制粘贴/切换文件时
   把 A 项目的 conn.php 内容误粘到了 B 项目里**（连接了错误的数据库名），导致 SQL 语句里的
   表在"实际连上的那个库"里根本不存在。判断线索：如果页面上出现了一句不属于这个项目代码的
   提示文字（比如另一个项目专属的"数据库连接成功"字样），基本可以确定是文件内容被张冠李戴了——
   直接让用户打开那个 conn.php 文件把内容发你看一眼，比猜测更快。
3. 排除文件混淆之后，再去 SQLyog 里确认对应的库和表是不是真的建好了（见故障链5）。

## 故障链 5：SQLyog 报 "Table 'A.xxx' doesn't exist"，但 A 根本不是这个表该在的库

**SQLyog 的查询窗口有一个"当前活动数据库"的概念**，没写库名前缀的 `INSERT INTO xxx` 之类语句
都是对着这个当前库执行的。如果脚本里最前面的 `USE 目标库名;` 这条语句没有被真正执行到
（常见于用户只选中了脚本的一部分文字执行、或者分好几次执行漏掉了这一句），后面的建表/插入语句
就会全部跑到之前残留的那个"当前库"里去，报错信息里的库名会暴露这一点
（比如明明是要建到 `lqxx` 库，报错却说 `php.xxx doesn't exist`）。

修复：**把整个 .sql 文件内容一次性粘贴进一个干净的查询窗口，执行"全部脚本"**（SQLyog 工具栏
上找"Execute all"或类似字样的按钮/图标，跟只执行光标所在一条语句的普通"执行"按钮是分开的），
确保 `CREATE DATABASE` / `USE` 这些语句真的先跑了。执行完看信息面板的统计，"N queries executed,
N success, 0 errors" 说明全部成功；如果数量对不上，说明中途有语句失败或被跳过，展开看具体哪一条。

## 故障链 6：插入数据报 "Duplicate entry 'xxx' for key 'PRIMARY'"

这通常不是代码 bug（主键约束正常工作，说明防重复插入的机制没问题），而是**用户填错了要插入的
对象**。常见场景：任务要求"添加另一个人（比如班长）的数据"，用户下意识地又填了一遍自己的信息，
而自己的记录在更早的步骤里已经插入过了。看到这个报错先确认："这一步是不是本来就该填一个
和之前不一样的人的信息"，而不是急着去改代码里的主键约束或去重逻辑。
