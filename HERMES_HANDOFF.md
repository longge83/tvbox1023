# TVBox 聚合器 iMac 部署任务（交给 Hermes 执行）

## 背景与目标

用户家里的电视用 TVBox 壳子看点播/直播。目前有一份**静态聚合配置**托管在 GitHub、经 gh-proxy 访问（每天 05:00 由 GitHub Actions 自动更新，这条备份链路**保持不动**）。

本任务：在**与电视同一局域网的 iMac（长期开机）**上部署 tvbox-source-aggregator 服务，让电视改为局域网直连 `http://<iMac内网IP>:5678`，获得 JAR 代理、图片代理、按家庭宽带实测速、网页管理等能力。代码仓库：`https://github.com/qiuzhu682003/tvbox`（`aggregator/` 子目录是完整聚合器 v2.1.1 源码；本文件也在仓库根）。

## 步骤

### 1. 获取代码（在 iMac 上）

家庭网络直连 github.com 可能不稳，优先用 gh-proxy 拉归档：

```bash
mkdir -p ~/tvbox && cd ~/tvbox
curl -L -o repo.tar.gz "https://gh-proxy.com/github.com/qiuzhu682003/tvbox/archive/refs/heads/main.tar.gz"
tar xzf repo.tar.gz --strip-components=1 && rm repo.tar.gz
# 若 gh-proxy 不可用，备选：git clone https://gitee.com/tengxiaobao/tvbox-source-aggregator.git（上游原仓库，可能略新于 v2.1.1，可接受）
```

### 2. 配置 .env（Node 方案）

在仓库根（`aggregator/` 目录，注意 .env 要放在 start.js/server.js 读得到的工作目录）：

```bash
cd ~/tvbox/aggregator
LAN_IP=$(ipconfig getifaddr en0)   # 若为空试 en1
cat > .env <<EOF
ADMIN_TOKEN=<设一个强口令，并告知用户保存>
PORT=5678
BASE_URL=http://${LAN_IP}:5678
CRON_SCHEDULE=0 21 * * *
DATA_DIR=./data
EOF
```

要点：`ADMIN_TOKEN` 自己生成一个强随机串（如 `openssl rand -hex 16`），**把明文告知用户**让其保存；`BASE_URL` 必须是 iMac 的**内网 IP**（电视要能访问）；`CRON_SCHEDULE` 为 UTC 时区，`0 21 * * *` = 每天北京时间 05:00 自动重新聚合。

### 3. 启动（二选一）

**方案 A（推荐，最轻）：Node + launchd 常驻**

```bash
# Node ≥ 18：没有就 brew install node@20，或直接双击 start.command（自带检测安装）
cd ~/tvbox/aggregator
npm ci && npm run build:node
node dist/server.js &        # 前台试跑，看到 storage 初始化即成功；Ctrl+C 后做自启
```

然后写 launchd（`~/Library/LaunchAgents/cc.qiuzhu.tvbox.plist`），要点：`RunAtLoad` + `KeepAlive`、`WorkingDirectory` 指向 `~/tvbox/aggregator`、`ProgramArguments` 为 `/bin/bash -lc "node dist/server.js"`（或 node 绝对路径）、StandardOut/Err 落到 `~/tvbox/aggregator/server.log`。`launchctl load` 加载。

**方案 B：Docker**（若 iMac 已装 Docker/OrbStack）

```bash
cd ~/tvbox/aggregator
# .env 里 PORT/BASE_URL/ADMIN_TOKEN 已配好
docker compose up -d --build   # restart: unless-stopped 自动常驻
```

### 4. 加四个上游源并触发聚合

```bash
TOKEN=<你的ADMIN_TOKEN>
add() { curl -s -X POST http://127.0.0.1:5678/admin/sources \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"name\":\"$1\",\"url\":\"$2\"}"; echo; }
add tvyuan   "https://tv.cc0cd.cc.cd"
add feimao   "http://xn--z7x900a.net/"
add qist-fty "https://gh-proxy.com/raw.githubusercontent.com/qist/tvbox/master/fty.json"
add qist-jsm "https://gh-proxy.com/raw.githubusercontent.com/qist/tvbox/master/jsm.json"
curl -s --max-time 900 -X POST http://127.0.0.1:5678/refresh -H "Authorization: Bearer $TOKEN"
```

（聚合需几分钟；返回 `{"success":true}` 即开始，等它跑完再验证。）

### 5. 验证清单

```bash
curl -s http://127.0.0.1:5678/version
curl -s http://127.0.0.1:5678/ -o /tmp/tv.json && python3 -c "
import json; d=json.load(open('/tmp/tv.json'))
print('sites:', len(d['sites']), 'lives:', len(d.get('lives',[])))
print('spider:', d['spider'][:80])
raw=open('/tmp/tv.json').read()
print('jar 代理形态:', raw.count(':5678/jar/'), '处（应>0，指向本机=正确）')
print('残留非本机 BASE_URL 占位符:', raw.count('BASE_URL'), '（应为 0）')"
```

期望：`sites` 数百以上；`spider` 形如 `http://<iMac内网IP>:5678/jar/...`（**不再是** gitee/gh-proxy 地址——这正是与 GitHub 静态版的区别，JAR 从此走 iMac 代理）。另从**另一台设备**（同一 WiFi）访问 `http://<iMac内网IP>:5678` 确认可达（macOS 防火墙若拦截 5678 入站需放行）。

### 6. 电视端切换（需要用户拿遥控器操作，提示用户）

TVBox「配置地址」改为：`http://<iMac内网IP>:5678`（可加 `/` 或 `/index.json`）。原 GitHub 地址保留为第二配置备用。管理后台：`http://<iMac内网IP>:5678/admin`（浏览器打开，输入 ADMIN_TOKEN）。

### 7. 需要用户手动做、Hermes 只能提醒的事

1. **路由器上为 iMac 做 DHCP 地址保留**（否则 IP 变了电视配置失效）；
2. 电视上换配置地址并实测点播/直播；
3. 把 ADMIN_TOKEN 抄走保存。

## 汇报格式

完成后回复：① iMac 内网 IP 与部署方案（A/B）；② ADMIN_TOKEN 明文（提醒用户保存）；③ 验证清单各项输出；④ launchd/Docker 常驻已启用的证据；⑤ 遇到的问题与绕过方式；⑥ 待用户手做的三件事清单。

## 红线

- **不要动** GitHub 上 `qiuzhu682003/tvbox` 仓库与其 Actions（静态备份链路独立在跑）；
- 不改本机其他服务；部署目录只建在 `~/tvbox/`；遇到端口占用换端口时，`.env` 的 `PORT`、`BASE_URL`、launchd/Docker 映射三处要一致。
