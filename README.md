# MCP Toolbox

> 通用 MCP 工具箱框架 —— 只需编写核心业务逻辑，即可发布 MCP 工具。

[English](#english) | 中文

## 功能特性

- **多语言工具** — Python、Shell、Java、SQL 四种工具类型，一行装饰器注册
- **Web 仪表盘** — 内置 FastAPI 管理界面，查看工具列表、调用日志、在线测试
- **透明日志** — 每次调用自动记录入参、出参、耗时、状态、错误分类
- **访问控制** — Token 权限管理，为不同 MCP 客户端分配可用工具范围
- **MCP 标准协议** — 基于 FastMCP，可接入 Claude Code 等任意 MCP 客户端
- **统一异常处理** — 错误自动分类（超时/连接/权限/参数等），友好提示
- **外部文件加载** — SQL 和 Shell 工具支持从外部文件加载命令/查询
- **中英文界面** — Web UI 支持中英文切换，明暗主题（亮/暗/跟随系统）
- **零配置启动** — 合理默认值，开箱即用

## 快速开始

### 安装

```bash
git clone https://github.com/cn-mr-wang/mcp-toolbox.git
cd mcp-toolbox
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

数据库扩展（可选）：

```bash
pip install -e ".[postgres]"   # PostgreSQL
pip install -e ".[mysql]"      # MySQL
pip install -e ".[all-db]"     # 全部
```

### 定义工具

在 `tools/` 目录下创建 `.py` 文件：

```python
# tools/my_tools.py
from mcp_toolbox.core.decorators import toolbox
from mcp_toolbox.core.types import ToolType

# 写法一：docstring 提取描述（推荐）
@toolbox.tool(name="greet", type=ToolType.PYTHON)
def greet(name: str, greeting: str = "你好") -> str:
    """向某人打招呼。

    Args:
        name: 人名
        greeting: 问候语
    """
    return f"{greeting}, {name}!"

# 写法二：装饰器显式传入描述
@toolbox.tool(
    name="add",
    type=ToolType.PYTHON,
    description="两数相加",
    param_descriptions={"a": "第一个数", "b": "第二个数"},
)
def add(a: int, b: int) -> int:
    return a + b
```

### 工具依赖

如果你的工具需要第三方库，在 `tools/` 目录下创建 `requirements.txt`：

```
# tools/requirements.txt
pandas>=2.0
requests
beautifulsoup4
```

服务启动时会自动检测并安装缺失的依赖，已安装的包会跳过。

### 启动服务

```bash
# 启动 MCP 服务器 + Web 仪表盘
python -m mcp_toolbox

# 仅启动 Web 仪表盘（不启动 MCP）
python -m mcp_toolbox --no-mcp

# 指定自定义工具模块
python -m mcp_toolbox --modules tools.my_tools tools.http_utils

# 开发调试：加载示例工具
python -m mcp_toolbox --load-examples --no-mcp
```

启动后访问 Web 仪表盘：http://127.0.0.1:8080

### 后台运行

```bash
# macOS / Linux
./scripts/start.sh                    # 后台启动（默认仅 Web 模式）
./scripts/start.sh --no-mcp           # 后台启动（仅 Web 模式）
./scripts/shutdown.sh                 # 停止服务

# Windows
scripts\start.bat                     # 后台启动
scripts\shutdown.bat                  # 停止服务
```

## 工具类型

### Python 工具

直接执行 Python 函数，支持同步和异步：

```python
@toolbox.tool(name="md5_hash", type=ToolType.PYTHON)
def md5_hash(text: str) -> str:
    """计算 MD5 哈希值。"""
    import hashlib
    return hashlib.md5(text.encode()).hexdigest()
```

### Shell 工具

通过 `subprocess` 执行命令，参数自动注入模板：

```python
@toolbox.tool(
    name="list_files",
    type=ToolType.SHELL,
    command="ls -la {path}",
    timeout=10,
)
def list_files(path: str = ".") -> str:
    """列出目录文件。"""
    pass
```

长命令可用 `command_file` 从外部脚本加载：

```python
@toolbox.tool(
    name="backup_db",
    type=ToolType.SHELL,
    command_file="scripts/backup_db.sh",
    timeout=300,
    description="备份数据库",
    param_descriptions={"db_name": "数据库名", "output_dir": "备份目录"},
)
def backup_db(db_name: str, output_dir: str = "/tmp") -> str:
    pass
```

### Java 工具

支持 JAR 模式和源码编译模式，三种参数传递方式：

```python
# JAR 模式（默认 JSON 传参）
@toolbox.tool(
    name="java_hash",
    type=ToolType.JAVA,
    jar_path="./tools/HashTool.jar",
)
def java_hash(text: str) -> str:
    """Java 计算哈希。"""
    pass

# args 模式 —— 一个 JAR 多个方法，通过参数分发
@toolbox.tool(
    name="java_toolkit",
    type=ToolType.JAVA,
    jar_path="./tools/Toolkit.jar",
    java_args_mode="args",  # 传 --key value 格式
)
def java_toolkit(action: str, table: str, limit: int = 100) -> dict:
    """Java 多功能工具。"""
    pass
# 命令行：java -jar Toolkit.jar --action query --table users --limit 100
```

**参数传递模式**（`java_args_mode`）：

| 模式 | 说明 | 命令行示例 |
|------|------|-----------|
| `json` | JSON 字符串（默认） | `java -jar tool.jar '{"action":"query"}'` |
| `args` | `--key value` 标志 | `java -jar tool.jar --action query` |
| `raw` | 仅传值（按参数顺序） | `java -jar tool.jar query users` |

### SQL 工具

支持 SQLite、PostgreSQL、MySQL，参数化查询防止 SQL 注入：

```python
@toolbox.tool(
    name="query_users",
    type=ToolType.SQL,
    connection="my_db",    # 命名连接，由 config.yaml 配置
    query="SELECT * FROM users WHERE age > {min_age} LIMIT {limit}",
)
def query_users(min_age: int = 18, limit: int = 10) -> list:
    """查询用户。"""
    pass
```

长 SQL 可用 `query_file` 从外部文件加载：

```python
@toolbox.tool(
    name="user_report",
    type=ToolType.SQL,
    connection="my_db",
    query_file="sql/user_report.sql",
    description="生成用户统计报表",
    param_descriptions={"start_date": "开始日期", "end_date": "结束日期"},
)
def user_report(start_date: str, end_date: str) -> dict:
    pass
```

#### 连接配置

```yaml
# config.yaml
sql_connections:
  my_db: "sqlite:///dev.db"
  # my_db: "postgresql://user:pass@host:5432/db"
```

## Web 仪表盘

启动后访问 http://127.0.0.1:8080

| 页面 | 路径 | 功能 |
|------|------|------|
| 仪表盘 | `/` | 统计概览、按工具统计、已注册工具（支持搜索） |
| 工具列表 | `/tools` | 所有工具，按类型筛选 |
| 工具详情 | `/tools/{name}` | 参数 Schema、源码/配置、在线测试、近期调用 |
| 调用日志 | `/logs` | 全量日志，按工具/状态/错误类型筛选 |
| 访问控制 | `/access` | 创建/编辑/删除 Token，配置工具权限 |

**特性**：
- 中英文切换（右上角）
- 明暗主题切换（亮/暗/跟随系统）
- 工具详情页支持在线测试，不计入调用统计
- 错误自动分类：超时、连接、权限、未找到、参数、执行、配置、未知

## 访问控制

每个 MCP 客户端可分配独立 Token，控制其可调用的工具范围。

### 创建 Token

1. Web UI `/access` 页面创建（需 Admin Token 登录）
2. 或通过 REST API 创建

### 使用 Token

```json
{
  "mcpServers": {
    "mcp-toolbox": {
      "command": "python",
      "args": ["-m", "mcp_toolbox", "--no-web", "--token", "your-token"],
      "cwd": "/path/to/mcp_toolbox"
    }
  }
}
```

或使用环境变量：

```json
{
  "mcpServers": {
    "mcp-toolbox": {
      "command": "python",
      "args": ["-m", "mcp_toolbox", "--no-web"],
      "env": { "MCP_TOOLBOX_TOKEN": "your-token" },
      "cwd": "/path/to/mcp_toolbox"
    }
  }
}
```

### Admin Token

保护 Web UI 的访问控制页面：

```bash
python -m mcp_toolbox --admin-token "your-admin-token"
# 或环境变量
export MCP_TOOLBOX_ADMIN_TOKEN="your-admin-token"
# 或 config.yaml
admin_token: "your-admin-token"
```

## 接入 Claude Code

### stdio 模式（默认）

在 Claude Code 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "mcp-toolbox": {
      "command": "python",
      "args": ["-m", "mcp_toolbox", "--no-web"],
      "cwd": "/path/to/mcp_toolbox"
    }
  }
}
```

### HTTP 模式

启动时使用 `--transport http`，MCP 端点挂载到 Web 服务器的 `/mcp` 路径：

```bash
python -m mcp_toolbox --transport http
```

客户端配置：

```json
{
  "mcpServers": {
    "mcp-toolbox": {
      "type": "http",
      "url": "http://127.0.0.1:8080/mcp"
    }
  }
}
```

HTTP 模式下 Web 仪表盘和 MCP 端点共用同一端口，适合需要远程访问或多客户端共享的场景。

## 命令行参数

```
python -m mcp_toolbox [OPTIONS]

选项:
  --config PATH       配置文件路径（默认 config.yaml）
  --modules MOD ...   指定工具模块（如 tools.my_tools）
  --tools-dir DIR     工具目录（默认 tools，支持相对/绝对路径）
  --web-host HOST     Web 服务地址（默认 127.0.0.1）
  --web-port PORT     Web 服务端口（默认 8080）
  --db-path PATH      日志数据库路径（默认 mcp_toolbox.db）
  --retention-days N  日志保留天数（最少1天，默认7天）
  --no-web            不启动 Web 仪表盘
  --no-mcp            不启动 MCP 服务器（仅 Web 模式）
  --transport MODE    MCP 传输模式：stdio（默认）或 http
  --load-examples     加载示例工具（开发调试用）
  --admin-token TOKEN 管理员 Token（保护访问控制页面）
  --token TOKEN       MCP 服务器 Token（按权限过滤可用工具）
```

## 配置文件

`config.yaml`（可选，全部有默认值）：

```yaml
server:
  host: "127.0.0.1"
  port: 8080

mcp:
  transport: stdio

database:
  log_path: "mcp_toolbox.db"
  retention_days: 7

tools:
  dir: "tools"
  # modules:
  #   - tools.my_tools
  auto_discover: true
  load_examples: false

# admin_token: "your-admin-token"

# sql_connections:
#   my_db: "sqlite:///data.db"
```

## 项目结构

```
mcp_toolbox/
├── pyproject.toml
├── config.yaml
├── scripts/                   # 启停脚本（macOS/Linux/Windows）
├── tools/                     # 你的自定义工具放这里
├── examples/                  # 框架示例（参考用，生产不加载）
└── mcp_toolbox/               # 框架代码
    ├── __main__.py            # 入口
    ├── config.py              # YAML 配置加载
    ├── core/
    │   ├── types.py           # ToolType、ToolEntry、ToolResult
    │   ├── schema.py          # 类型注解 → JSON Schema
    │   ├── registry.py        # 工具注册表
    │   ├── decorators.py      # @toolbox.tool() 装饰器
    │   ├── errors.py          # 统一异常处理
    │   └── token.py           # Token 权限管理
    ├── executors/
    │   ├── python_executor.py
    │   ├── shell_executor.py
    │   ├── java_executor.py
    │   └── sql_executor.py
    ├── logging/
    │   ├── models.py          # SQLite 表结构
    │   ├── store.py           # 日志读写
    │   └── middleware.py      # 透明日志中间件
    ├── server/
    │   └── mcp_server.py      # FastMCP 集成
    └── web/
        ├── app.py             # FastAPI 应用
        ├── routes_api.py      # REST API
        ├── routes_pages.py    # HTML 页面
        ├── static/            # 静态资源（favicon）
        └── templates/         # Jinja2 模板
```

## 依赖

| 包 | 用途 |
|---|------|
| `mcp` | MCP 协议 SDK |
| `fastapi` | Web 框架 |
| `uvicorn` | ASGI 服务器 |
| `jinja2` | HTML 模板引擎 |
| `pydantic` | 数据验证 |
| `pyyaml` | YAML 配置解析 |

## 许可证

[MIT](LICENSE)

---

## English

> Generic MCP tool framework — write your core business logic, publish as MCP tools instantly.

### Features

- **Multi-language tools** — Python, Shell, Java, SQL with decorator-based registration
- **Web dashboard** — Built-in FastAPI UI with tool list, call logs, and online testing
- **Transparent logging** — Auto-records params, output, duration, status, error category
- **Access control** — Token-based permissions, assign allowed tools per MCP client
- **MCP protocol** — Built on FastMCP, works with Claude Code and any MCP client
- **Unified error handling** — Auto-classifies errors (timeout/connection/permission/etc.)
- **External file loading** — SQL and Shell tools support loading from external files
- **i18n & themes** — Chinese/English UI, light/dark/system theme
- **Zero-config** — Sensible defaults, works out of the box

### Quick Start

```bash
git clone https://github.com/cn-mr-wang/mcp-toolbox.git
cd mcp-toolbox
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Define tools in tools/*.py, then:
python -m mcp_toolbox
```

### Tool Dependencies

If your tools need third-party libraries, create `requirements.txt` in the `tools/` directory:

```
# tools/requirements.txt
pandas>=2.0
requests
beautifulsoup4
```

Missing dependencies are auto-installed on startup. Already installed packages are skipped.

### Tool Types

| Type | Description | Example |
|------|-------------|---------|
| `PYTHON` | Execute Python functions | `@toolbox.tool(type=ToolType.PYTHON)` |
| `SHELL` | Run shell commands via subprocess | `@toolbox.tool(type=ToolType.SHELL, command="ls {path}")` |
| `JAVA` | Run JAR or compile Java source | `@toolbox.tool(type=ToolType.JAVA, jar_path="tool.jar")` |
| `SQL` | Parameterized queries (SQLite/PG/MySQL) | `@toolbox.tool(type=ToolType.SQL, connection="my_db", query="...")` |

### Claude Code Integration

**stdio mode** (default):

```json
{
  "mcpServers": {
    "mcp-toolbox": {
      "command": "python",
      "args": ["-m", "mcp_toolbox", "--no-web"],
      "cwd": "/path/to/mcp_toolbox"
    }
  }
}
```

**HTTP mode** — start with `--transport http`, MCP endpoint at `/mcp`:

```json
{
  "mcpServers": {
    "mcp-toolbox": {
      "type": "http",
      "url": "http://127.0.0.1:8080/mcp"
    }
  }
}
```

### License

[MIT](LICENSE)
