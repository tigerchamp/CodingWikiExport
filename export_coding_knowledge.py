import argparse, os, re, time
from playwright.sync_api import sync_playwright

# 运行脚本前先将项目文档目录设置为“全部收起”

parser = argparse.ArgumentParser(description="批量导出 CODING Wiki 为 Markdown")
parser.add_argument('-u', '--start_url', required=True,
                    help='CODING 知识库首页地址，例如 https://xxx.coding.net/p/pj/km/spaces/123')
parser.add_argument('-s', '--skip', type=int, default=0,
                    help='跳过前 N 篇，从第 N+1 篇开始（从 1 开始计数）')
args = parser.parse_args()

start_url   = args.start_url
skip_count  = args.skip          # 0 表示不跳过

download_path = "./coding_wiki_md"

os.makedirs(download_path, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir="./user_data",  # 复用已有登录态，首次手动登录一次即可
        headless=False,               # 调试用 True 可改成无头
        accept_downloads=True
    )
    page = browser.new_page()
    page.goto(start_url)

    # 1. 等目录树渲染出来
    page.wait_for_selector('[class*="page-tree-"]', timeout=30_000)

    # 2. 如果目录很长，先滚动到底触发懒加载
    tree = page.locator('[class*="page-tree-"]')
    if tree.count():
        tree.first.evaluate("el => el.scrollIntoView(false)")   # 先滚到可见
        for _ in range(5):                                    # 最多滚 5 次
            page.keyboard.press("End")
            page.wait_for_timeout(500)

    # 3. 抓取所有文章链接（绝对路径）
    links = page.eval_on_selector_all(
        'a[class*="page-tree-link-"][href*="/pages/"]',
        '''(as) => as.map(a => {
            const href = a.getAttribute('href');
            // 处理相对路径
            return href.startsWith('http') ? href : location.origin + href;
        })'''
    )
    print(f"共发现 {len(links)} 篇文章")

    # 4. 逐个访问并导出 Markdown
    for idx, url in enumerate(links, 1):

        if idx <= skip_count:
            print(f"跳过 [{idx}/{len(links)}] {url}")
            continue

        print(f"下载 [{idx}/{len(links)}] {url}")       
        page.goto(url)
        page.wait_for_load_state("networkidle")

        # 点击「更多」按钮 → 导出为 Markdown
        more = page.locator('button[class*="more-button-"]').first
        more.click()

        # 1. 先等菜单弹出来
        page.wait_for_selector('.dropdown-3W57O0rrHW', timeout=15_000)

        # 2. 再点击“导出为 Markdown”
        export_btn = page.locator('.dropdown-3W57O0rrHW >> text="导出为 Markdown"')
        export_btn.wait_for(state='visible', timeout=10_000)
        export_btn.click(force=True)

        # 等待对话框出现
        page.wait_for_selector('.t-dialog', timeout=10_000)

        # 最多等 5 秒，如果"包含子文档"开关出现就点击
        switch = page.locator('button[role="switch"].cuk-switch')
        try:
            switch.wait_for(state='visible', timeout=5000)
            if switch.get_attribute('aria-checked') != 'true':
                switch.click()
        except:
            pass  # 没出现就跳过

         # 2. 等待确认对话框并点击“确认导出”
        page.wait_for_selector('.t-dialog >> text=确认导出', timeout=15_000)
        page.locator('.t-dialog >> text=确认导出').click()

         # 2. 等待确认对话框并点击“下载文件”
        page.wait_for_selector('.t-dialog >> text=下载文件', timeout=60_000)
        
         # 等待下载
        with page.expect_download(timeout=60_000) as dl_info:
            page.locator('.t-dialog >> text=下载文件').click()
        dl = dl_info.value

        # 提取项目名
        proj = page.locator('.project-button-fXc5E5CTk8 span').inner_text()
        # 提取页面标题
        title = page.locator('title').inner_text().split(" - ", 1)[0]

        safe_proj = re.sub(r'[\\/:*?"<>|]', '_', proj).strip()
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title).strip()

        file_name = f"{safe_title}.zip"

        dl.save_as(os.path.join(f"{download_path}/{safe_proj}/know", file_name))
        

        time.sleep(1.5)  # 礼貌限速

    browser.close()