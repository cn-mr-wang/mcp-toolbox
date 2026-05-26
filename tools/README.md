# 自定义工具目录

在此目录下创建 `.py` 文件或子文件夹，自动被框架加载。

## 目录结构

### 单文件方式

```
tools/
├── my_tools.py
├── http_utils.py
└── db_queries.py
```

### 子文件夹方式

```
tools/
├── calculator/
│   ├── __init__.py      # 必须有，标识为 Python 包
│   ├── main.py          # @toolbox.tool 入口
│   └── utils.py         # 辅助模块，无注解不报错
└── http_client/
    ├── __init__.py
    ├── client.py
    └── helpers.py
```

## 工具定义示例

### 写法一：docstring 提取描述（简洁推荐）

```python
from mcp_toolbox.core.decorators import toolbox
from mcp_toolbox.core.types import ToolType

@toolbox.tool(name="greet", type=ToolType.PYTHON)
def greet(name: str, greeting: str = "你好") -> str:
    """向某人打招呼。

    Args:
        name: 人名
        greeting: 问候语
    """
    return f"{greeting}, {name}!"
```

### 写法二：装饰器显式传入描述

```python
@toolbox.tool(
    name="add",
    type=ToolType.PYTHON,
    description="两数相加",
    param_descriptions={"a": "第一个数", "b": "第二个数"},
)
def add(a: int, b: int) -> int:
    return a + b
```

## 自定义配置

工具可读取 Web UI `/configs` 页面管理的 YAML 配置项。

### Python 工具

通过 `get_config()` 函数获取配置值：

```python
from mcp_toolbox.core.decorators import toolbox
from mcp_toolbox.core.types import ToolType
from mcp_toolbox.core.config_store import get_config

@toolbox.tool(name="send_email", type=ToolType.PYTHON)
def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件。"""
    host = get_config("email_server", "smtp.host")
    port = get_config("email_server", "smtp.port", default=587)
    username = get_config("email_server", "smtp.username")
    password = get_config("email_server", "smtp.password")
    # ...
```

### Shell / SQL / Java 工具

使用 `{config:name.key}` 模板变量，执行时自动替换为配置值：

```python
# Shell 工具 — 命令模板中使用
@toolbox.tool(
    name="call_api",
    type=ToolType.SHELL,
    command='curl -H "Authorization: Bearer {config:api.token}" {config:api.base_url}/{endpoint}',
    timeout=30,
)
def call_api(endpoint: str) -> str:
    """调用外部 API。"""
    pass

# SQL 工具 — 使用 {config:xxx} 获取连接
@toolbox.tool(
    name="query_users",
    type=ToolType.SQL,
    connection="{config:db.connection}",  # 从 /configs 页面读取连接字符串
    query="SELECT * FROM users WHERE status = {status}",
)
def query_users(status: str = "active") -> list:
    """查询用户。"""
    pass

# Java 工具 — JAR 路径支持变量，配置自动注入为系统属性
@toolbox.tool(
    name="java_tool",
    type=ToolType.JAVA,
    jar_path="{config:java.tool_path}/tool.jar",
)
def java_tool(action: str) -> dict:
    """Java 工具。"""
    pass
# Java 程序中通过 System.getProperty("config_java_tool_path") 获取
```

### 配置变量语法

| 语法 | 说明 | 示例 |
|------|------|------|
| `{config:name}` | 获取整个配置（JSON 字符串） | `{config:api}` |
| `{config:name.key}` | 获取嵌套值 | `{config:api.base_url}` |
| `{config:name.key.sub}` | 多层嵌套 | `{config:email.smtp.host}` |

> **注意**：配置变量在参数注入（`{param}`）之前解析，两者可混合使用。

## 启动方式

```bash
# 自动发现 tools/ 目录（默认行为）
python -m mcp_toolbox

# 或显式指定模块
python -m mcp_toolbox --modules tools.my_tools
```
