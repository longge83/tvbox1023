# tvbox — 自聚合 TVBox 点播配置

多源聚合的 TVBox 点播配置，**每天北京时间 05:00 由 GitHub Actions 自动重新聚合并推送**。

## 电视端配置地址

TVBox 壳子「配置地址」处填：

```
https://gh-proxy.com/raw.githubusercontent.com/longge83/tvbox1023/main/tvbox.json
```

（`gh-proxy.com` 为 GitHub raw 加速；若失效可换 `ghfast.top` 同路径。）

## 内容与来源

| 上游源 | 说明 |
|---|---|

聚合（去重 / 测速标注 / Spider JAR 收编）由 [tvbox-source-aggregator](https://gitee.com/tengxiaobao/tvbox-source-aggregator) v2.1.1 完成，源码 vendor 在 `aggregator/`。

## 静态化处理（export_static.py）

聚合器输出里所有 Spider JAR 被改写为 `<BASE_URL>/jar/<key>` 代理地址——静态托管没有这个代理，
本脚本按聚合器 SQLite 里的 `jar:<key>` 映射把它们**还原为原始 URL**（原始源均为国内可达：
gitee / gh-proxy / 源站自有域名），并删除图片代理 `pic` 字段。

## 本地手动刷新

```bash
# 1. 本地起聚合服务（在 tvbox-source-aggregator 目录）
npm run build:node && node dist/server.js
# 2. 用管理 API 加源后触发 POST /refresh（Bearer <ADMIN_TOKEN>）
# 3. 导出
curl -s http://127.0.0.1:5678/ -o ../tvbox-static/merged-config.json  # 放到聚合器目录
python export_static.py
git add tvbox.json && git commit -m refresh && git push
```

## 直播

直播源不依赖本配置，电视端单独填（已实测可用）：

- 点播+直播二合一：上方 tvbox.json（内含聚合的直播分组）
- 纯直播推荐：`https://gh-proxy.com/raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.m3u`（每 6h 更新）
- EPG：`https://gh-proxy.com/raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/e.xml`
