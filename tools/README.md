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

## 启动方式

```bash
# 自动发现 tools/ 目录（默认行为）
python -m mcp_toolbox

# 或显式指定模块
python -m mcp_toolbox --modules tools.my_tools
```
