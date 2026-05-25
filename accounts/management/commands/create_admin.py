"""
建立最高權限管理員帳號 (lv=9)。

使用方式：
  python manage.py create_admin
  python manage.py create_admin --username admin --name 管理員 --cellphone 0900000000

未提供的欄位會互動式詢問。
"""

import getpass
from django.core.management.base import BaseCommand, CommandError
from accounts.models import Employee, LV_ADMIN


class Command(BaseCommand):
    help = "建立最高權限管理員帳號 (lv=9)"

    def add_arguments(self, parser):
        parser.add_argument("--username", help="登入帳號")
        parser.add_argument("--name", help="姓名")
        parser.add_argument("--cellphone", help="手機號碼")
        parser.add_argument("--password", help="密碼（建議改用互動輸入以避免留在 shell 歷史）")

    def handle(self, *args, **options):
        username = options["username"] or input("登入帳號: ").strip()
        name = options["name"] or input("姓名: ").strip()
        cellphone = options["cellphone"] or input("手機號碼: ").strip()

        if not username or not name or not cellphone:
            raise CommandError("帳號、姓名、手機號碼皆為必填。")

        if Employee.objects.filter(username=username).exists():
            raise CommandError(f"帳號「{username}」已存在。")

        if options["password"]:
            password = options["password"]
        else:
            password = getpass.getpass("密碼: ")
            confirm = getpass.getpass("確認密碼: ")
            if password != confirm:
                raise CommandError("兩次輸入的密碼不一致。")

        if len(password) < 8:
            raise CommandError("密碼至少需要 8 個字元。")

        emp = Employee.objects.create_user(
            username=username,
            password=password,
            name=name,
            cellphone=cellphone,
            lv=LV_ADMIN,
        )

        self.stdout.write(self.style.SUCCESS(
            f"管理員帳號建立成功：{emp.username}（{emp.name}），權限等級：{emp.get_lv_display()}"
        ))
