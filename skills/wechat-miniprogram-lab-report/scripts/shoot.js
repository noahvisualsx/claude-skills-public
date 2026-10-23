#!/usr/bin/env node
/**
 * 用 miniprogram-automator 驱动微信开发者工具，按"计划"逐步操作并截取模拟器截图。
 * 用法: node shoot.js plan.json
 *
 * plan.json 示例:
 * {
 *   "project": "/abs/path/to/miniprogram",
 *   "outDir": "/abs/path/to/shots",
 *   "clearStorage": true,
 *   "steps": [
 *     {"reLaunch": "/pages/index/index", "shot": "4-首页.png"},
 *     {"tap": ".btn", "wait": 800, "shot": "5-点击跳转后.png"},
 *     {"input": ["input", "新的一项"], "confirm": "input", "shot": "4-输入后.png"},
 *     {"switchTab": "/pages/logs/logs", "shot": "3-日志页.png"},
 *     {"navigateTo": "/pages/route/route"}, {"navigateBack": true},
 *     {"pullDown": true, "shot": "2-下拉刷新.png"},
 *     {"setData": {"list": []}}, {"callMethod": ["onConfirm", {"detail": {"value": "x"}}]},
 *     {"evaluate": "wx.setStorageSync('k', 1)"}
 *   ]
 * }
 * 每一步可同时带 wait(ms，默认 600) 和 shot(文件名)。动作按上面顺序执行。
 * 首页建议 wait 3000（图片加载慢）。截完自动调用 clean_shot.py 去掉圆角外残影。
 * 启动前会先 `cli quit` 关掉已打开的开发者工具（否则常报 timeout waiting for automator response），
 * 失败会自动重试一次（首次偶发 getPageMetaByWebviewId ... null）。
 */
const path = require('path');
const fs = require('fs');
const automator = require('miniprogram-automator');

const CLI = process.env.WX_CLI || '/Applications/wechatwebdevtools.app/Contents/MacOS/cli';
const { execSync } = require('child_process');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const quitIDE = () => { try { execSync(`"${CLI}" quit`, { stdio: 'ignore', timeout: 60000 }); } catch (e) {} };

async function run(plan) {
  quitIDE();
  await sleep(6000);
  const mp = await automator.launch({ cliPath: CLI, projectPath: plan.project, timeout: 120000 });
  try {
    if (plan.clearStorage) await mp.evaluate(() => wx.clearStorageSync());
    for (const [i, s] of plan.steps.entries()) {
      let page = await mp.currentPage();
      if (s.reLaunch) page = await mp.reLaunch(s.reLaunch);
      if (s.navigateTo) page = await mp.navigateTo(s.navigateTo);
      if (s.redirectTo) page = await mp.redirectTo(s.redirectTo);
      if (s.switchTab) page = await mp.switchTab(s.switchTab);
      if (s.navigateBack) page = await mp.navigateBack();
      // 发生过跳转时，等页面栈稳定后重新获取当前页，否则 callMethod/$ 会落到旧页面
      if (s.reLaunch || s.navigateTo || s.redirectTo || s.switchTab || s.navigateBack) {
        await sleep(500);
        page = await mp.currentPage();
      }
      if (s.evaluate) await mp.evaluate(new Function(s.evaluate));
      if (s.setData) await page.setData(s.setData);
      if (s.callMethod) await page.callMethod(...s.callMethod);
      if (s.input) {
        const el = await page.$(s.input[0]);
        await el.input(s.input[1]);
      }
      if (s.confirm) {
        const el = await page.$(s.confirm);
        await el.trigger('confirm', { value: s.confirmValue ?? '' });
      }
      if (s.tap) {
        const el = await page.$(s.tap);
        if (!el) throw new Error(`step ${i}: 找不到元素 ${s.tap}`);
        await el.tap();
      }
      if (s.trigger) {
        // {"trigger": [选择器, 事件名, detail对象]} 例如 [".item", "longpress", {}]
        const el = await page.$(s.trigger[0]);
        if (!el) throw new Error(`step ${i}: 找不到元素 ${s.trigger[0]}`);
        await el.trigger(s.trigger[1], s.trigger[2] || {});
      }
      if (s.pullDown) await mp.callWxMethod('startPullDownRefresh');
      await sleep(s.wait ?? 600);
      if (s.shot) {
        const file = path.join(plan.outDir, s.shot);
        await mp.screenshot({ path: file });
        try { execSync(`python3 "${path.join(__dirname, 'clean_shot.py')}" "${file}"`); } catch (e) {}
        console.log('截图:', file);
      }
    }
  } finally {
    await mp.close();
  }
}

(async () => {
  const plan = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  fs.mkdirSync(plan.outDir, { recursive: true });
  try {
    await run(plan);
  } catch (e) {
    console.error('第一次失败，重试:', e.message || e);
    await run(plan);
  }
})().catch(e => { console.error('失败:', e.message || e); process.exit(1); });
