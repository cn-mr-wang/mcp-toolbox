"""Python 工具示例 —— 展示两种描述写法。"""

import hashlib
import json

from mcp_toolbox.core.decorators import toolbox
from mcp_toolbox.core.types import ToolType


# ── 写法一：docstring 提取描述（简洁推荐） ──────────────────────────

@toolbox.tool(name="calculate_fibonacci", type=ToolType.PYTHON)
def calculate_fibonacci(n: int) -> list:
    """计算斐波那契数列前 n 项。

    Args:
        n: 要生成的斐波那契数个数
    """
    if n <= 0:
        return []
    if n == 1:
        return [0]
    fib = [0, 1]
    for _ in range(2, n):
        fib.append(fib[-1] + fib[-2])
    return fib[:n]


@toolbox.tool(name="md5_hash", type=ToolType.PYTHON)
def md5_hash(text: str) -> str:
    """计算字符串的 MD5 哈希值。

    Args:
        text: 要哈希的字符串
    """
    return hashlib.md5(text.encode()).hexdigest()


@toolbox.tool(name="word_count", type=ToolType.PYTHON)
def word_count(text: str) -> dict:
    """统计文本的字数、字符数和行数。

    Args:
        text: 要统计的文本
    """
    return {
        "words": len(text.split()),
        "characters": len(text),
        "lines": len(text.splitlines()),
    }


# ── 写法二：装饰器显式传入 description + param_descriptions ─────────

@toolbox.tool(
    name="json_pretty",
    type=ToolType.PYTHON,
    description="格式化 JSON 字符串",
    param_descriptions={
        "text": "要格式化的 JSON 字符串",
        "indent": "缩进空格数",
    },
)
def json_pretty(text: str, indent: int = 2) -> str:
    return json.dumps(json.loads(text), indent=indent, ensure_ascii=False)


@toolbox.tool(
    name="string_reverse",
    type=ToolType.PYTHON,
    description="反转字符串",
    param_descriptions={"text": "要反转的字符串"},
)
def string_reverse(text: str) -> str:
    return text[::-1]
