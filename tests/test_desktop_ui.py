"""
桌面端布局测试 — 验证二区域结构与抽屉交互。
依赖：后端服务在 http://127.0.0.1:8010 运行。
用 sync_playwright 直接启动，不依赖 pytest-playwright fixture。
"""
import json
import os

import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("DECISION_BRIEF_TEST_URL", "http://127.0.0.1:8010")


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


def test_weather_settings_explain_mock_fallback(page):
    """未配置高德 API 时，要说明使用模拟数据，不能只显示“模拟数据”。"""
    config = {
        "llm": {"model": "", "baseUrl": "", "hasKey": False},
        "weather": {"city": "", "baseUrl": "", "hasKey": False, "hasBaseUrl": False},
        "hasLlm": False,
        "hasWeather": False,
    }

    def handle_config(route):
        route.fulfill(status=200, content_type="application/json", body=json.dumps(config))

    page.route("**/api/config", handle_config)
    try:
        page.goto(BASE_URL)
        page.locator(".nav-item[data-tab='settings']").click()
        page.wait_for_function(
            "document.querySelector('#weatherConfigValue')?.textContent.includes('如果没有配置高德天气 API')"
        )
        status = page.locator("#weatherConfigValue").inner_text()
        assert status == "如果没有配置高德天气 API，会使用模拟数据"
        assert status != "模拟数据"

        page.locator("#setWeatherConfig").click()
        assert page.locator("#w_key").is_visible()
        assert page.locator("#w_base_url").is_visible()
        assert page.locator("#w_city").is_visible()
        assert "没有高德 API 时会使用模拟数据" in page.locator(".weather-tip").inner_text()
    finally:
        page.unroute("**/api/config", handle_config)


def test_stats_refreshes_each_time_drawer_opens(page):
    calls = {"count": 0}

    def handle_stats(route):
        calls["count"] += 1
        total = 2 if calls["count"] == 1 else 1
        route.fulfill(
            status=200,
            content_type="application/json",
            body=(
                '{"totalDecisions":%d,"modeDistribution":{},'
                '"avgConfidence":0,"executedRate":0,"regretRate":0,"weekTrend":[]}'
            ) % total,
        )

    page.route("**/api/stats", handle_stats)
    try:
        page.goto(BASE_URL)
        page.locator(".nav-item[data-tab='stats']").click()
        page.wait_for_function(
            "document.querySelector('#statsScroll .stat b')?.textContent.trim() === '2'"
        )

        page.locator(".nav-item[data-tab='archive']").click()
        page.locator(".nav-item[data-tab='stats']").click()
        page.wait_for_function(
            "document.querySelector('#statsScroll .stat b')?.textContent.trim() === '1'"
        )
        assert calls["count"] == 2
    finally:
        page.unroute("**/api/stats", handle_stats)


def test_zdog_dice_renders_requested_result(page):
    record = {
        "id": "dice-test-5",
        "question": "骰子动画验收",
        "mode": "random",
        "result": {
            "type": "random",
            "options": ["方案一", "方案二", "方案三", "方案四", "方案五", "方案六"],
            "wheelResult": "方案四",
        },
        "brief": {
            "summary": "测试骰子最终落到第四项",
            "confidence": 58,
            "perspectives": [],
            "risks": [],
            "nextSteps": [],
        },
        "createdAt": "2026-07-26T20:00:00",
        "executed": False,
        "regret": False,
    }

    def handle_archive(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"ok": True, "list": [record], "total": 1, "page": 1, "pageSize": 20}),
        )

    def handle_detail(route):
        route.fulfill(status=200, content_type="application/json", body=json.dumps(record))

    page.route("**/api/archive*", handle_archive)
    page.route("**/api/decision/dice-test-5", handle_detail)
    try:
        page.goto(BASE_URL)
        assert page.evaluate("typeof Zdog") == "object"
        page.locator(".nav-item[data-tab='archive']").click()
        page.wait_for_selector(".archive-card[data-id='dice-test-5']")
        page.locator(".archive-card[data-id='dice-test-5']").click()
        page.wait_for_selector(".random-dice-canvas[data-ready='true']")
        page.wait_for_timeout(1600)

        stage = page.locator(".random-dice-canvas-stage")
        assert stage.get_attribute("data-result") == "4"
        painted_pixels = page.locator(".random-dice-canvas").evaluate(
            """canvas => {
                const pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
                let painted = 0;
                for (let i = 3; i < pixels.length; i += 4) {
                    if (pixels[i] > 0) painted++;
                }
                return painted;
            }"""
        )
        assert painted_pixels > 1000
    finally:
        page.unroute("**/api/archive*", handle_archive)
        page.unroute("**/api/decision/dice-test-5", handle_detail)


