# 鼠鼠偷吃 (safe-looter) — 三角洲行动

摸金抽卡 Web 小游戏。后端 Python Flask + 前端原生 HTML/CSS/JS SPA，纯前端 CSS Grid 渲染结果（无服务端 GIF 生成）。

在线地址: https://touchi.oumanatsumi.cn
仓库: https://github.com/oumanatsumi/safe-looter

## 项目结构

```
touchi/
├── backend/
│   ├── app.py / wsgi.py       # Flask 应用 + Gunicorn 入口
│   ├── config.py / config.yaml # 配置（环境变量 > YAML），端口 5001
│   ├── database.py            # SQLite (WAL), write_with_retry(), 自动列迁移
│   ├── api/                   # touchi / collection / economy / stats / admin
│   ├── game/
│   │   ├── touchi.py          # 物品加载、概率判定、网格布局、build_touchi_result()
│   │   ├── economy.py         # 经济系统 + APScheduler 自动偷吃
│   │   └── events.py          # 7 种随机事件（各 4% 概率）
│   └── resources/             # items/(png) + expressions/(cry/eat/happy/sousuo/eating.gif)
├── frontend/                  # 原生 JS SPA，无框架
│   ├── index.html
│   └── js/pages/              # touchi.js / collection.js / warehouse.js / admin.js
└── workspace/                 # DEPLOY.md / nginx conf / systemd service / package.sh
```

## 本地运行

```bash
cd backend && pip install -r requirements.txt && python app.py
# http://localhost:5001
```

## 核心架构

### 偷吃流程
1. 前端 `POST /api/touchi` → 后端 `build_touchi_result()` 返回结构化 JSON
2. 前端 `buildSafeGrid()` 构建 CSS Grid 安全箱 + 逐项揭晓动画
3. 搜索阶段：灰框 + 搜索图标旋转 → 揭晓：品质色弹入 + 物品图片
4. 全部揭晓后：eating.gif 切换为结果表情，底部展示物品列表

### 概率系统
- 普通模式: 蓝25% 紫42% 金28% 红5%（可通过 admin 面板改）
- 猛攻模式: 蓝0% 紫45% 金45% 红10%
- RARE_ITEMS（17个）概率 1/3，ULTRA_RARE_ITEMS（心、雷）概率 1/100

### 搜索时长 (ms)
蓝 400 / 紫 600 / 金 1000 / 红 2500，物品间隔 150ms，揭晓顺序按坐标 (y,x) 从左到右从上到下

### 冷却持久化
双重防护：前端 localStorage + 后端 DB 列 `user_economy.last_touchi_time/touchi_cooldown`

### API 响应（POST /api/touchi 成功时）
```json
{
  "ok": true,
  "items": [{"name","level","x","y","width","height","search_duration_ms","image_url","value"}],
  "grid_size": 2, "region_width": 2, "region_height": 1,
  "expression": "happy", "total_search_ms": 1800,
  "total_value": 123456, "highest_level": "gold",
  "event": {"triggered": true, "type": "...", "message": "..."} | null,
  "wait_time": 90, "cooldown_modifier": 1.0
}
```

## 生产部署

- **服务器**: Alibaba Cloud Linux 3.2104 (RHEL/CentOS 8+), Nginx + Gunicorn + Systemd
- **用户**: `nginx`（非 www-data）
- **Nginx 配置**: `/etc/nginx/conf.d/touchi.conf`（非 sites-enabled）
- **后端端口**: 5001（仅 127.0.0.1，Nginx 代理 /api/*）
- **数据库路径**: `/opt/astrbot/data/plugin_data/astrbot_plugin_touchi/collection.db`
- **部署时注意**: `config.yaml` 已从打包中排除，不会覆盖生产配置

### 更新部署流程
```bash
# 本地打包（config.yaml 不在包内）
bash workspace/package.sh
# 上传
scp workspace/packages/touchi-backend.tar.gz root@121.43.243.130:/opt/touchi/
scp workspace/packages/touchi-frontend.tar.gz root@121.43.243.130:/opt/touchi/
# 服务器解压重启
cd /opt/touchi && tar -xzf touchi-backend.tar.gz -C backend/
tar -xzf touchi-frontend.tar.gz -C frontend/
sudo systemctl restart touchi
```

### 常见问题
- **前端没更新**: 浏览器 Ctrl+Shift+R 强制刷新
- **网络错误但 API 正常**: 前端 JS 文件是旧版本
- **日志权限**: `sudo chown nginx:nginx /var/log/touchi`
- **SELinux**: `sudo setsebool -P httpd_can_network_connect on`
- **DNS 超时**: 阿里云安全组放行 80 端口

### 关键 commit 里程碑
- `024b31e` 前端渲染重构：删除 300 行 Pillow GIF 代码，改为 CSS Grid 动画
- `5bcec71` 冷却持久化修复（localStorage + DB 双重防护）
