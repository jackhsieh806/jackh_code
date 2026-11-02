"""把 Python 版的測驗題和電腦個性同步到網頁版 index.html。

測驗題以 werewolf/guide.py 為準，電腦個性以 werewolf/personality.py 為準。
在 repo 根目錄執行：python3 werewolf/web/sync_quiz.py
"""
import dataclasses
import json
import math
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from werewolf.guide import QUIZ_TOPICS  # noqa: E402
from werewolf.personality import PERSONALITIES  # noqa: E402

page = pathlib.Path(__file__).with_name("index.html")
html = page.read_text(encoding="utf-8")


def replace(pattern: str, new: str) -> None:
    global html
    html, n = re.subn(pattern, lambda _: new, html, count=1, flags=re.S)
    if n != 1:
        sys.exit(f"找不到要替換的區塊：{pattern}")


def camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(w.title() for w in rest)


def js_number(v):
    """JSON 沒有無限大，用很大的數字代替（門檻永遠達不到）。"""
    if isinstance(v, float) and math.isinf(v):
        return 1e9 if v > 0 else -1e9
    return v


topics = [{"name": name, "qs": [list(q) for q in qs]}
          for key, (name, qs) in QUIZ_TOPICS.items() if key != "1"]
replace(r"const QUIZ_TOPICS = \[.*?\];",
        "const QUIZ_TOPICS = " + json.dumps(topics, ensure_ascii=False, indent=0) + ";")

personas = {p.key: {camel(k): js_number(v) for k, v in dataclasses.asdict(p).items()}
            for p in PERSONALITIES.values()}
replace(r"const PERSONALITIES = \{.*?\};\n",
        "const PERSONALITIES = " + json.dumps(personas, ensure_ascii=False) + ";\n")

page.write_text(html, encoding="utf-8")
print(f"已同步 {sum(len(t['qs']) for t in topics)} 題、{len(personas)} 種電腦個性")