def test_random_effects_preview_renders_six_production_variants(page):
    page.goto(BASE_URL + "/random-effects-preview.html")
    page.wait_for_selector(".preview-effect")
    page.wait_for_selector(".random-dice-canvas[data-ready='true']")
    page.wait_for_timeout(1800)

    variants = page.locator(".preview-effect").evaluate_all(
        "nodes => nodes.map(node => node.dataset.variant)"
    )
    assert variants == ["pointer", "sticks", "dice", "cards", "tickets", "ink"]

    rendered = page.locator(".preview-effect .random-draw").evaluate_all(
        "nodes => nodes.map(node => node.className)"
    )
    assert rendered == [
        "random-draw random-draw--pointer",
        "random-draw random-draw--sticks",
        "random-draw random-draw--dice",
        "random-draw random-draw--cards",
        "random-draw random-draw--tickets",
        "random-draw random-draw--ink",
    ]

    results = page.locator(".preview-effect .random-draw-result").all_text_contents()
    assert results == [
        "这次抽到：「现在就做」",
        "这次抽到：「明天再定」",
        "这次抽到：「先问朋友」",
        "这次抽到：「换个方案」",
        "这次抽到：「暂时放下」",
        "这次抽到：「凭直觉选」",
    ]

    stage = page.locator(".random-dice-canvas-stage")
    assert stage.get_attribute("data-result") == "3"
    painted_pixels = page.locator(".random-dice-canvas").evaluate(
        """canvas => {
            const pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
            let painted = 0;
            for (let i = 3; i < pixels.length; i += 4) {
                if (pixels[i] > 0) painted++;
            }
            return painted;
        }"""
    )
    assert painted_pixels > 1000


def test_random_preview_cards_flip_one_front_and_sticks_use_palette(page):
    page.goto(BASE_URL + "/random-effects-preview.html")
    page.wait_for_selector("[data-preview-variant='cards'] .random-card-form")

    replay = page.get_by_role("button", name="重新播放六张抽卡", exact=True)
    replay.click()
    page.wait_for_timeout(620)
    picked = page.locator(
        "[data-preview-variant='cards'] .random-card-form.is-picked"
    )
    assert picked.locator(".random-card-back").evaluate(
        "node => getComputedStyle(node).opacity"
    ) == "1"
    assert picked.locator(".random-card-front").evaluate(
        "node => getComputedStyle(node).opacity"
    ) == "0"

    page.wait_for_timeout(1200)
    assert picked.locator(".random-card-back").evaluate(
        "node => getComputedStyle(node).opacity"
    ) == "0"
    assert picked.locator(".random-card-front").evaluate(
        "node => getComputedStyle(node).opacity"
    ) == "1"
    other_fronts = page.locator(
        "[data-preview-variant='cards'] .random-card-form:not(.is-picked) .random-card-front"
    ).evaluate_all("nodes => nodes.map(node => getComputedStyle(node).opacity)")
    assert other_fronts == ["0"] * 5

    stick_colors = page.locator(
        "[data-preview-variant='sticks'] .random-stick"
    ).evaluate_all("nodes => nodes.map(node => getComputedStyle(node).stroke)")
    assert len(set(stick_colors)) == 2
    assert "rgb(0, 0, 0)" not in stick_colors
    band_color = page.locator(
        "[data-preview-variant='sticks'] .random-stick-cup-band"
    ).evaluate("node => getComputedStyle(node).fill")
    assert band_color != "rgb(0, 0, 0)"

    stick_layers = page.locator(
        "[data-preview-variant='sticks'] .random-sticks-svg"
    ).evaluate(
        """svg => Array.from(svg.children).map(node => node.getAttribute('class') || '')"""
    )
    assert stick_layers.index("random-stick-rim-back") < next(
        i for i, cls in enumerate(stick_layers) if cls.startswith("random-stick ")
    )
    assert next(
        i for i, cls in enumerate(stick_layers) if cls.startswith("random-stick ")
    ) < stick_layers.index("random-stick-cup")
    assert stick_layers.index("random-stick-cup") < stick_layers.index("random-stick-rim-front")

    ticket_geometry = page.locator(
        "[data-preview-variant='tickets'] .random-tickets-svg"
    ).evaluate(
        """svg => {
            const windowRect = svg.querySelector('.random-ticket-window').getBoundingClientRect();
            return Array.from(svg.querySelectorAll('.random-ticket-row')).map(row => {
                const rect = row.getBoundingClientRect();
                const intersects = rect.bottom > windowRect.top && rect.top < windowRect.bottom;
                return {
                    intersects,
                    fullyVisible: rect.top >= windowRect.top - 1 && rect.bottom <= windowRect.bottom + 1,
                };
            });
        }"""
    )
    assert all(row["fullyVisible"] for row in ticket_geometry if row["intersects"])


