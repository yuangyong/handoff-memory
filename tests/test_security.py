import unittest

from handoff_memory.security import (
    PersonalInfoFinding,
    SecretFinding,
    find_personal_information,
    find_secrets,
)


class PersonalInformationDetectionTests(unittest.TestCase):
    def test_reports_only_personal_information_type_and_line_number(self) -> None:
        email = "alice@example.com"
        phone = "13800138000"
        identity = "1101051949" + "1231002X"
        content = f"联系邮箱：{email}\n手机号：{phone}\n身份证：{identity}\n"

        findings = find_personal_information(content)

        self.assertEqual(
            findings,
            [
                PersonalInfoFinding(kind="邮箱地址", line=1),
                PersonalInfoFinding(kind="中国大陆手机号", line=2),
                PersonalInfoFinding(kind="中国大陆身份证号", line=3),
            ],
        )
        rendered = repr(findings)
        self.assertNotIn(email, rendered)
        self.assertNotIn(phone, rendered)
        self.assertNotIn(identity, rendered)

    def test_deduplicates_same_personal_information_type_on_one_line(self) -> None:
        content = "收件人：alice@example.com、bob@example.org"

        self.assertEqual(
            find_personal_information(content),
            [PersonalInfoFinding(kind="邮箱地址", line=1)],
        )

    def test_rejects_invalid_or_embedded_personal_information_candidates(self) -> None:
        invalid_checksum = "1101051949" + "12310021"
        invalid_date = "1101051999" + "0230001X"
        content = (
            "not-an-email@\n"
            "编号 9138001380007 不应截取中间手机号\n"
            f"校验位错误：{invalid_checksum}\n"
            f"日期错误：{invalid_date}\n"
        )

        self.assertEqual(find_personal_information(content), [])

    def test_personal_information_scan_does_not_change_default_secret_scan(self) -> None:
        personal_information = "alice@example.com\n13800138000\n"
        secret = "api_key=abcdefghijklmnopqrstuvwxyz123456"

        self.assertEqual(find_secrets(personal_information), [])
        self.assertEqual(find_personal_information(secret), [])
        self.assertEqual(
            find_secrets(secret),
            [SecretFinding(kind="疑似密钥赋值", line=1)],
        )


if __name__ == "__main__":
    unittest.main()
