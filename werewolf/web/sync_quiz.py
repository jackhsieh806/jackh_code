"""把 werewolf/guide.py 的測驗題同步到網頁版 index.html。

在 repo 根目錄執行：python3 werewolf/web/sync_quiz.py
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from werewolf.guide import QUIZ_TOPICS  # noqa: E402

page = pathlib.Path(__file__).with_name("index.html")
html = page.read_text(encoding="utf-8")
topics = [{"name": name, "qs": [list(q) for q in qs]}
          for key, (name, qs) in QUIZ_TOPICS.items() if key != "1"]
new = "const QUIZ_TOPICS = " + json.dumps(topics, ensure_ascii=False, indent=0) + ";"
html, n = re.subn(r"const QUIZ_TOPICS = \[.*?\];", lambda _: new, html, count=1, flags=re.S)
if n != 1:
    sys.exit("找不到 QUIZ_TOPICS 區塊")
page.write_text(html, encoding="utf-8")
print(f"已同步 {sum(len(t['qs']) for t in topics)} 題")
