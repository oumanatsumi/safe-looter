# touchi 部署指南

支持 Debian/Ubuntu 和 RHEL/CentOS (Alibaba Cloud Linux) 两套系统。

## 架构

```
浏览器 ──→ Nginx (:80) ──→ 前端静态文件 (/opt/touchi/frontend)
                          ──→ /api/*  ──→ Gunicorn (:5000) ──→ Flask
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
# 创建目录结构
sudo mkdir -p /opt/touchi/backend/data
sudo mkdir -p /opt/touchi/backend/output
sudo mkdir -p /opt/touchi/frontend
sudo mkdir -p /var/log/touchi
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
#   port: 5000
#   admin_token: 改成你的密码
#   db_path: data/collection.db

# 创建空的数据库文件
touch /opt/touchi/backend/data/collection.db

# 设置权限（RHEL/CentOS 用 nginx 用户，Debian/Ubuntu 用 www-data）
sudo chown -R nginx:nginx /opt/touchi
sudo chmod -R 755 /opt/touchi
# 确保 nginx 能写 data/ 和 output/
sudo chmod 770 /opt/touchi/backend/data
sudo chmod 770 /opt/touchi/backend/output
```

> **注意**：如果 SELinux 处于 enforcing 模式，需要放行：
> ```bash
> sudo setsebool -P httpd_can_network_connect on
> sudo chcon -R -t httpd_sys_rw_content_t /opt/touchi/backend/data
> sudo chcon -R -t httpd_sys_rw_content_t /opt/touchi/backend/output
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
sudo cp workspace/touchi.oumanatsumi.cn.conf /etc/nginx/conf.d/touchi.conf
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
sudo cp workspace/touchi.service /etc/systemd/system/

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
curl http://127.0.0.1:5000/api/leaderboard
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

# 数据库备份
cp /opt/touchi/backend/data/collection.db /opt/touchi/backend/data/collection.db.bak.$(date +%Y%m%d)

# 更新部署
# 1. 上传新的 tar.gz
# 2. 解压覆盖
# 3. sudo systemctl restart touchi
```

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
