"""Java 工具示例 —— 展示多种描述写法和参数传递模式。

注意：需要先安装 Java，并创建对应的 JAR 或源文件。
"""

from mcp_toolbox.core.decorators import toolbox
from mcp_toolbox.core.types import ToolType


# ── 写法一：docstring 提取描述 ─────────────────────────────────────

@toolbox.tool(
    name="java_json_parse",
    type=ToolType.JAVA,
    jar_path="./tools/JsonTool.jar",
    timeout=30,
)
def java_json_parse(text: str) -> str:
    """使用 Java 解析 JSON（更健壮的解析器）。

    Args:
        text: 要解析的 JSON 字符串
    """
    pass


# ── 写法二：装饰器显式传入 description + param_descriptions ─────────

@toolbox.tool(
    name="java_hash",
    type=ToolType.JAVA,
    source_path="./tools/src/HashTool.java",
    main_class="HashTool",
    classpath="./tools/src",
    timeout=30,
    description="使用 Java 计算哈希值",
    param_descriptions={
        "algorithm": "哈希算法（MD5、SHA-256 等）",
        "text": "要哈希的文本",
    },
)
def java_hash(algorithm: str, text: str) -> str:
    pass


# ── 写法三：args 模式 —— 传 --key value 参数 ───────────────────────
# Java 端用参数解析库（如 picocli、commons-cli）接收
# 命令行：java -jar tools.jar --action query --table users --limit 10

@toolbox.tool(
    name="java_toolkit",
    type=ToolType.JAVA,
    jar_path="./tools/Toolkit.jar",
    java_args_mode="args",  # 传 --key value 格式
    timeout=60,
    description="Java 多功能工具（支持多种操作）",
    param_descriptions={
        "action": "操作类型（query/export/import）",
        "table": "目标表名",
        "limit": "返回行数上限",
    },
)
def java_toolkit(action: str, table: str, limit: int = 100) -> dict:
    pass


# ── 写法四：raw 模式 —— 只传值，不传 key ───────────────────────────
# 适合参数顺序固定的简单工具
# 命令行：java -jar tools.jar SHA-256 "hello world"

@toolbox.tool(
    name="java_hash_simple",
    type=ToolType.JAVA,
    jar_path="./tools/HashTool.jar",
    java_args_mode="raw",  # 只传值，按参数定义顺序
    timeout=30,
    description="Java 哈希（简单参数模式）",
    param_descriptions={
        "algorithm": "哈希算法",
        "text": "要哈希的文本",
    },
)
def java_hash_simple(algorithm: str, text: str) -> str:
    pass
