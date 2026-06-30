"""八字降级校验引擎。

移植自 HTML 版本的 BaziEngine（行 3379-3440）。
前端只做信息完整性校验、年柱推算和时辰识别；完整四柱、大运流年、十神格局
需接入 bazi-skill 或万年历排盘，本模块不做超越此边界的推断。

API：
  parse(text)        -> {year, month, day, gender, place, hour, calendar, missing}
  year_pillar(y,m,d) -> 年柱字符串（如 '庚午年'）
  analyze(text)      -> {complete, info, missing?/pillars?, wuxing?, element?, audit?}
"""

import re
from typing import Any, Dict, List, Optional

# 10 天干
STEMS: List[str] = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

# 12 地支
BRANCHES: List[str] = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 12 时辰：branch / 时间区间 / 触发关键词
HOUR_BRANCHES: List[Dict[str, Any]] = [
    {"branch": "子", "range": "23:00-01:00", "keys": ["子时", "半夜", "深夜"]},
    {"branch": "丑", "range": "01:00-03:00", "keys": ["丑时", "凌晨"]},
    {"branch": "寅", "range": "03:00-05:00", "keys": ["寅时", "平旦", "黎明"]},
    {"branch": "卯", "range": "05:00-07:00", "keys": ["卯时", "清晨", "日出"]},
    {"branch": "辰", "range": "07:00-09:00", "keys": ["辰时", "早上", "早晨"]},
    {"branch": "巳", "range": "09:00-11:00", "keys": ["巳时", "上午", "早间"]},
    {"branch": "午", "range": "11:00-13:00", "keys": ["午时", "中午", "正午"]},
    {"branch": "未", "range": "13:00-15:00", "keys": ["未时", "午后", "下午"]},
    {"branch": "申", "range": "15:00-17:00", "keys": ["申时", "傍晚", "夕时"]},
    {"branch": "酉", "range": "17:00-19:00", "keys": ["酉时", "日落", "黄昏"]},
    {"branch": "戌", "range": "19:00-21:00", "keys": ["戌时", "夜晚", "晚上"]},
    {"branch": "亥", "range": "21:00-23:00", "keys": ["亥时", "夜深", "入夜"]},
]

# 地支五行：子亥=水，寅卯=木，巳午=火，申酉=金，辰戌丑未=土
BRANCH_WUXING: Dict[str, str] = {
    "子": "水", "亥": "水",
    "寅": "木", "卯": "木",
    "巳": "火", "午": "火",
    "申": "金", "酉": "金",
    "辰": "土", "戌": "土", "丑": "土", "未": "土",
}

# 天干五行：甲乙=木，丙丁=火，戊己=土，庚辛=金，壬癸=水
STEM_WUXING: Dict[str, str] = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}

# 正则：完整生日（年-月-日），分隔符支持 年/月/日 或 - / . 三种
_BIRTHDAY_RE = re.compile(
    r"(19\d{2}|20\d{2})\s*(?:年|[-/.])\s*(\d{1,2})\s*(?:月|[-/.])\s*(\d{1,2})\s*(?:日|号)?"
)
# 仅年份兜底
_YEAR_ONLY_RE = re.compile(r"(19\d{2}|20\d{2})")
# 性别：要求前后是空白或字符串边界，避免误匹配
_GENDER_MALE_RE = re.compile(r"(^|\s)(男|男性|男生|男命)(\s|$)")
_GENDER_FEMALE_RE = re.compile(r"(^|\s)(女|女性|女生|女命)(\s|$)")
# 出生地：前缀词 + 2-12 个汉字（可选省/市/县/区后缀）
_PLACE_RE = re.compile(r"(?:出生地|出生于|生于|在)\s*([\u4e00-\u9fa5]{2,12}(?:省|市|县|区)?)")
# 出生地兜底：2-8 个汉字 + 省/市/县/区
_PLACE_FALLBACK_RE = re.compile(r"[\u4e00-\u9fa5]{2,8}(?:省|市|县|区)")
# 中文标点转空格（与 JS 版本一致）
_PUNCT_RE = re.compile(r"[，。；、]")


def parse(text: str) -> Dict[str, Any]:
    """从自然语言文本中提取八字所需的出生信息。

    返回字段：
      year/month/day: int 或 None
      gender: '男' / '女' / ''
      place: str（可能为空）
      hour: 命中的时辰 dict 或 None
      calendar: '农历' / '阳历' / ''
      missing: 缺失字段名列表（用于补全提示）
    """
    q = _PUNCT_RE.sub(" ", str(text or ""))

    birthday = _BIRTHDAY_RE.search(q)
    year = None
    month = None
    day = None
    if birthday:
        year = int(birthday.group(1))
        month = int(birthday.group(2))
        day = int(birthday.group(3))
    else:
        year_only = _YEAR_ONLY_RE.search(q)
        if year_only:
            year = int(year_only.group(1))

    if _GENDER_MALE_RE.search(q):
        gender = "男"
    elif _GENDER_FEMALE_RE.search(q):
        gender = "女"
    else:
        gender = ""

    place_match = _PLACE_RE.search(q)
    place = place_match.group(1) if place_match else ""
    if not place:
        # 兜底：找最后一个 "X省/X市/X县/X区" 形态
        all_places = _PLACE_FALLBACK_RE.findall(q)
        if all_places:
            place = all_places[-1]

    hour = next(
        (h for h in HOUR_BRANCHES if any(k in q for k in h["keys"])),
        None,
    )

    if "农历" in q or "阴历" in q:
        calendar = "农历"
    elif "阳历" in q or "公历" in q:
        calendar = "阳历"
    else:
        calendar = ""

    missing: List[str] = []
    if not birthday:
        missing.append("阳历或农历生日")
    if not hour:
        missing.append("出生时辰")
    if not gender:
        missing.append("性别")
    if not place:
        missing.append("出生地")

    return {
        "year": year,
        "month": month,
        "day": day,
        "gender": gender,
        "place": place,
        "hour": hour,
        "calendar": calendar,
        "missing": missing,
    }


