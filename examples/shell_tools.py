"""Shell 工具示例 —— 展示两种描述写法 + 外部命令文件。"""

from mcp_toolbox.core.decorators import toolbox
from mcp_toolbox.core.types import ToolType


# ── 写法一：docstring 提取描述 ─────────────────────────────────────

@toolbox.tool(
    name="list_files",
    type=ToolType.SHELL,
    command="ls -la {path}",
    timeout=10,
)
def list_files(path: str = ".") -> str:
    """列出目录下的文件。

    Args:
        path: 目录路径
    """
    pass


@toolbox.tool(
    name="git_log",
    type=ToolType.SHELL,
    command="git -C {repo_path} log --oneline -n {count}",
    timeout=10,
)
def git_log(repo_path: str = ".", count: int = 10) -> str:
    """查看最近的 Git 提交记录。

    Args:
        repo_path: Git 仓库路径
        count: 显示的提交数量
    """
    pass


# ── 写法二：装饰器显式传入 description + param_descriptions ─────────

@toolbox.tool(
    name="disk_usage",
    type=ToolType.SHELL,
    command="df -h {path}",
    timeout=10,
    description="查看磁盘使用情况",
    param_descriptions={"path": "挂载点或目录路径"},
)
def disk_usage(path: str = "/") -> str:
    pass


@toolbox.tool(
    name="system_info",
    type=ToolType.SHELL,
    command="uname -a && echo '---' && uptime && echo '---' && free -h 2>/dev/null || vm_stat",
    timeout=10,
    description="获取系统信息（操作系统、运行时间、内存）",
)
def system_info() -> str:
    pass


# ── 写法三：从外部脚本文件加载命令（适合复杂命令） ──────────────────

@toolbox.tool(
    name="backup_db",
    type=ToolType.SHELL,
    command_file="scripts/backup_db.sh",  # 相对于本文件所在目录
    timeout=300,
    description="备份数据库",
    param_descriptions={"db_name": "数据库名", "output_dir": "备份输出目录"},
)
def backup_db(db_name: str, output_dir: str = "/tmp") -> str:
    pass
