# WeChat Butler 快速开始指南

## 文档信息

- **版本**: v1.0.0
- **创建日期**: 2025-11-22
- **最后更新**: 2025-11-22
- **适用版本**: v0.1.0+

---

## 📋 目录

- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [基础配置](#基础配置)
- [编写第一个规则](#编写第一个规则)
- [启动服务](#启动服务)
- [测试验证](#测试验证)
- [常见问题](#常见问题)

---

## 环境要求

### 系统要求
- **操作系统**: Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+)
- **Python**: Python 3.11 或更高版本
- **内存**: 至少 100MB 可用内存
- **磁盘空间**: 至少 50MB 可用空间

### 依赖服务
1. **chatshell-api**: 用于读取微信消息并发送 webhook
2. **wechat-sendmsg**: 用于发送微信消息（可选，如果需要自动回复功能）

### 网络要求
- 本地网络可访问 chatshell-api 服务
- 可访问互联网（如果需要 LLM 功能）

---

## 安装步骤

### 方法一：从源码安装（推荐）

1. **克隆项目**
   ```bash
   git clone https://github.com/xlight/wechat-butler.git
   cd wechat-butler
   ```

2. **安装 Python 依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **验证安装**
   ```bash
   python --version
   # 应该显示 Python 3.11 或更高版本

   python -c "import fastapi; print('FastAPI installed')"
   ```

### 方法二：使用 Docker（可选）

1. **构建 Docker 镜像**
   ```bash
   docker build -t wechat-butler .
   ```

2. **运行容器**
   ```bash
   docker run -d \
     --name wechat-butler \
     -p 8080:8080 \
     -v $(pwd)/config:/app/config \
     -v $(pwd)/logs:/app/logs \
     wechat-butler
   ```

### 方法三：使用预编译包（未来版本）

```bash
# 下载最新版本
wget https://github.com/xlight/wechat-butler/releases/latest/download/wechat-butler.tar.gz

# 解压
tar -xzf wechat-butler.tar.gz
cd wechat-butler

# 运行
./wechat-butler
```

---

## 基础配置

### 1. 创建配置文件

在项目根目录创建 `config.yaml` 文件：

```yaml
# config.yaml
server:
  host: "0.0.0.0"      # 监听地址
  port: 8080           # 监听端口
  debug: false         # 调试模式

webhook:
  secret: "your-secret-key-here"  # Webhook 签名密钥
  path: "/webhook/message"        # Webhook 路径

wechat:
  sendmsg_url: "http://localhost:8000"  # wechat-sendmsg 地址
  api_key: ""                           # API 密钥（如果需要）

logging:
  level: "INFO"        # 日志级别: DEBUG, INFO, WARNING, ERROR
  file: "./logs/wechat-butler.log"  # 日志文件路径
  max_size: 10         # 日志文件最大大小（MB）
  backup_count: 5      # 保留的日志文件数量

rules:
  directory: "./rules"  # 规则文件目录
  auto_reload: true     # 自动重载规则文件
```

### 2. 创建规则目录

```bash
mkdir -p rules
```

### 3. 配置 chatshell-api

确保 chatshell-api 已正确配置 webhook：

```bash
# 启动 chatshell-api 时添加 webhook 参数
./bin/chatlog server \
  --webhook-host http://localhost:8080 \
  --webhook-path /webhook/message \
  --webhook-secret your-secret-key-here
```

### 4. 启动 wechat-sendmsg（可选）

如果需要自动回复功能，启动 wechat-sendmsg：

```bash
# 在另一个终端启动 wechat-sendmsg
python -m wechat_sendmsg
```

---

## 编写第一个规则

### 1. 创建基础规则文件

在 `rules/` 目录下创建 `basic.yaml` 文件：

```yaml
# rules/basic.yaml
rules:
  - name: "自动问候回复"
    description: "自动回复问候消息"
    enabled: true
    priority: 100
    conditions:
      - type: "keyword"
        field: "content"
        value: ["你好", "hello", "hi", "您好"]
        case_sensitive: false
    actions:
      - type: "reply"
        content: "你好！我是自动回复助手，有什么可以帮您的吗？"
        delay: 1  # 延迟1秒回复

  - name: "文件助手转发"
    description: "将文件助手消息转发到指定群聊"
    enabled: true
    priority: 90
    conditions:
      - type: "talker"
        value: "filehelper"
    actions:
      - type: "forward"
        to: "工作群"
        prefix: "[文件助手] "

  - name: "重要消息提醒"
    description: "包含关键词的消息发送通知"
    enabled: true
    priority: 80
    conditions:
      - type: "keyword"
        field: "content"
        value: ["紧急", "重要", "urgent", "critical"]
    actions:
      - type: "notification"
        title: "重要消息提醒"
        message: "收到重要消息：{{content}}"
```

### 2. 规则语法说明

#### 条件类型
- `keyword`: 关键词匹配
- `regex`: 正则表达式匹配
- `talker`: 对话者匹配
- `sender`: 发送者匹配
- `type`: 消息类型匹配

#### 动作类型
- `reply`: 回复消息
- `forward`: 转发消息
- `notification`: 发送系统通知
- `command`: 执行系统命令
- `http`: 调用 HTTP API

### 3. 更多规则示例

创建 `rules/advanced.yaml`：

```yaml
# rules/advanced.yaml
rules:
  - name: "工作时间自动回复"
    description: "工作时间外的消息自动回复"
    enabled: true
    conditions:
      - type: "time"
        start: "18:00"
        end: "09:00"
        weekdays: [1, 2, 3, 4, 5]  # 周一至周五
    actions:
      - type: "reply"
        content: "现在是非工作时间，我将在工作时间回复您。"

  - name: "群聊@提醒"
    description: "在群聊中被@时回复"
    enabled: true
    conditions:
      - type: "regex"
        field: "content"
        value: "@.*"
      - type: "talker"
        value: ["工作群", "项目群"]  # 只在指定群聊生效
    actions:
      - type: "reply"
        content: "收到@，稍后处理"

  - name: "链接安全检测"
    description: "检测消息中的链接并提醒"
    enabled: true
    conditions:
      - type: "regex"
        field: "content"
        value: "https?://"
    actions:
      - type: "reply"
        content: "检测到链接，请注意安全"
```

---

## 启动服务

### 1. 直接运行

```bash
# 在项目根目录运行
python main.py

# 或者指定配置文件
python main.py --config config.yaml
```

### 2. 使用 systemd 服务（Linux）

创建服务文件 `/etc/systemd/system/wechat-butler.service`：

```ini
[Unit]
Description=WeChat Butler Service
After=network.target

[Service]
Type=simple
User=wechat
WorkingDirectory=/opt/wechat-butler
ExecStart=/usr/bin/python3 /opt/wechat-butler/main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable wechat-butler
sudo systemctl start wechat-butler
sudo systemctl status wechat-butler
```

### 3. 使用 Docker Compose

创建 `docker-compose.yml`：

```yaml
version: '3.8'
services:
  wechat-butler:
    image: wechat-butler:latest
    container_name: wechat-butler
    ports:
      - "8080:8080"
    volumes:
      - ./config:/app/config
      - ./rules:/app/rules
      - ./logs:/app/logs
    restart: unless-stopped
```

启动服务：

```bash
docker-compose up -d
```

---

## 测试验证

### 1. 检查服务状态

```bash
# 检查服务是否运行
curl http://localhost:8080/health

# 预期响应
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime": 3600
}
```

### 2. 查看加载的规则

```bash
curl http://localhost:8080/api/v1/rules

# 预期响应
{
  "rules": [
    {
      "name": "自动问候回复",
      "enabled": true,
      "conditions": [...],
      "actions": [...]
    }
  ]
}
```

### 3. 测试 Webhook 接口

```bash
# 模拟 chatshell-api 发送 webhook
curl -X POST http://localhost:8080/webhook/message \
  -H "Content-Type: application/json" \
  -H "X-Signature: your-signature" \
  -d '{
    "talker": "filehelper",
    "sender": "user123",
    "content": "你好，测试消息",
    "type": 1,
    "timestamp": 1732252800
  }'
```

### 4. 查看日志

```bash
# 查看实时日志
tail -f logs/wechat-butler.log

# 搜索特定消息
grep "处理消息" logs/wechat-butler.log
```

### 5. 测试规则匹配

```bash
# 测试规则匹配（需要启动服务）
curl -X POST http://localhost:8080/api/v1/rules/test \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "talker": "filehelper",
      "sender": "user123",
      "content": "你好"
    }
  }'
```

---

## 常见问题

### Q1: 服务启动失败
**问题**: `python main.py` 报错
**解决**:
```bash
# 检查 Python 版本
python --version

# 安装依赖
pip install -r requirements.txt

# 检查配置文件
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

### Q2: Webhook 签名验证失败
**问题**: chatshell-api 发送的 webhook 被拒绝
**解决**:
1. 检查 config.yaml 中的 `webhook.secret`
2. 确保 chatshell-api 使用相同的密钥
3. 检查请求头中的 `X-Signature`

### Q3: 规则不生效
**问题**: 消息到达但规则未触发
**解决**:
1. 检查规则文件格式是否正确
2. 查看日志中的规则加载信息
3. 使用规则测试接口验证匹配
4. 检查规则是否启用 (`enabled: true`)

### Q4: 无法连接到 wechat-sendmsg
**问题**: 自动回复失败
**解决**:
1. 确认 wechat-sendmsg 服务正在运行
2. 检查 config.yaml 中的 `wechat.sendmsg_url`
3. 测试 wechat-sendmsg 连接:
   ```bash
   curl http://localhost:8000/health
   ```

### Q5: 内存占用过高
**问题**: 服务运行一段时间后内存占用增加
**解决**:
1. 降低日志级别: `logging.level: "WARNING"`
2. 减少规则数量或优化规则
3. 定期重启服务
4. 检查是否有内存泄漏

### Q6: 如何更新规则
**问题**: 修改规则文件后不生效
**解决**:
1. 确保 `config.yaml` 中 `rules.auto_reload: true`
2. 手动触发重载:
   ```bash
   curl -X POST http://localhost:8080/api/v1/rules/reload
   ```
3. 重启服务

---

## 下一步

### 1. 探索更多功能
- 学习[规则编写指南](rule-writing.md)编写复杂规则
- 查看[系统集成指南](api-integration.md)集成其他系统
- 尝试[LLM集成](llm-integration.md)启用智能回复

### 2. 监控和维护
- 设置[系统监控](monitoring.md)
- 配置[日志管理](logging.md)
- 学习[故障排查](troubleshooting.md)

### 3. 参与贡献
- 查看[开发者指南](developer-guide.md)
- 报告问题或提出建议
- 贡献代码或文档

---

## 获取帮助

- **文档**: 查看完整的[文档中心](../README.md)
- **问题反馈**: 提交 [GitHub Issues](https://github.com/xlight/wechat-butler/issues)
- **社区讨论**: 加入 QQ 群或 Discord
- **邮件支持**: support@wechat-butler.com

---

**提示**: 如果在使用过程中遇到任何问题，请先查看日志文件 `logs/wechat-butler.log`，通常可以找到问题的原因和解决方案。

祝您使用愉快！🎉
