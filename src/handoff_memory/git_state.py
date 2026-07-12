"""0.1 兼容门面；新代码请使用 :mod:`handoff_memory.repository_state`。"""

from .repository_state import RepositoryState, read_git_state

GitState = RepositoryState

__all__ = ["GitState", "read_git_state"]
