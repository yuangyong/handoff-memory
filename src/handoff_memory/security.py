"""交接文件的本地敏感信息检测。"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretFinding:
    """疑似敏感信息的位置，不保存或回显原始值。"""

    kind: str
    line: int


_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OpenAI 风格密钥", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub 访问令牌", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("AWS Access Key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    (
        "疑似密钥赋值",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|access[_-]?token|password)\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{16,}"
        ),
    ),
    ("私钥", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
)


def find_secrets(content: str) -> list[SecretFinding]:
    """返回高置信度疑似密钥位置，不返回匹配内容。"""
    findings: list[SecretFinding] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        for kind, pattern in _PATTERNS:
            if pattern.search(line):
                finding = SecretFinding(kind=kind, line=line_number)
                if finding not in findings:
                    findings.append(finding)
    return findings
