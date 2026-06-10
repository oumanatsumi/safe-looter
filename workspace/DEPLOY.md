# touchi 部署指南

## 架构

```
浏览器 ──→ Nginx (:80) ──→ 前端静态文件 (/opt/touchi/frontend)
                          ──→ /api/*  ──→ Gunicorn (:5000) ──→ Flask
                          ──→ /output/*     → 后端生成的 GIF
                          ──→ /resources/*  → 道具图标、表情
```

## 前置要求

- **Python >= 3.7**（建议 3.9+）
- 如果 Python 版本过旧（如 3.6），需先升级：
  ```bash
  sudo apt install -y python3.9 python3.9-venv
  # 然后用 python3.9 替代 python3 创建虚拟环境
  ```

## 1. 服务器准备

```bash
# 安装依赖
sudo apt update
sudo apt install -y nginx python3 python3-venv python3-pip

# 创建目录结构
sudo mkdir -p /opt/touchi/backend/data
sudo mkdir -p /opt/touchi/backend/output
sudo mkdir -p /opt/touchi/frontend
sudo mkdir -p /var/log/touchi

# 创建日志目录
sudo mkdir -p /var/log/touchi
```

## 2. 部署后端

```bash
# 上传并解压
cd /opt/touchi
tar -xzf touchi-backend.tar.gz -C backend/

# 创建 Python 虚拟环境
cd /opt/touchi/backend
python3.8 -m venv venv
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

# 设置权限
sudo chown -R www-data:www-data /opt/touchi
sudo chmod -R 755 /opt/touchi
```

## 3. 部署前端

```bash
# 上传并解压
cd /opt/touchi
tar -xzf touchi-frontend.tar.gz -C frontend/

sudo chown -R www-data:www-data /opt/touchi/frontend
```

## 4. 配置 Nginx

```bash
# 复制配置文件
sudo cp workspace/touchi.oumanatsumi.cn.conf /etc/nginx/sites-available/

# 启用站点
sudo ln -sf /etc/nginx/sites-available/touchi.oumanatsumi.cn.conf /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 nginx
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

```bash
sudo apt install -y certbot python3-certbot-nginx
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

## 文件清单

| 文件 | 说明 |
|------|------|
| `workspace/packages/touchi-backend.tar.gz` | 后端 Python 代码 + 资源文件 |
| `workspace/packages/touchi-frontend.tar.gz` | 前端静态文件 |
| `workspace/touchi.oumanatsumi.cn.conf` | Nginx 站点配置 |
| `workspace/touchi.service` | Systemd 服务文件 |
| `workspace/package.sh` | 打包脚本（在开发机执行） |
