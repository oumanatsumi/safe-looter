# 鼠鼠偷吃 (touchi) — 三角洲行动

Web 小游戏，模拟"三角洲行动"中的偷吃（摸金）玩法。后端 Python Flask + 前端原生 HTML/CSS/JS SPA。

## 项目结构

```
touchi/
├── backend/
│   ├── app.py              # Flask 工厂函数，注册蓝图、静态文件路由
│   ├── config.py            # 配置加载 (YAML + 环境变量覆盖)
│   ├── config.yaml          # 默认配置文件
│   ├── database.py          # SQLite 连接、表初始化、游戏配置读写
│   ├── api/
│   │   ├── touchi.py        # POST /api/touchi — 偷吃一次
│   │   ├── collection.py    # GET/POST /api/collection — 图鉴
│   │   ├── economy.py       # GET/POST /api/economy — 经济系统、升级、猛攻、自动偷吃
│   │   ├── stats.py         # GET /api/stats — 统计
│   │   └── admin.py         # GET/POST /api/admin — 管理员配置
│   ├── game/
│   │   ├── touchi.py        # 偷吃核心逻辑：随机格子、物品生成、概率判定
│   │   ├── economy.py       # 经济逻辑 + APScheduler 自动偷吃调度
│   │   └── events.py        # 事件系统
│   ├── data/                # SQLite 数据库文件 (collection.db)
│   ├── resources/
│   │   ├── items/           # 物品图标 PNG (蓝/紫/金/红品质)
│   │   └── expressions/     # 鼠鼠表情 (cry/eat/happy/sousuo)
│   └── output/              # 生成的偷吃结果 GIF
└── frontend/
    ├── index.html           # SPA 入口 (偷吃 / 图鉴 / 仓库 / 管理)
    ├── css/style.css
    └── js/
        ├── app.js           # 应用入口、导航、初始化
        ├── api.js           # API 请求封装
        ├── utils.js         # 工具函数
        └── pages/
            ├── touchi.js    # 偷吃页面逻辑
            ├── collection.js # 图鉴页面
            ├── warehouse.js  # 仓库/特勤处/猛攻/自动偷吃
            └── admin.js     # 管理员设置弹窗
```

## 运行方式

```bash
cd backend
pip install -r requirements.txt
python app.py
# 监听 http://0.0.0.0:5000
```

配置优先级：**环境变量 > config.yaml > 代码默认值**。关键环境变量：`TOUCHI_DB_PATH`, `TOUCHI_PORT`, `TOUCHI_HOST`, `ADMIN_TOKEN`。

## 技术要点

- **数据库**：SQLite (WAL 模式)，路径 `backend/data/collection.db`。使用 `write_with_retry()` 处理并发写入锁。
- **游戏配置**：存储在 `system_config` 表中（不是 YAML），通过 admin API 动态修改。默认值在 `database.py` 的 `GAME_CONFIG_DEFAULTS`。
- **自动偷吃**：APScheduler 后台线程，在 `game/economy.py` 的 `start_scheduler()` 中启动。
- **物品品质**：蓝/紫/金/红（blue/purple/gold/red），概率可在管理员面板调整。
- **六套猛攻**：消耗 300 万哈夫币，持续 2 分钟，无蓝装、金红爆率翻倍。
- **管理员 token**：默认 `admin123`，可在 `config.yaml` 或环境变量 `ADMIN_TOKEN` 修改。
- **前端路由**：SPA，所有非 `/api/`、`/output/`、`/resources/` 路径都返回 `index.html`。

## API 概述

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/touchi` | 执行一次偷吃 |
| GET | `/api/collection/<user_id>` | 获取用户图鉴 |
| POST | `/api/collection` | 标记物品已发现 |
| GET | `/api/economy/<user_id>` | 获取用户经济数据 |
| POST | `/api/economy/upgrade` | 升级特勤处 |
| POST | `/api/economy/menggong` | 激活猛攻 |
| POST | `/api/economy/auto` | 切换自动偷吃 |
| GET | `/api/stats/<user_id>` | 获取统计 |
| GET | `/api/admin/config` | 获取当前配置 |
| POST | `/api/admin/config` | 更新配置 (需 token) |

## 注意事项

- `config.yaml` 只包含静态配置；游戏参数（冷却时间、爆率等）存储在数据库 `system_config` 表中。
- 自动偷吃调度器在 `create_app()` 时启动，持续运行在后台线程。
- 前端的"上次偷吃结果"存在 `user_last_touchi` 表，以 JSON 存储物品列表。
