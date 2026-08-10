from DrissionPage import ChromiumPage, ChromiumOptions
from bs4 import BeautifulSoup
import time
import os
import sys
import datetime

# ================= jiahui配置区域 =================
TARGET_WEBSITE = "https://qwr.ezijc.com/?id=jdxv"
OUTPUT_FILE = "result_jiahui.txt"
SCROLL_RETRY_TIMES = 5       # 滚动到底后无新内容的重试次数
SCROLL_WAIT_SECONDS = 1.5    # 每次滚动后等待新内容加载的秒数
# =================================================

# 是否在 CI 环境（GitHub Actions）运行
IS_CI = os.environ.get('GITHUB_ACTIONS') == 'true' or os.environ.get('CI') == 'true'


def init_browser():
    """初始化浏览器：CI 环境用无头模式 + no-sandbox，并指定 Linux Chrome 路径"""
    co = ChromiumOptions()
    if IS_CI:
        # GitHub Actions 是无显示器 + root 环境，必须无头 + 关闭沙箱
        co.headless(True)
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--disable-gpu')
    # Linux 上指定 Chrome 路径（ubuntu-latest 自带）
    if sys.platform.startswith('linux'):
        for p in ['/usr/bin/google-chrome-stable', '/usr/bin/google-chrome',
                  '/usr/bin/chromium', '/usr/bin/chromium-browser']:
            if os.path.exists(p):
                co.set_browser_path(p)
                break
    return ChromiumPage(co)


def scroll_crawl_full_content(page):
    """
    滚动加载页面全量内容。
    :param page: 已打开目标页面的 ChromiumPage 实例
    :return: 清洗后的纯文本（不含"特殊单子"标记及之前内容）
    """
    last_page_height = 0
    current_retry_count = 0
    current_scroll_round = 0

    while True:
        current_scroll_round += 1
        print(f"[运行状态] 开始第 {current_scroll_round} 次向下滚动操作...")

        pre_scroll_height = page.run_js("return document.body.scrollHeight")
        page.scroll.to_bottom()
        time.sleep(SCROLL_WAIT_SECONDS)
        post_scroll_height = page.run_js("return document.body.scrollHeight")

        print(f"[运行状态] 滚动前页面高度：{pre_scroll_height}，滚动后页面高度：{post_scroll_height}")

        if post_scroll_height == pre_scroll_height:
            current_retry_count += 1
            print(f"[运行状态] 未检测到新内容加载，当前重试次数：{current_retry_count}/{SCROLL_RETRY_TIMES}")
            if current_retry_count >= SCROLL_RETRY_TIMES:
                print(f"[运行状态] 已达到配置的最大滚动重试次数 {SCROLL_RETRY_TIMES}，所有滚动加载内容抓取完成")
                break
            time.sleep(1)
        else:
            current_retry_count = 0
            last_page_height = post_scroll_height

    print("[运行状态] 开始解析全量页面内容...")
    full_page_html = page.html
    soup = BeautifulSoup(full_page_html, "html.parser")
    raw_text = soup.get_text(separator="\n", strip=True)

    # 业务清洗：从全部文本开头到"特殊单子"字样的文字全部删除，同时删除"特殊单子"本身
    marker = "特殊单子"
    if marker in raw_text:
        split_index = raw_text.find(marker)
        cleaned_content = raw_text[split_index + len(marker):]
        print("[运行状态] 已完成文本清洗：删除开头至'特殊单子'的全部内容，包含该标记本身")
    else:
        cleaned_content = raw_text
        print("[运行警告] 未在文本中找到'特殊单子'标记，未执行截断操作")

    # 清理多余空行
    lines = [line.strip() for line in cleaned_content.splitlines() if line.strip()]
    return "\n".join(lines)


def save_to_local_file(content):
    """保存文本到脚本所在目录，CI 失败返回 False 让主流程非0退出"""
    save_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(save_dir, OUTPUT_FILE)
    if not content or len(content) < 20:
        print(f"⚠️ 警告: 未获取到有效内容（长度 {len(content or '')}），文件未生成")
        return False
    # 修复 PermissionError：写入重试 + 备用文件名
    max_write_retry = 3
    actual_save_name = full_path
    for retry in range(max_write_retry):
        try:
            with open(actual_save_name, "w", encoding="utf-8") as f:
                f.write(content)
            file_size = os.path.getsize(actual_save_name)
            print(f"🎉 成功! 文件已保存至: {actual_save_name}")
            print(f"   文件大小: {file_size} bytes，抓取总文字长度：{len(content)} 字符")
            return True
        except PermissionError:
            if retry < max_write_retry - 1:
                print(f"[运行提示] 文件被占用，第{retry + 1}次重试写入...")
                time.sleep(2)
            else:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file_name = os.path.join(save_dir, f"result_jiahui_{timestamp}.txt")
                with open(backup_file_name, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"[运行提示] 原文件权限不足，已自动保存为备用文件：{backup_file_name}")
                return True
        except Exception as e:
            print(f"❌ 文件保存失败: {e}")
            return False
    return False


def start_crawl():
    """主流程：初始化浏览器 → 加载目标站 → 滚动抓取 → 清洗 → 保存"""
    print("🚀 启动浏览器，准备开始抓取 jiahui...")
    page = init_browser()
    try:
        print(f"[运行状态] 正在加载目标站点：{TARGET_WEBSITE}")
        page.get(TARGET_WEBSITE)
        time.sleep(2)

        final_text = scroll_crawl_full_content(page)
        ok = save_to_local_file(final_text)
        return ok, final_text
    except Exception as err:
        print(f"[运行错误] 程序执行出现异常: {err}")
        import traceback
        traceback.print_exc()
        return False, ""
    finally:
        print("[运行状态] 正在自动关闭浏览器，释放系统资源...")
        try:
            page.quit()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        ok, final_result = start_crawl()
        # 【关键】CI 环境抓取失败时应以非0退出码终止，让 workflow 失败而非静默推送空文件
        if IS_CI:
            if not ok or not final_result:
                print("❌ CI 环境：抓取无内容，以非0状态退出")
                sys.exit(1)
    except Exception as e:
        print(f"主程序错误: {e}")
        if IS_CI:
            sys.exit(1)
    finally:
        # 【关键修改】仅在本地交互环境等待回车；CI 环境直接退出，否则会卡死
        if not IS_CI:
            try:
                input("\n[程序结束] 请按回车键关闭窗口...")
            except EOFError:
                pass
