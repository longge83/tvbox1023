#!/usr/bin/env python3
"""从本地 tvbox-source-aggregator 导出可静态托管的 TVBox 配置。

聚合器输出里所有 Spider JAR 都被改写成 {BASE_URL}/jar/<key> 代理地址，
静态部署没有这个代理，因此按 SQLite 里的 jar:<key> 映射还原为原始 URL
（原始源为 gitee / gh-proxy / 源站自有域名，电视端直连可达）。
图片代理 pic 无静态等价物，直接删除。
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

AGG_DIR = Path(r"C:\Users\qiuzhu\ZCodeProject\tvbox-source-aggregator")
SRC = AGG_DIR / "merged-config.json"
DB = AGG_DIR / "data" / "tvbox.db"
OUT = Path(__file__).parent / "tvbox.json"

LOCAL_HOSTS = ("192.168.4.100:5678", "127.0.0.1:5678", "localhost:5678")


def load_jar_map() -> dict:
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT key, value FROM kv WHERE key LIKE 'jar:%'").fetchall()
    con.close()
    return {k.removeprefix("jar:"): v for k, v in rows}


def main() -> int:
    raw = SRC.read_text(encoding="utf-8")
    jar_map = load_jar_map()
    if not jar_map:
        print("ERROR: jar mapping in SQLite is empty", file=sys.stderr)
        return 1

    replaced = 0
    unresolved = set()

    def sub(match: re.Match) -> str:
        nonlocal replaced
        key = match.group(1)
        origin = jar_map.get(key)
        if origin is None:
            unresolved.add(key)
            return match.group(0)
        replaced += 1
        return origin

    pattern = re.compile(
        r"https?://(?:" + "|".join(re.escape(h) for h in LOCAL_HOSTS) + r")/jar/([0-9a-f]+)"
    )
    raw = pattern.sub(sub, raw)

    # 聚合后未再 refresh 时可能残留占位符形态
    raw = raw.replace("%7B%7BBASE_URL%7D%7D", "").replace("{BASE_URL}", "")

    cfg = json.loads(raw)
    pic = cfg.pop("pic", None)

    residual = [
        u for u in re.findall(r"https?://[^\"\\s]+", raw)
        if any(h in u for h in LOCAL_HOSTS) and "127.0.0.1:9978" not in u
    ]

    OUT.write_text(json.dumps(cfg, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"sites={len(cfg.get('sites', []))} lives={len(cfg.get('lives', []))}")
    print(f"jar rewritten={replaced} unresolved={sorted(unresolved) if unresolved else 'none'}")
    print(f"pic removed={pic!r}")
    print(f"residual local urls={residual if residual else 'none'}")
    print(f"written: {OUT} ({OUT.stat().st_size} bytes)")
    return 1 if unresolved or residual else 0


if __name__ == "__main__":
    sys.exit(main())
