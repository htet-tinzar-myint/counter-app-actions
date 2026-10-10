"""dashboard の画面をヘッドレスブラウザで開き、スクリーンショットを保存する。

GitHub Actions のランナーはブラウザで直接見られないため、
画面を画像にして Artifact としてダウンロードできるようにする。

使い方:
    pip install playwright
    python -m playwright install --with-deps chromium
    python scripts/screenshot.py http://localhost:8080 dashboard.png
"""

import sys

from playwright.sync_api import sync_playwright

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: screenshot.py <dashboard base URL> <output.png>")
    url, out = sys.argv[1], sys.argv[2]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(3000)  # WebSocket でカウントが何回か届くのを待つ
        page.screenshot(path=out, full_page=True)
        browser.close()
    print(f"Saved screenshot: {out}")
