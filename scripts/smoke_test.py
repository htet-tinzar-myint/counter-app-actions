"""dashboard-service のスモークテスト。

1. /health が 200 を返すこと
2. WebSocket（socket.io）で接続し、counting-service から取得した "count" が届くこと
   → dashboard → counting の通信まで含めて動いていることを確認できる

使い方:
    pip install websocket-client
    python scripts/smoke_test.py http://localhost:8080
    python scripts/smoke_test.py https://dashboard-service-xxxx.a.run.app
"""

import json
import os
import sys
import time
import urllib.request

import websocket


def wait_for_health(base_url: str, timeout_sec: int = 60) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=5) as res:
                if res.status == 200:
                    print("OK  /health -> 200")
                    return
        except Exception as e:  # 起動待ちの間はエラーを無視して再試行
            print(f"... waiting for /health ({e})")
        time.sleep(2)
    raise SystemExit("NG  /health did not return 200")


def wait_for_count(base_url: str, timeout_sec: int = 30) -> dict:
    ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
    ws_url += "/socket.io/?EIO=3&transport=websocket"
    try:
        ws = websocket.create_connection(ws_url, timeout=10)
    except Exception as e:
        raise SystemExit(f"NG  cannot open WebSocket {ws_url}: {e}")
    try:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                msg = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue  # 受信待ちのタイムアウトは deadline まで再試行
            except websocket.WebSocketConnectionClosedException:
                raise SystemExit("NG  WebSocket closed by dashboard before count was received")
            # socket.io のイベントは 42<ack id>["message", {...}] の形式で届く
            if not msg.startswith("42") or "[" not in msg:
                continue
            event, payload = json.loads(msg[msg.index("["):])
            if event != "message" or "count" not in payload:
                continue
            # counting-service に届かないと count = -1、hostname = "[Unreachable]" になる
            if payload["count"] < 0:
                raise SystemExit(f"NG  dashboard cannot reach counting-service: {payload.get('message')}")
            print(f"OK  received count over WebSocket: {payload}")
            return payload
    finally:
        ws.close()
    raise SystemExit("NG  no count received (dashboard cannot reach counting-service?)")


def report_to_github(base_url: str, payload: dict) -> None:
    """GitHub Actions 上で実行されたときだけ、結果を実行画面に表示する。

    - ::notice::        → 実行画面の上部（Annotations）に緑のメッセージ
    - GITHUB_STEP_SUMMARY → 実行画面の Summary に結果の表
    """
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    print(f"::notice title=Smoke test passed::dashboard → counting OK (count={payload['count']})")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write("### ✅ Smoke test passed\n\n")
        f.write("| 項目 | 結果 |\n| --- | --- |\n")
        f.write(f"| dashboard URL | `{base_url}` |\n")
        f.write("| /health | 200 OK |\n")
        f.write("| dashboard → counting | OK |\n")
        f.write(f"| count | `{payload['count']}` |\n")
        f.write(f"| counting hostname | `{payload.get('hostname', '-')}` |\n\n")
        f.write("<details><summary>WebSocket で受信したデータ</summary>\n\n")
        f.write(f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n\n</details>\n\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: smoke_test.py <dashboard base URL>")
    base = sys.argv[1].rstrip("/")
    wait_for_health(base)
    result = wait_for_count(base)
    report_to_github(base, result)
    print("Smoke test passed")
