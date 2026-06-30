"""
桌面端布局测试 — 验证二区域结构与抽屉交互。
依赖：后端服务在 http://localhost:8000 运行。
用 sync_playwright 直接启动，不依赖 pytest-playwright fixture。
"""
import pytest
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def page():
    p = sync_playwright().start()
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 800})
    yield pg
    pg.close()
    b.close()
    p.stop()


def test_app_shell_two_pane_layout(page):
    """桌面端应有 .app-shell 二区域结构，无 .ios-wrapper 可见"""
    page.goto(BASE_URL)
    page.wait_for_selector(".app-shell", timeout=10000)
    assert page.locator(".app-shell").is_visible()
    # ios-wrapper 应被隐藏
    ios = page.locator(".ios-wrapper")
    if ios.count() > 0:
        assert not ios.is_visible()


def test_sidebar_visible_with_nav(page):
    """侧栏应有 4 个 nav-item：决策/档案/统计/设置"""
    page.goto(BASE_URL)
    page.wait_for_selector(".sidebar .nav-item", timeout=10000)
    navs = page.locator(".sidebar .nav-item")
    assert navs.count() == 4
    assert navs.nth(0).get_attribute("data-tab") == "chat"
    cls = navs.nth(0).get_attribute("class") or ""
    assert "active" in cls


def test_mode_grid_six_seals(page):
    """六模式印章应横排显示，data-mode 正确，且恰好有一个 active"""
    page.goto(BASE_URL)
    page.wait_for_selector(".mode-grid .mode-card", timeout=10000)
    # 等待 init 完成（applyPrefs 异步调用 setMode）
    page.wait_for_timeout(1500)
    cards = page.locator(".mode-grid .mode-card")
    assert cards.count() == 6
    expected = ["auto", "rational", "random", "nature", "dialogue", "fengshui"]
    for i, m in enumerate(expected):
        assert cards.nth(i).get_attribute("data-mode") == m
    # 恰好有一个 mode-card 是 active（取决于后端 default_mode 偏好）
    active_count = 0
    for i in range(6):
        cls = cards.nth(i).get_attribute("class") or ""
        if "active" in cls:
            active_count += 1
    assert active_count == 1


def test_click_archive_opens_drawer(page):
    """点击档案 nav-item 应打开右侧抽屉"""
    page.goto(BASE_URL)
    page.wait_for_selector(".nav-item[data-tab='archive']", timeout=10000)
    page.locator(".nav-item[data-tab='archive']").click()
    page.wait_for_timeout(300)
    cls = page.locator("#drawer").get_attribute("class") or ""
    assert "open" in cls
    cls2 = page.locator("#drawerOverlay").get_attribute("class") or ""
    assert "open" in cls2


def test_close_drawer_with_back_button(page):
    """抽屉打开后，点击返回按钮应关闭"""
    page.goto(BASE_URL)
    page.wait_for_selector(".nav-item[data-tab='archive']", timeout=10000)
    page.locator(".nav-item[data-tab='archive']").click()
    page.wait_for_timeout(300)
    page.locator("#drawerBack").click()
    page.wait_for_timeout(300)
    cls = page.locator("#drawer").get_attribute("class") or ""
    assert "open" not in cls


def test_esc_closes_drawer(page):
    """按 Esc 应关闭抽屉"""
    page.goto(BASE_URL)
    page.wait_for_selector(".nav-item[data-tab='stats']", timeout=10000)
    page.locator(".nav-item[data-tab='stats']").click()
    page.wait_for_timeout(300)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    cls = page.locator("#drawer").get_attribute("class") or ""
    assert "open" not in cls


def test_chat_main_area_visible(page):
    """主区对话流容器应可见"""
    page.goto(BASE_URL)
    page.wait_for_selector("#chatContainer", timeout=10000)
    assert page.locator("#chatContainer").is_visible()
    assert page.locator("#inputText").is_visible()
    assert page.locator("#sendBtn").is_visible()