def test_random_preview_switches_all_four_skins(page):
    page.goto(BASE_URL + "/random-effects-preview.html")
    for label, skin in [
        ("原来的样子", "heritage"),
        ("安静工作台", "workbench"),
        ("决策日志", "journal"),
        ("模块工作台", "console"),
    ]:
        page.get_by_role("button", name=label, exact=True).click()
        assert page.locator("html").get_attribute("data-skin") == skin
        assert page.locator(".preview-skin.is-active").get_attribute("data-skin") == skin


def test_nature_detail_shows_inputs_and_weights(page):
    record = {
        "id": "nature-reference-test",
        "question": "要不要周末出门？",
        "mode": "nature",
        "result": {
            "type": "nature",
            "signal": "雨前收束",
            "poem": "雨快到了，先把今天能收好的东西收好。",
            "suggestion": "带伞，行程留一点余量。",
            "source": "amap",
            "isReal": True,
            "city": "杭州",
            "weather": "雷阵雨",
            "temperature": "29",
            "humidity": "78",
            "wind": "东南风 3级",
            "sun": "雨幕遮日",
            "moonPhase": "下弦月",
            "updateTime": "2026-07-26 22:30:00",
            "alarms": [{"title": "雷电黄色预警"}],
            "weatherTrend": "明天 · 多云 · 31℃",
            "forecast_24h": [{"time": "明天", "weather": "多云", "temperature": "31"}],
            "signals": {"weights": [
                {"name": "真实天气", "weight": 32, "value": "雷阵雨"},
                {"name": "天气预警", "weight": 28, "value": "雷电黄色预警"},
                {"name": "月相", "weight": 6, "value": "下弦月"},
            ]},
        },
        "brief": None,
        "createdAt": "2026-07-26T22:30:00",
        "executed": False,
        "regret": False,
    }

    def handle_archive(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"ok": True, "list": [record], "total": 1, "page": 1, "pageSize": 20}),
        )

    def handle_detail(route):
        route.fulfill(status=200, content_type="application/json", body=json.dumps(record))

    page.route("**/api/archive*", handle_archive)
    page.route("**/api/decision/nature-reference-test", handle_detail)
    try:
        page.goto(BASE_URL)
        page.locator(".nav-item[data-tab='archive']").click()
        page.locator(".archive-card[data-id='nature-reference-test']").click()
        page.wait_for_selector(".nature-weights")
        assert "雷电黄色预警" in page.locator(".nature-considerations").inner_text()
        assert "下弦月" in page.locator(".nature-evidence").inner_text()
        assert page.locator(".nature-weight-row").count() == 3
        assert "明天 · 多云 · 31" in page.locator(".nature-forecast").inner_text()
    finally:
        page.unroute("**/api/archive*", handle_archive)
        page.unroute("**/api/decision/nature-reference-test", handle_detail)


def test_dialogue_choice_is_saved_to_history(page):
    saved = {}
    response = {
        "brief": {
            "summary": "先看清你最舍不得什么",
            "confidence": 58,
            "perspectives": [],
            "risks": [],
            "nextSteps": [],
        },
        "nature": None,
        "mode": "dialogue",
        "reply": "选一个最接近你真实想法的回答。",
        "result": {
            "type": "dialogue",
            "question": "如果没人评价你，你会怎么选？",
            "options": ["马上去做", "先等一周", "其实不想做"],
        },
        "autoRecognized": None,
        "decisionId": "dialogue-save-test",
    }

    def handle_chat(route):
        route.fulfill(status=200, content_type="application/json", body=json.dumps(response))

    def handle_patch(route):
        saved.update(route.request.post_data_json)
        body = {
            "id": "dialogue-save-test",
            "question": "我要不要接受邀请？",
            "mode": "dialogue",
            "result": response["result"],
            "dialogueHistory": saved.get("dialogueHistory", []),
            "executed": False,
            "regret": False,
        }
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

    page.route("**/api/chat", handle_chat)
    page.route("**/api/decision/dialogue-save-test", handle_patch)
    try:
        page.goto(BASE_URL)
        page.locator(".mode-card[data-mode='dialogue']").click()
        page.locator("#inputText").fill("我要不要接受邀请？")
        page.locator("#sendBtn").click()
        page.get_by_role("button", name="马上去做", exact=True).click()
        page.wait_for_function("() => document.querySelector('.dialogue-record') !== null")
        page.wait_for_timeout(100)
        assert saved["dialogueHistory"] == [{
            "question": "如果没人评价你，你会怎么选？",
            "answer": "马上去做",
        }]
        assert "dialogueDone" not in saved
    finally:
        page.unroute("**/api/chat", handle_chat)
        page.unroute("**/api/decision/dialogue-save-test", handle_patch)
