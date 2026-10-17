"""把網頁版包成可以獨立開啟的完整 HTML，給 GitHub Pages 用。

web/index.html 是 Claude 網頁（Artifact）的原始檔，外層的 doctype、viewport 等由 Claude 自動補上；
GitHub Pages 需要完整的頁面，所以這裡補上外層後輸出到 werewolf/play/index.html。

在 repo 根目錄執行：python3 werewolf/web/build_pages.py
"""
import pathlib

src = pathlib.Path(__file__).with_name("index.html")
out = pathlib.Path(__file__).resolve().parents[1] / "play" / "index.html"

html = src.read_text(encoding="utf-8")
split = html.index('<div class="wrap">')
head, body = html[:split].strip(), html[split:].strip()

page = f"""<!doctype html>
<!-- 由 werewolf/web/build_pages.py 從 werewolf/web/index.html 產生，請改原始檔後重新產生 -->
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<style>
:root {{ padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }}
body {{ margin: 0; font: 14px system-ui, sans-serif; }}
img {{ max-width: 100%; }}
[hidden] {{ display: none !important; }}
</style>
{head}
</head>
<body>
{body}
</body>
</html>
"""
out.parent.mkdir(exist_ok=True)
out.write_text(page, encoding="utf-8")
print(f"已產生 {out.relative_to(out.parents[2])}")
