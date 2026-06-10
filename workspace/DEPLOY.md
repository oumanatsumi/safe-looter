# touchi 部署指南

支持 Debian/Ubuntu 和 RHEL/CentOS (Alibaba Cloud Linux) 两套系统。

## 架构

```
浏览器 ──→ Nginx (:80) ──→ 前端静态文件 (/opt/touchi/frontend)
                          ──→ /api/*  ──→ Gunicorn (:5001) ──→ Flask
                          ──→ /output/*     → 后端生成的 GIF
                          ──→ /resources/*  → 道具图标、表情
```

## 前置要求

- **Python >= 3.8**
- 本文档使用 **RHEL/CentOS 8+** (含 Alibaba Cloud Linux 3) 的命令。Debian/Ubuntu 用户可参考斜体注释。

## 1. 服务器准备

**RHEL/CentOS / Alibaba Cloud Linux：**
```bash
sudo dnf install -y nginx python38 python38-pip python38-devel
# 创建 python3 软链（如未自动创建）
sudo alternatives --set python3 /usr/bin/python3.8 2>/dev/null || true
```

**Debian/Ubuntu：**
```bash
sudo apt update
sudo apt install -y nginx python3 python3-venv python3-pip
```

**通用操作：**
```bash
# 创建目录结构（output 用于存放生成的 GIF）
sudo mkdir -p /opt/touchi/backend/output
sudo mkdir -p /opt/touchi/frontend
sudo mkdir -p /var/log/touchi
sudo chown nginx:nginx /var/log/touchi
```

## 2. 部署后端

```bash
# 上传并解压
cd /opt/touchi
tar -xzf touchi-backend.tar.gz -C backend/

# 创建 Python 虚拟环境
cd /opt/touchi/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# 确认配置（按需修改）
vim /opt/touchi/backend/config.yaml
#   host: 127.0.0.1       ← 只监听本地，由 nginx 代理
#   port: 5001
#   admin_token: 改成你的密码
#   db_path: 数据库路径，可指向项目外（例 /opt/astrbot/.../collection.db）
#   items_dir / expressions_dir / output_dir: 保持默认相对路径即可

# 如 db_path 指向了外部目录，需要额外创建并赋权
# 例：db_path: /opt/astrbot/data/plugin_data/astrbot_plugin_touchi/collection.db
sudo mkdir -p /opt/astrbot/data/plugin_data/astrbot_plugin_touchi

# 设置权限（RHEL/CentOS 用 nginx 用户，Debian/Ubuntu 用 www-data）
sudo chown -R nginx:nginx /opt/touchi
sudo chmod -R 755 /opt/touchi
# 确保 nginx 能写 output/
sudo chmod 770 /opt/touchi/backend/output

# 赋予外部数据库目录权限（按你的实际 db_path 调整）
sudo chown -R nginx:nginx /opt/astrbot/data/plugin_data/astrbot_plugin_touchi
sudo chmod 770 /opt/astrbot/data/plugin_data/astrbot_plugin_touchi
```

> **注意**：如果 SELinux 处于 enforcing 模式，需要放行：
> ```bash
> sudo setsebool -P httpd_can_network_connect on
> sudo chcon -R -t httpd_sys_rw_content_t /opt/touchi/backend/output
> # 如果 db_path 指向外部，同样需要放行
> sudo chcon -R -t httpd_sys_rw_content_t /opt/astrbot/data/plugin_data/astrbot_plugin_touchi
> ```

## 3. 部署前端

```bash
# 上传并解压
cd /opt/touchi
tar -xzf touchi-frontend.tar.gz -C frontend/

sudo chown -R nginx:nginx /opt/touchi/frontend
```

## 4. 配置 Nginx

**RHEL/CentOS：**
```bash
sudo cp touchi.oumanatsumi.cn.conf /etc/nginx/conf.d/touchi.conf
```

**Debian/Ubuntu：**
```bash
sudo cp workspace/touchi.oumanatsumi.cn.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/touchi.oumanatsumi.cn.conf /etc/nginx/sites-enabled/
```

**通用：**
```bash
# 测试配置
sudo nginx -t

# 启动 / 重载
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

## 5. 配置 Systemd 服务

```bash
# 复制 service 文件
sudo cp touchi.service /etc/systemd/system/

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable touchi
sudo systemctl start touchi

# 检查状态
sudo systemctl status touchi
journalctl -u touchi -f   # 查看日志
```

## 6. 配置 SSL（Let's Encrypt）

**RHEL/CentOS：**
```bash
sudo dnf install -y certbot python3-certbot-nginx
```

**Debian/Ubuntu：**
```bash
sudo apt install -y certbot python3-certbot-nginx
```

**通用：**
```bash
sudo certbot --nginx -d touchi.oumanatsumi.cn
# 选择 redirect (HTTP → HTTPS)
```

## 7. 验证部署

```bash
# 检查服务
sudo systemctl status nginx
sudo systemctl status touchi

# 测试 API
curl http://127.0.0.1:5001/api/leaderboard
curl https://touchi.oumanatsumi.cn/api/leaderboard

