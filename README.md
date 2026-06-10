# 🐭 鼠鼠偷吃 — Safe Looter

> 三角洲行动主题的摸金抽卡小游戏，点击"偷吃"开箱，收集金红图鉴！

<p align="center">
  <img src="backend/resources/expressions/happy.png" width="80" alt="happy mouse">
  <img src="backend/resources/expressions/eat.png" width="80" alt="eating mouse">
  <img src="backend/resources/expressions/cry.png" width="80" alt="cry mouse">
</p>

## 🎮 玩法

- 点击 **偷吃** 按钮开启安全箱，随机获得 2~6 件物品
- 物品分为 💙蓝 💜紫 💛金 ❤️红 四个品质
- 收集金红品质物品完成 **图鉴**
- 积累哈夫币升级 **特勤处** 扩大格子（2x2 → 7x7）
- 激活 **六套猛攻** 大幅提升金红爆率
- 开启 **自动偷吃** 挂机摸金

## 🎲 概率系统

| 品质 | 普通模式 | 猛攻模式 | 自动模式 |
|------|:-------:|:-------:|:-------:|
| 💙 蓝 | 25% | 0%  | 35%  |
| 💜 紫 | 42% | 45% | 52%  |
| 💛 金 | 28% | 45% | 9.3% |
| ❤️ 红 | 5%  | 10% | 1.7% |

同品质内还有稀有度分级：普通 / 稀有（1/3概率）/ 超稀有「❤️心」「💧泪」（1/100概率）。

## 🏗️ 项目结构

```
safe-looter/
├── backend/
│   ├── app.py              # Flask 应用工厂
│   ├── wsgi.py             # Gunicorn 入口
│   ├── config.py/yaml      # 配置（环境变量 > YAML > 默认）
│   ├── database.py         # SQLite 操作、表初始化、配置读写
│   ├── api/                # REST API 蓝图
│   │   ├── touchi.py       # POST /api/touchi — 偷吃核心
│   │   ├── collection.py   # GET  /api/collection — 图鉴
│   │   ├── economy.py      # 经济系统、猛攻、升级、自动偷吃
│   │   ├── stats.py        # 排行榜、道具列表
│   │   └── admin.py        # 管理员配置
│   ├── game/               # 游戏核心逻辑
│   │   ├── touchi.py       # 开箱生成、物品加载、GIF 渲染
│   │   ├── economy.py      # 经济逻辑 + APScheduler 自动调度
│   │   └── events.py       # 7 种随机事件
│   └── resources/          # 道具图标 + 表情
├── frontend/               # 原生 JS SPA
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── api.js          # API 客户端
│       ├── app.js          # 应用控制器
│       └── pages/          # 偷吃、图鉴、仓库、管理
└── workspace/              # 部署相关
    ├── DEPLOY.md           # 部署指南 + 更新流程 + 故障排查
    ├── touchi.oumanatsumi.cn.conf  # Nginx 配置
    ├── touchi.service      # Systemd 服务
    └── package.sh          # 打包脚本
```

## 🚀 快速开始

### 本地开发

```bash
cd backend
pip install -r requirements.txt
python app.py
# 打开 http://localhost:5001
```

### 生产部署

在线地址：**[touchi.oumanatsumi.cn](https://touchi.oumanatsumi.cn)**

部署架构：

```
浏览器 → Nginx :80 → /            → 前端静态文件
                    → /api/*       → Gunicorn :5001 → Flask
                    → /output/*    → 生成的 GIF
                    → /resources/* → 道具图标
```

完整部署指南、更新流程和故障排查见 **[DEPLOY.md](workspace/DEPLOY.md)**。

```bash
# 后端
cd /opt/touchi && tar -xzf touchi-backend.tar.gz -C backend/
cd backend && python3 -m venv venv && pip install -r requirements.txt
sudo systemctl enable --now touchi

# 前端（Nginx 直接 serve）
tar -xzf touchi-frontend.tar.gz -C frontend/
# RHEL/CentOS:
sudo cp workspace/touchi.oumanatsumi.cn.conf /etc/nginx/conf.d/touchi.conf
# Debian/Ubuntu:
sudo cp workspace/touchi.oumanatsumi.cn.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/touchi.oumanatsumi.cn.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 🔧 配置

`backend/config.yaml` + 环境变量覆盖：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `port` | `5001` | 后端监听端口 |
| `admin_token` | `不告诉你` | 管理员密码 |
| `auto_touchi_interval` | `600` | 自动偷吃间隔（秒） |
| `mengong_cost` | `3000000` | 猛攻消耗（哈夫币） |
| `default_grid_size` | `2` | 初始背包格子 |
| `db_path` | `data/collection.db` | 数据库路径，可指向项目外 |

游戏参数（爆率、冷却等）通过管理员面板实时修改，存储在 SQLite 中。

## 📡 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/touchi` | 执行一次偷吃 |
| GET | `/api/collection/<user_id>` | 获取图鉴 |
| GET | `/api/economy/<user_id>` | 获取经济数据 |
| POST | `/api/menggong` | 激活猛攻 |
| POST | `/api/upgrade` | 升级特勤处 |
| POST | `/api/auto-touchi/start` | 开启自动偷吃 |
| POST | `/api/auto-touchi/stop` | 关闭自动偷吃 |
| GET | `/api/leaderboard` | 排行榜 |
| GET/POST | `/api/admin/config` | 管理配置 |

## 📄 License

MIT
