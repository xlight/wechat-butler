# WeChat Butler API 参考手册

## 文档信息

- **版本**: v1.0.0
- **创建日期**: 2025-11-22
- **最后更新**: 2025-11-22
- **API 版本**: v1
- **基础路径**: `/api/v1`

---

## 📋 目录

- [概述](#概述)
- [认证授权](#认证授权)
- [API 端点](#api-端点)
- [数据模型](#数据模型)
- [错误处理](#错误处理)
- [速率限制](#速率限制)
- [示例代码](#示例代码)

---

## 概述

WeChat Butler 提供完整的 RESTful API，用于管理规则、执行命令、查询状态等操作。所有 API 都遵循 REST 设计原则，使用 JSON 作为数据交换格式。

### 基础信息

- **基础 URL**: `http://localhost:8080` (默认)
- **API 版本**: `v1`
- **内容类型**: `application/json`
- **字符编码**: `UTF-8`

### 快速开始

```bash
# 检查服务状态
curl http://localhost:8080/api/v1/health

# 获取规则列表（需要认证）
curl -H "X-API-Key: your-api-key" http://localhost:8080/api/v1/rules
```

---

## 认证授权

### API 密钥认证

大多数 API 端点需要 API 密钥认证。在请求头中提供 `X-API-Key`：

```http
GET /api/v1/rules
X-API-Key: your-api-key-here
```

### 权限说明

不同的 API 密钥可能具有不同的权限级别：

| 权限 | 说明 | 示例端点 |
|------|------|----------|
| `read` | 只读权限 | `GET /api/v1/rules` |
| `write` | 读写权限 | `POST /api/v1/rules` |
| `admin` | 管理权限 | `PUT /api/v1/config` |

### Webhook 认证

Webhook 端点使用 HMAC-SHA256 签名认证：

```http
POST /webhook/message
X-Signature: sha256=...
Content-Type: application/json

{"event": "message.new", ...}
```

签名计算方法：
```python
import hmac
import hashlib

secret = "your-webhook-secret"
payload = '{"event": "message.new"}'
signature = hmac.new(
    secret.encode(),
    payload.encode(),
    hashlib.sha256
).hexdigest()
```

---

## API 端点

### 健康检查

#### GET /health

检查服务健康状态。

**无需认证**

**响应示例**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600,
  "timestamp": "2025-11-22T10:30:00Z"
}
```

### 规则管理

#### GET /rules

获取所有规则列表。

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `enabled` | boolean | 否 | 过滤启用状态 |
| `limit` | integer | 否 | 返回数量限制 |
| `offset` | integer | 否 | 偏移量 |

**响应示例**:
```json
{
  "rules": [
    {
      "id": "rule_001",
      "name": "自动问候",
      "enabled": true,
      "priority": 100,
      "conditions": [...],
      "actions": [...],
      "created_at": "2025-11-22T10:00:00Z",
      "updated_at": "2025-11-22T10:00:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

#### POST /rules

创建新规则。

**请求体**:
```json
{
  "name": "新规则",
  "description": "规则描述",
  "enabled": true,
  "priority": 100,
  "conditions": [
    {
      "type": "keyword",
      "field": "content",
      "value": ["你好"],
      "case_sensitive": false
    }
  ],
  "actions": [
    {
      "type": "reply",
      "content": "你好！",
      "delay": 1
    }
  ]
}
```

**响应示例**:
```json
{
  "id": "rule_002",
  "name": "新规则",
  "enabled": true,
  "created_at": "2025-11-22T10:05:00Z"
}
```

#### GET /rules/{id}

获取指定规则的详细信息。

**路径参数**:
- `id`: 规则 ID

**响应示例**:
```json
{
  "id": "rule_001",
  "name": "自动问候",
  "description": "自动回复问候消息",
  "enabled": true,
  "priority": 100,
  "conditions": [...],
  "actions": [...],
  "stats": {
    "matched": 15,
    "executed": 15,
    "last_matched": "2025-11-22T10:00:00Z"
  },
  "created_at": "2025-11-22T09:00:00Z",
  "updated_at": "2025-11-22T10:00:00Z"
}
```

#### PUT /rules/{id}

更新规则。

**路径参数**:
- `id`: 规则 ID

**请求体**: 同 POST /rules

**响应示例**:
```json
{
  "id": "rule_001",
  "updated": true,
  "updated_at": "2025-11-22T10:10:00Z"
}
```

#### DELETE /rules/{id}

删除规则。

**路径参数**:
- `id`: 规则 ID

**响应示例**:
```json
{
  "id": "rule_001",
  "deleted": true
}
```

#### POST /rules/{id}/test

测试规则匹配。

**路径参数**:
- `id`: 规则 ID

**请求体**:
```json
{
  "message": {
    "talker": "filehelper",
    "sender": "user123",
    "content": "你好",
    "type": 1,
    "timestamp": 1732252800
  }
}
```

**响应示例**:
```json
{
  "matched": true,
  "conditions_matched": [
    {
      "type": "keyword",
      "matched": true,
      "details": "匹配关键词：你好"
    }
  ],
  "actions_generated": [
    {
      "type": "reply",
      "content": "你好！",
      "delay": 1
    }
  ]
}
```

#### POST /rules/import

批量导入规则。

**请求体**:
```json
{
  "rules": [
    {
      "name": "规则1",
      "conditions": [...],
      "actions": [...]
    },
    {
      "name": "规则2",
      "conditions": [...],
      "actions": [...]
    }
  ],
  "overwrite": false
}
```

#### GET /rules/export

导出所有规则。

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `format` | string | 否 | 导出格式：`json` 或 `yaml` |

### 命令执行

#### POST /commands/execute

执行命令。

**请求体**:
```json
{
  "command": "send_message",
  "params": {
    "to": "filehelper",
    "content": "测试消息"
  },
  "async": false,
  "timeout": 30
}
```

**可用命令**:
| 命令 | 说明 | 参数 |
|------|------|------|
| `send_message` | 发送微信消息 | `to`, `content`, `type` |
| `execute_script` | 执行脚本 | `script`, `args`, `cwd` |
| `call_http` | 调用 HTTP API | `url`, `method`, `headers`, `body` |
| `system_notify` | 发送系统通知 | `title`, `message`, `level` |

**响应示例**:
```json
{
  "id": "cmd_001",
  "command": "send_message",
  "status": "completed",
  "result": {
    "success": true,
    "message_id": "msg_123",
    "sent_at": "2025-11-22T10:15:00Z"
  },
  "started_at": "2025-11-22T10:15:00Z",
  "completed_at": "2025-11-22T10:15:01Z"
}
```

#### GET /commands

获取命令执行历史。

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `limit` | integer | 否 | 返回数量限制 |
| `offset` | integer | 否 | 偏移量 |
| `status` | string | 否 | 过滤状态 |
| `command` | string | 否 | 过滤命令类型 |

**响应示例**:
```json
{
  "commands": [
    {
      "id": "cmd_001",
      "command": "send_message",
      "status": "completed",
      "params": {...},
      "result": {...},
      "started_at": "2025-11-22T10:15:00Z",
      "completed_at": "2025-11-22T10:15:01Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

#### GET /commands/{id}

获取命令执行详情。

**路径参数**:
- `id`: 命令 ID

#### POST /commands/{id}/cancel

取消正在执行的命令。

**路径参数**:
- `id`: 命令 ID

### 消息管理

#### GET /messages

获取已处理的消息记录。

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `limit` | integer | 否 | 返回数量限制 |
| `offset` | integer | 否 | 偏移量 |
| `talker` | string | 否 | 过滤对话者 |
| `sender` | string | 否 | 过滤发送者 |
| `start_time` | string | 否 | 开始时间 |
| `end_time` | string | 否 | 结束时间 |

**响应示例**:
```json
{
  "messages": [
    {
      "id": "msg_001",
      "talker": "filehelper",
      "sender": "user123",
      "content": "你好",
      "type": 1,
      "timestamp": "2025-11-22T10:00:00Z",
      "processed": true,
      "rules_matched": ["rule_001"],
      "actions_executed": ["reply_001"],
      "processing_time": 50
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

#### GET /messages/{id}

获取消息处理详情。

**路径参数**:
- `id`: 消息 ID

### 系统管理

#### GET /metrics

获取系统性能指标。

**响应示例**:
```json
{
  "system": {
    "uptime": 3600,
    "memory_usage": 52428800,
    "cpu_percent": 2.5,
    "thread_count": 8
  },
  "processing": {
    "messages_total": 150,
    "messages_processed": 150,
    "messages_failed": 2,
    "avg_processing_time": 45.2,
    "rules_total": 10,
    "rules_active": 8
  },
  "performance": {
    "qps": 5.2,
    "response_time_avg": 25.3,
    "response_time_p95": 48.7,
    "error_rate": 0.013
  }
}
```

#### GET /logs

查询系统日志。

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `level` | string | 否 | 日志级别 |
| `module` | string | 否 | 模块名称 |
| `start_time` | string | 否 | 开始时间 |
| `end_time` | string | 否 | 结束时间 |
| `limit` | integer | 否 | 返回数量限制 |

**响应示例**:
```json
{
  "logs": [
    {
      "timestamp": "2025-11-22T10:00:00Z",
      "level": "INFO",
      "module": "rule_engine",
      "message": "规则 rule_001 匹配消息 msg_001",
      "data": {
        "rule": "rule_001",
        "message": "msg_001"
      }
    }
  ],
  "total": 100,
  "limit": 10,
  "offset": 0
}
```

#### GET /config

获取当前配置。

**响应示例**:
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8080,
    "debug": false
  },
  "webhook": {
    "secret": "***",
    "path": "/webhook/message"
  },
  "wechat": {
    "sendmsg_url": "http://localhost:8000"
  },
  "logging": {
    "level": "INFO",
    "file": "./logs/wechat-butler.log"
  }
}
```

#### PUT /config

更新配置（部分更新）。

**请求体**:
```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

**响应示例**:
```json
{
  "updated": true,
  "requires_restart": false,
  "updated_fields": ["logging.level"]
}
```

#### POST /reload

重载配置和规则。

**响应示例**:
```json
{
  "reloaded": true,
  "rules_loaded": 10,
  "config_updated": true
}
```

### 实时事件

#### GET /events

Server-Sent Events (SSE) 事件流。

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `types` | string | 否 | 事件类型过滤，逗号分隔 |

**事件类型**:
- `message.processed`: 消息处理完成
- `rule.matched`: 规则匹配
- `command.executed`: 命令执行完成
- `system.status`: 系统状态更新
- `error.occurred`: 错误发生

**事件格式**:
```
event: message.processed
data: {"id": "msg_001", "status": "success"}

event: rule.matched
data: {"rule": "rule_001", "message": "msg_001"}
```

### Webhook 接口

#### POST /webhook/message

接收 chatshell-api 的 webhook 消息。

**请求头**:
- `X-Signature`: HMAC-SHA256 签名
- `Content-Type`: `application/json`

**请求体**:
```json
{
  "event": "message.new",
  "timestamp": 1732252800,
  "data": {
    "msgId": "123456789",
    "talker": "filehelper",
    "sender": "user123",
    "content": "Hello World",
    "type": 1,
    "createTime": 1732252800,
    "isSend": 0
  }
}
```

**响应**:
- `200 OK`: 接收成功
- `400 Bad Request`: 请求格式错误或签名验证失败
- `500 Internal Server Error`: 服务器内部错误

---

## 数据模型

### 规则 (Rule)

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "enabled": "boolean",
  "priority": "integer",
  "conditions": ["Condition"],
  "actions": ["Action"],
  "stats": {
    "matched": "integer",
    "executed": "integer",
    "last_matched": "string"
  },
  "created_at": "string",
  "updated_at": "string"
}
```

### 条件 (Condition)

```json
{
  "type": "string",  // keyword, regex, sender, talker, type, time, group
  "field": "string", // 仅 keyword, regex 类型需要
  "value": ["string"] | "string",
  "case_sensitive": "boolean",  // 仅 keyword 类型
  "flags": "string",  // 仅 regex 类型
  "operator": "string",  // 仅 group 类型: AND, OR, NOT
  "conditions": ["Condition"]  // 仅 group 类型
}
```

### 动作 (Action)

```json
{
  "type": "string",  // reply, forward, command, http, notification, llm
  "content": "string",  // reply 类型
  "to": "string",  // reply, forward 类型
  "prefix": "string",  // forward 类型
  "command": "string",  // command 类型
  "args": ["string"],  // command 类型
  "url": "string",  // http 类型
  "method": "string",  // http 类型
  "headers": "object",  // http 类型
  "body": "object",  // http 类型
  "title": "string",  // notification 类型
  "message": "string",  // notification 类型
  "provider": "string",  // llm 类型
  "prompt": "string",  // llm 类型
  "delay": "integer",  // 延迟执行（秒）
  "timeout": "integer"  // 超时时间（秒）
}
```

### 消息 (Message)

```json
{
  "id": "string",
  "talker": "string",
  "sender": "string",
  "content": "string",
  "type": "integer",
  "timestamp": "string",
  "processed