# 打开浏览器访问
# https://touchi.oumanatsumi.cn
```

## 日常维护

```bash
# 重启后端
sudo systemctl restart touchi

# 查看后端日志
journalctl -u touchi -f

# 查看 nginx 日志
tail -f /var/log/nginx/touchi.access.log
tail -f /var/log/nginx/touchi.error.log

# 查看 gunicorn 错误日志
tail -f /var/log/touchi/gunicorn-error.log

# 数据库备份（路径以 config.yaml 中的 db_path 为准）
DB_PATH=$(grep 'db_path:' /opt/touchi/backend/config.yaml | sed 's/.*: //')
cp "$DB_PATH" "$DB_PATH.bak.$(date +%Y%m%d)"
```

## 更新部署（代码变更后重新上线）

### 流程概览

```
本地开发 → 打包 → 上传服务器 → 解压覆盖 → 按需重载配置 → 重启服务
```

### 步骤

**1. 本地 — 打包**

```bash
cd E:/proj/touchi
bash workspace/package.sh
# 产物: workspace/packages/touchi-backend.tar.gz
#       workspace/packages/touchi-frontend.tar.gz
```

**2. 上传到服务器**

```bash
scp workspace/packages/touchi-backend.tar.gz  root@121.43.243.130:/opt/touchi/
scp workspace/packages/touchi-frontend.tar.gz root@121.43.243.130:/opt/touchi/
```

**3. 服务器 — 解压覆盖**

```bash
# 后端
cd /opt/touchi
tar -xzf touchi-backend.tar.gz -C backend/

# 前端（纯静态文件，有改动才做）
tar -xzf touchi-frontend.tar.gz -C frontend/
```

**4. 服务器 — 配置文件（仅首次或配置变更时需要）**

以下文件首次部署已就位，**后续代码更新通常无需重做**。如果这些文件有改动才执行：

```bash
# systemd service（改了端口/路径才需更新）
sudo cp /opt/touchi/workspace/touchi.service /etc/systemd/system/
sudo systemctl daemon-reload

# nginx 配置（改了路由/端口才需更新）
sudo cp /opt/touchi/workspace/touchi.oumanatsumi.cn.conf /etc/nginx/conf.d/touchi.conf
sudo nginx -t && sudo systemctl reload nginx
```

**5. 服务器 — 重启后端**

```bash
# Python 依赖有变更时先装
cd /opt/touchi/backend
source venv/bin/activate
pip install -r requirements.txt
deactivate

# 重启
sudo systemctl restart touchi
sudo systemctl status touchi
```

**6. 验证**

```bash
curl http://127.0.0.1:5001/api/leaderboard
# 浏览器访问 https://touchi.oumanatsumi.cn
```

### 变更类型速查

| 改了什么 | 需要做的 |
|---------|---------|
| 仅 Python 代码（game/api） | 重新打包后端 → 上传解压 → `systemctl restart touchi` |
| 仅前端（HTML/CSS/JS） | 重新打包前端 → 上传解压 → 清浏览器缓存 |
| 新增/修改 Python 依赖 | 上传后端包 + 手动 `pip install -r requirements.txt` + 重启 |
| 改了端口 | 改 `config.yaml` + `touchi.service` + nginx conf，三处全部重载 |
| 新增道具图片 | 放入 `resources/items/` 后重新打包后端上传 |

### 常见问题

| 现象 | 检查 |
|------|------|
| 网页打不开/超时 | `sudo ss -tlnp \| grep :80`，确认 nginx 在监听；安全组放行 80 |
| curl 后端 5001 拒绝连接 | `sudo systemctl status touchi`，`journalctl -u touchi -n 20` |
| gunicorn 日志权限报错 | `sudo chown nginx:nginx /var/log/touchi` |
| SELinux 相关错误 | `sudo setsebool -P httpd_can_network_connect on` |
| DNS 解析后仍超时 | 等 1-2 分钟 DNS 传播，或用 `curl -H "Host: touchi.oumanatsumi.cn" http://121.43.243.130/` 绕过 DNS 测试 |

## RHEL/CentOS vs Debian 差异速查

| 项目 | RHEL/CentOS 8+ | Debian/Ubuntu |
|------|:---:|:---:|
| Nginx 用户 | `nginx` | `www-data` |
| 包管理器 | `dnf` | `apt` |
| Nginx 站点配置 | `/etc/nginx/conf.d/*.conf` | `/etc/nginx/sites-enabled/` |
| Python 包 | `python38` | `python3` |

## 文件清单

| 文件 | 说明 |
|------|------|
| `workspace/packages/touchi-backend.tar.gz` | 后端 Python 代码 + 资源文件 |
| `workspace/packages/touchi-frontend.tar.gz` | 前端静态文件 |
| `workspace/touchi.oumanatsumi.cn.conf` | Nginx 站点配置 |
| `workspace/touchi.service` | Systemd 服务文件 |
| `workspace/package.sh` | 打包脚本（在开发机执行） |
