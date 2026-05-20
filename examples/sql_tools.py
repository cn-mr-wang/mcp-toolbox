"""SQL 工具示例 —— 展示两种描述写法 + 命名连接 + 外部 SQL 文件。"""

from mcp_toolbox.core.decorators import toolbox
from mcp_toolbox.core.types import ToolType


# ── 写法一：docstring 提取描述 ─────────────────────────────────────

@toolbox.tool(
    name="query_users",
    type=ToolType.SQL,
    connection="my_db",  # 命名连接，由 config.yaml 的 sql_connections 配置
    query="SELECT * FROM users WHERE age > {min_age} LIMIT {limit}",
)
def query_users(min_age: int = 18, limit: int = 10) -> list:
    """按年龄查询用户。

    Args:
        min_age: 最小年龄
        limit: 返回行数上限
    """
    pass


# ── 写法二：装饰器显式传入 description + param_descriptions ─────────

@toolbox.tool(
    name="count_records",
    type=ToolType.SQL,
    connection="my_db",
    query="SELECT COUNT(*) as count FROM {table}",
    description="统计表中的记录数",
    param_descriptions={"table": "表名"},
)
def count_records(table: str) -> dict:
    pass


@toolbox.tool(
    name="search_by_name",
    type=ToolType.SQL,
    connection="my_db",
    query="SELECT * FROM users WHERE name LIKE '%' || {name} || '%' LIMIT 20",
    description="按姓名模糊搜索用户",
    param_descriptions={"name": "要搜索的姓名关键字"},
)
def search_by_name(name: str) -> list:
    pass


# ── 写法三：从外部 .sql 文件加载查询（适合复杂 SQL） ────────────────

@toolbox.tool(
    name="user_report",
    type=ToolType.SQL,
    connection="my_db",
    query_file="sql/user_report.sql",  # 相对于本文件所在目录
    description="生成用户统计报表",
    param_descriptions={"start_date": "开始日期 YYYY-MM-DD", "end_date": "结束日期 YYYY-MM-DD"},
)
def user_report(start_date: str, end_date: str) -> dict:
    pass
