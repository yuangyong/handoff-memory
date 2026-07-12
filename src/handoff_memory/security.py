"""交接文件的本地敏感信息检测。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SecretFinding:
    """疑似敏感信息的位置，不保存或回显原始值。"""

    kind: str
    line: int


@dataclass(frozen=True)
class PersonalInfoFinding:
    """疑似个人信息的类型和位置，不保存或回显匹配内容。"""

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

_EMAIL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9._%+-])"
    r"[A-Za-z0-9][A-Za-z0-9._%+-]{0,63}"
    r"@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}"
    r"(?![A-Za-z0-9.-])"
)
_MAINLAND_MOBILE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?86[ -]?)?1[3-9]\d{9}(?!\d)"
)
_MAINLAND_ID_PATTERN = re.compile(r"(?<!\d)\d{17}[\dXx](?![\dXx])")
_MAINLAND_ID_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_MAINLAND_ID_CHECK_CODES = "10X98765432"


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


def find_personal_information(content: str) -> list[PersonalInfoFinding]:
    """可选扫描基础个人信息，仅返回类型与行号，不返回匹配内容。"""
    findings: list[PersonalInfoFinding] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        kinds: list[str] = []
        if _EMAIL_PATTERN.search(line):
            kinds.append("邮箱地址")
        if _MAINLAND_MOBILE_PATTERN.search(line):
            kinds.append("中国大陆手机号")
        if any(
            _is_valid_mainland_id(match.group(0))
            for match in _MAINLAND_ID_PATTERN.finditer(line)
        ):
            kinds.append("中国大陆身份证号")
        findings.extend(
            PersonalInfoFinding(kind=kind, line=line_number) for kind in kinds
        )
    return findings


def _is_valid_mainland_id(candidate: str) -> bool:
    normalized = candidate.upper()
    if normalized[0] == "0" or normalized[:6] == "000000":
        return False
    if normalized[14:17] == "000":
        return False
    try:
        birthday = date.fromisoformat(
            f"{normalized[6:10]}-{normalized[10:12]}-{normalized[12:14]}"
        )
    except ValueError:
        return False
    if birthday > date.today():
        return False

    checksum = sum(
        int(character) * weight
        for character, weight in zip(normalized[:17], _MAINLAND_ID_WEIGHTS)
    )
    return normalized[-1] == _MAINLAND_ID_CHECK_CODES[checksum % 11]
