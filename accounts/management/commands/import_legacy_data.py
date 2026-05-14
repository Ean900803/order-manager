"""
從舊 PyQt6 系統的 MySQL 資料庫匯入資料到 Django 系統。

使用方式：
  python manage.py import_legacy_data \
      --host 127.0.0.1 --port 3306 \
      --user root --password secret \
      --db inventory_sales

注意：
  - 舊系統密碼為 SHA-256，匯入後需強制使用者重設密碼
    （或改用 --legacy-passwords 保留原始 hash，搭配 legacy auth backend）
  - 執行前請確認 Django migrate 已完成
  - 重複執行是安全的（使用 get_or_create / update_or_create）
"""

import hashlib
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

try:
    import pymysql
except ImportError:
    pymysql = None


class Command(BaseCommand):
    help = "從舊版 MySQL 資料庫匯入 employees/categories/products/customers/orders/order_records"

    def add_arguments(self, parser):
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=3306)
        parser.add_argument("--user", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--db", default="inventory_sales")
        parser.add_argument(
            "--legacy-passwords",
            action="store_true",
            help="保留 SHA-256 hash（需搭配 legacy auth backend）",
        )

    def handle(self, *args, **options):
        if pymysql is None:
            raise CommandError("請先安裝 pymysql: pip install pymysql")

        conn = pymysql.connect(
            host=options["host"],
            port=options["port"],
            user=options["user"],
            password=options["password"],
            database=options["db"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

        try:
            with transaction.atomic():
                self._import_employees(conn, options["legacy_passwords"])
                self._import_categories(conn)
                self._import_products(conn)
                self._import_customers(conn)
                self._import_orders(conn)
                self._import_order_records(conn)
        finally:
            conn.close()

        self.stdout.write(self.style.SUCCESS("✅ 資料匯入完成"))

    # ── Employees ─────────────────────────────────────────────────────────────

    def _import_employees(self, conn, keep_legacy_passwords):
        from accounts.models import Employee

        with conn.cursor() as cur:
            cur.execute("SELECT * FROM employees")
            rows = cur.fetchall()

        count = 0
        for row in rows:
            emp, created = Employee.objects.get_or_create(
                pk=row["id"],
                defaults={
                    "username": row["username"],
                    "name": row["name"],
                    "cellphone": row["cellphone"],
                    "address": row["address"] or "",
                    "lv": row["lv"],
                    "resigned_date": row.get("resigned_date"),
                    "is_active": row.get("resigned_date") is None,
                },
            )
            if created:
                if keep_legacy_passwords:
                    # 直接寫入 SHA-256 hash（需搭配 legacy backend）
                    Employee.objects.filter(pk=emp.pk).update(
                        password=f"sha256$${row['password']}"
                    )
                else:
                    # 設定無效密碼，強制首次登入重設
                    emp.set_unusable_password()
                    emp.save(update_fields=["password"])
                count += 1

        self.stdout.write(f"  員工：匯入 {count} 筆（共 {len(rows)} 筆）")

    # ── Categories ────────────────────────────────────────────────────────────

    def _import_categories(self, conn):
        from catalog.models import Category

        with conn.cursor() as cur:
            cur.execute("SELECT * FROM categories")
            rows = cur.fetchall()

        count = 0
        for row in rows:
            _, created = Category.objects.update_or_create(
                pk=row["id"],
                defaults={
                    "name": row["name"],
                    "deleted_at": row.get("deleted_at"),
                },
            )
            if created:
                count += 1

        self.stdout.write(f"  分類：匯入 {count} 筆（共 {len(rows)} 筆）")

    # ── Products ──────────────────────────────────────────────────────────────

    def _import_products(self, conn):
        from catalog.models import Product, Category

        with conn.cursor() as cur:
            cur.execute("SELECT * FROM products")
            rows = cur.fetchall()

        count = 0
        for row in rows:
            _, created = Product.objects.update_or_create(
                pk=row["id"],
                defaults={
                    "category_id": row["category_id"],
                    "name": row["name"],
                    "description": row.get("description") or "",
                    "price": row["price"],
                    "cost": row["cost"],
                    "created_at": row["created_at"],
                    "deleted_at": row.get("deleted_at"),
                },
            )
            if created:
                count += 1

        self.stdout.write(f"  商品：匯入 {count} 筆（共 {len(rows)} 筆）")

    # ── Customers ─────────────────────────────────────────────────────────────

    def _import_customers(self, conn):
        from customers.models import Customer

        with conn.cursor() as cur:
            cur.execute("SELECT * FROM customers")
            rows = cur.fetchall()

        count = 0
        for row in rows:
            _, created = Customer.objects.update_or_create(
                pk=row["id"],
                defaults={
                    "name": row["name"],
                    "cellphone": row.get("cellphone") or "",
                    "address": row.get("address") or "",
                    "note": row.get("note") or "",
                },
            )
            if created:
                count += 1

        self.stdout.write(f"  客戶：匯入 {count} 筆（共 {len(rows)} 筆）")

    # ── Orders ────────────────────────────────────────────────────────────────

    def _import_orders(self, conn):
        from orders.models import Order

        with conn.cursor() as cur:
            cur.execute("SELECT * FROM orders")
            rows = cur.fetchall()

        count = 0
        for row in rows:
            _, created = Order.objects.update_or_create(
                pk=row["id"],
                defaults={
                    "customer_id": row["customer_id"],
                    "ordered_date": row["ordered_date"],
                    "status": row["status"],
                    "deleted_at": row.get("deleted_at"),
                },
            )
            if created:
                count += 1

        self.stdout.write(f"  訂單：匯入 {count} 筆（共 {len(rows)} 筆）")

    # ── Order Records ─────────────────────────────────────────────────────────

    def _import_order_records(self, conn):
        from orders.models import OrderRecord

        with conn.cursor() as cur:
            cur.execute("SELECT * FROM order_records")
            rows = cur.fetchall()

        count = 0
        for row in rows:
            _, created = OrderRecord.objects.update_or_create(
                pk=row["id"],
                defaults={
                    "order_id": row["order_id"],
                    "product_id": row["product_id"],
                    "quantity": row["quantity"],
                    "price": row["price"],
                    "cost": row["cost"],
                    "discount": row["discount"],
                    "created_at": row["created_at"],
                    "deleted_at": row.get("deleted_at"),
                },
            )
            if created:
                count += 1

        self.stdout.write(f"  訂單明細：匯入 {count} 筆（共 {len(rows)} 筆）")