def year_pillar(year: Optional[int], month: Optional[int], day: Optional[int]) -> str:
    """计算年柱（天干+地支+年）。

    立春前（month<2 或 month==2 且 day<4）按上一年计算。
    year 为 None 时返回占位符 '未知年柱'。
    """
    if not year:
        return "未知年柱"
    adjusted_year = year
    if month is not None and day is not None and (month < 2 or (month == 2 and day < 4)):
        adjusted_year = year - 1
    stem_idx = ((adjusted_year - 4) % 10 + 10) % 10
    branch_idx = ((adjusted_year - 4) % 12 + 12) % 12
    return STEMS[stem_idx] + BRANCHES[branch_idx] + "年"


def analyze(text: str) -> Dict[str, Any]:
    """完整八字分析入口。

    缺字段 → {complete: false, info, missing}
    完整   → {complete: true, info, pillars, wuxing, element, audit}

    本模块只完成信息校验 + 年柱 + 时辰；完整四柱/大运/十神需 bazi-skill 接入。
    """
    info = parse(text)
    if info["missing"]:
        return {"complete": False, "info": info, "missing": info["missing"]}

    yp = year_pillar(info["year"], info["month"], info["day"])
    # year_pillar 形如 "庚午年"，去掉"年"后取第 2 个字符即地支
    branch = yp.replace("年", "")[1]
    base_element = BRANCH_WUXING.get(branch, "土")
    hour_branch = info["hour"]["branch"]
    hour_range = info["hour"]["range"]

    return {
        "complete": True,
        "info": info,
        "pillars": {
            "year": yp,
            "month": "需节气万年历确认",
            "day": "需万年历日柱确认",
            "hour": f"{hour_branch}时（{hour_range}，天干需日柱推定）",
        },
        "wuxing": (
            f"年支属{base_element}，时支为{hour_branch}。"
            f"完整五行强弱需月令、日主、藏干和十神共同判断。"
        ),
        "element": f"初步参考{base_element}气，不作为完整喜用神结论",
        "audit": (
            "前端已完成信息完整性校验、年柱和时辰识别；"
            "完整四柱、大运流年、十神格局需接入 bazi-skill 或万年历排盘。"
        ),
    }


if __name__ == "__main__":
    # 自测 1：完整信息（1990 庚午年）
    text1 = "男命 1990年6月15日 出生于北京 农历 午时"
    r1 = analyze(text1)
    print("case1（完整）:", r1)
    assert r1["complete"] is True
    assert r1["info"]["gender"] == "男"
    assert r1["info"]["year"] == 1990
    assert r1["info"]["month"] == 6
    assert r1["info"]["day"] == 15
    assert r1["info"]["place"] == "北京"
    assert r1["info"]["calendar"] == "农历"
    assert r1["info"]["hour"]["branch"] == "午"
    assert r1["pillars"]["year"] == "庚午年", f"年柱应为 庚午年，实际 {r1['pillars']['year']}"
    assert r1["pillars"]["hour"] == "午时（11:00-13:00，天干需日柱推定）"
    assert "年支属火" in r1["wuxing"]
    assert "bazi-skill" in r1["audit"]

    # 自测 2：立春前按上一年（1990年1月15日 → 1989 己巳年）
    text2 = "男命 1990年1月15日 出生于上海 阳历 子时"
    r2 = analyze(text2)
    print("case2（立春前）:", r2["pillars"]["year"])
    assert r2["pillars"]["year"] == "己巳年", f"立春前应为 己巳年，实际 {r2['pillars']['year']}"

    # 自测 3：立春当天按本年（1990年2月4日 → 庚午年）
    text3 = "男命 1990年2月4日 出生于广州 阳历 午时"
    r3 = analyze(text3)
    print("case3（立春当天）:", r3["pillars"]["year"])
    assert r3["pillars"]["year"] == "庚午年"

    # 自测 4：缺字段
    text4 = "你好"
    r4 = analyze(text4)
    print("case4（缺字段）:", r4)
    assert r4["complete"] is False
    assert "阳历或农历生日" in r4["missing"]
    assert "出生时辰" in r4["missing"]
    assert "性别" in r4["missing"]
    assert "出生地" in r4["missing"]

    # 自测 5：year_pillar 直接调用
    assert year_pillar(None, None, None) == "未知年柱"
    assert year_pillar(1984, 6, 15) == "甲子年"  # 1984 甲子年
    assert year_pillar(2024, 6, 15) == "甲辰年"  # 2024 甲辰年

    # 自测 6：阴历关键词 + 女命 + 时辰关键词"中午"
    text6 = "女 1995年8月8日 生于成都 阴历 中午"
    r6 = analyze(text6)
    print("case6（阴历/女/中午）:", r6["info"]["gender"], r6["info"]["calendar"], r6["info"]["hour"]["branch"])
    assert r6["info"]["gender"] == "女"
    assert r6["info"]["calendar"] == "农历"
    assert r6["info"]["hour"]["branch"] == "午"  # "中午" 命中午时

    print("\n全部通过")
