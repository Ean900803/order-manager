"""
產生示範資料。預設輸出成 CSV 檔；帶 --to-db 則直接用 ORM 寫入資料庫。

CSV 搭配流程：
  1. python manage.py migrate          # 先用 migration 建好資料表
  2. python manage.py seed_demo        # 產生 CSV 到 seed_csv/
  3. 用資料庫管理工具把各 CSV 匯入對應資料表

用法：
  python manage.py seed_demo                       # 產 CSV（預設：5 員工 / 40 商品 / 40 客戶 / 100 訂單）
  python manage.py seed_demo --out path/to/dir     # 指定輸出目錄（預設 seed_csv）
  python manage.py seed_demo --orders 200 --customers 80
  python manage.py seed_demo --null "\\N"          # NULL 改輸出 \\N（給 MySQL LOAD DATA 用）
  python manage.py seed_demo --to-db               # 不產 CSV，直接寫入資料庫
  python manage.py seed_demo --to-db --clean       # 先清空（保留 admin）再寫入資料庫

說明：
  - 每張資料表輸出一支 CSV，檔名前綴數字即匯入順序（01_、02_...），對應資料表名為去掉前綴的部分。
  - CSV 含標頭列，欄位名稱對齊 Django migration 建出的資料表。
  - 含外鍵的欄位以 `_id` 結尾，值為對應 CSV 內的 id。
  - 時間欄位以 UTC 輸出（settings.USE_TZ=True，Django 即以 UTC 存入 MySQL）。
  - NULL 預設輸出為空字串（給 DBeaver 等 GUI 匯入，需勾選空字串轉 NULL）；用 LOAD DATA 改帶 --null "\\N"。
"""
import csv
import os
import random
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Employee, LV_EMPLOYEE, LV_SALES, LV_MANAGER, LV_ADMIN


CATEGORIES = ["飲料", "零食", "泡麵", "罐頭", "冷凍", "日用品", "文具", "酒類"]
UNITS = ["個", "瓶", "罐", "包", "盒", "箱", "打", "組"]

# (分類名, [商品名 ...])
PRODUCTS = {
    "飲料": ["可樂", "雪碧", "綠茶", "烏龍茶", "豆漿", "牛奶", "礦泉水", "運動飲料"],
    "零食": ["洋芋片", "巧克力", "餅乾", "口香糖", "魷魚絲", "蝦味先"],
    "泡麵": ["科學麵", "統一麵", "維力炸醬麵", "韓國辛拉麵"],
    "罐頭": ["鮪魚罐頭", "肉醬罐頭", "玉米罐頭"],
    "冷凍": ["水餃", "燒賣", "雞塊"],
    "日用品": ["衛生紙", "牙膏", "洗髮精", "肥皂"],
    "文具": ["原子筆", "筆記本", "便條紙"],
    "酒類": ["啤酒", "高粱"],
}

CUSTOMER_SURNAMES = ["王", "陳", "林", "李", "張", "黃", "吳", "劉", "蔡", "楊"]
CUSTOMER_GIVENNAMES = ["小明", "美玲", "志強", "雅婷", "建宏", "麗華", "俊傑", "靜怡", "宏志", "佩珊"]


class Command(BaseCommand):
    help = "產生示範資料並輸出成 CSV 檔（不寫入資料庫）"

    def add_arguments(self, parser):
        parser.add_argument("--out", default="seed_csv", help="CSV 輸出目錄（預設 seed_csv）")
        parser.add_argument("--orders", type=int, default=100)
        parser.add_argument("--customers", type=int, default=40)
        parser.add_argument("--null", default="", help="NULL 的輸出字串（預設空字串，給 DBeaver 等 GUI 匯入；用 LOAD DATA 改帶 --null \"\\N\"）")
        parser.add_argument("--to-db", action="store_true", help="直接用 ORM 寫入資料庫（不產 CSV）")
        parser.add_argument("--clean", action="store_true", help="搭配 --to-db：先清空舊資料（保留 admin）後重建")

    def handle(self, *args, **opts):
        random.seed(42)
        if opts["to_db"]:
            self._seed_to_db(opts)
            return
        out_dir = opts["out"]
        self.null = opts["null"]
        self._seq = 0  # 檔名前綴序號 = 匯入順序
        os.makedirs(out_dir, exist_ok=True)

        base_dt = timezone.make_aware(datetime(2026, 5, 25, 9, 0, 0))

        # ---- 員工 accounts_employee ----
        # 欄位：id, password, last_login, username, name, cellphone, address, lv, resigned_date
        employees = []  # (id, lv)
        emp_rows = []
        admin_pw = make_password("admin12345")
        staff_pw = make_password("staff12345")
        emp_rows.append([1, admin_pw, None, "admin", "管理員", "0900000000", "", LV_ADMIN, None])
        employees.append((1, LV_ADMIN))
        emp_levels = [(LV_SALES, "業務"), (LV_SALES, "業務"), (LV_MANAGER, "主管"),
                      (LV_EMPLOYEE, "員工"), (LV_EMPLOYEE, "員工")]
        for i, (lv, role) in enumerate(emp_levels, 1):
            eid = i + 1
            name = f"{random.choice(CUSTOMER_SURNAMES)}{role}{i}"
            cell = f"09{random.randint(10000000, 99999999)}"
            emp_rows.append([eid, staff_pw, None, f"staff{i}", name, cell, "", lv, None])
            employees.append((eid, lv))
        emp_ids = [e[0] for e in employees]
        self._write(out_dir, "employees",
                    ["id", "password", "last_login", "username", "name",
                     "cellphone", "address", "lv", "resigned_date"], emp_rows)

        # ---- 單位 catalog_unit ----
        # 欄位：id, name
        unit_id = {name: i for i, name in enumerate(UNITS, 1)}
        unit_rows = [[uid, name] for name, uid in unit_id.items()]
        self._write(out_dir, "units", ["id", "name"], unit_rows)

        # ---- 分類 catalog_category ----
        # 欄位：id, name, deleted_at, deleted_by_id
        cat_id = {name: i for i, name in enumerate(CATEGORIES, 1)}
        cat_rows = [[cid, name, None, None] for name, cid in cat_id.items()]
        self._write(out_dir, "categories",
                    ["id", "name", "deleted_at", "deleted_by_id"], cat_rows)

        # ---- 商品 catalog_product + 商品單位定價 catalog_productunit ----
        # product 欄位：id, name, description, created_at, deleted_at,
        #               category_id, base_unit_id, created_by_id, deleted_by_id
        # productunit 欄位：id, conversion_rate, price, cost, status, created_at,
        #                   created_by_id, product_id, unit_id
        product_rows = []
        pu_rows = []
        # product_id -> list of (pu_id, unit_id, price, cost, conversion_rate)
        product_units = {}
        base_cost = {}  # product_id -> 基準單位成本
        base_unit_of = {}  # product_id -> base unit_id
        pid = 0
        puid = 0
        created = self._fmt_dt(base_dt)
        for cat_name, names in PRODUCTS.items():
            for name in names:
                pid += 1
                base = random.choice([unit_id["個"], unit_id["瓶"], unit_id["罐"],
                                      unit_id["包"], unit_id["盒"]])
                price = Decimal(random.randint(15, 200))
                cost = (price * Decimal("0.6")).quantize(Decimal("0.01"))
                product_rows.append([pid, name, "", created, None,
                                     cat_id[cat_name], base, 1, None])
                base_unit_of[pid] = base
                base_cost[pid] = cost
                product_units[pid] = []

                puid += 1
                pu_rows.append([puid, 1, price, cost, "active", created, 1, pid, base])
                product_units[pid].append((puid, base, price, cost, 1))

                # 50% 機率加箱單位
                if random.random() < 0.5:
                    rate = random.choice([6, 12, 24])
                    bprice = price * rate * Decimal("0.9")
                    bcost = cost * rate * Decimal("0.95")
                    puid += 1
                    pu_rows.append([puid, rate, bprice, bcost, "active", created,
                                    1, pid, unit_id["箱"]])
                    product_units[pid].append((puid, unit_id["箱"], bprice, bcost, rate))
        product_ids = list(range(1, pid + 1))
        self._write(out_dir, "products",
                    ["id", "name", "description", "created_at", "deleted_at",
                     "category_id", "base_unit_id", "created_by_id", "deleted_by_id"],
                    product_rows)
        self._write(out_dir, "product_unit",
                    ["id", "conversion_rate", "price", "cost", "status", "created_at",
                     "created_by_id", "product_id", "unit_id"], pu_rows)

        # ---- 客戶 customers_customer ----
        # 欄位：id, name, cellphone, address, note
        cust_rows = []
        for i in range(opts["customers"]):
            name = f"{random.choice(CUSTOMER_SURNAMES)}{random.choice(CUSTOMER_GIVENNAMES)}"
            cust_rows.append([
                i + 1, f"{name}{i:02d}",
                f"09{random.randint(10000000, 99999999)}",
                f"台北市信義區范例路{random.randint(1, 200)}號", "",
            ])
        customer_ids = [r[0] for r in cust_rows]
        self._write(out_dir, "customers",
                    ["id", "name", "cellphone", "address", "note"], cust_rows)

        # ---- 進貨批次 inventory_stock ----
        # 欄位：id, quantity, quantity_remaining, unit_cost, restocked_date,
        #       product_id, restocked_by_id, unit_id
        stock_rows = []
        today = date(2026, 5, 25)
        sid = 0
        for pid in product_ids:
            for _ in range(random.randint(1, 3)):
                sid += 1
                qty_base = random.randint(50, 300)
                rdate = today - timedelta(days=random.randint(0, 90))
                stock_rows.append([
                    sid, qty_base, qty_base, base_cost[pid], rdate.isoformat(),
                    pid, random.choice(emp_ids), base_unit_of[pid],
                ])
        self._write(out_dir, "stocks",
                    ["id", "quantity", "quantity_remaining", "unit_cost",
                     "restocked_date", "product_id", "restocked_by_id", "unit_id"],
                    stock_rows)

        # ---- 訂單 orders_order + 明細 orders_orderrecord ----
        # order 欄位：id, ordered_date, status, deleted_at, customer_id, deleted_by_id
        # record 欄位：id, quantity, price, cost, conversion_rate, discount, created_at,
        #             created_by_id, deleted_by_id, order_id, product_id, unit_id
        statuses = ["pending", "confirmed", "completed", "cancelled"]
        weights = [2, 3, 4, 1]
        order_rows = []
        record_rows = []
        rid = 0
        for i in range(opts["orders"]):
            oid = i + 1
            status = random.choices(statuses, weights=weights)[0]
            ordered = timezone.make_aware(datetime.combine(
                today - timedelta(days=random.randint(0, 60)),
                datetime.min.time().replace(hour=random.randint(9, 20))
            ))
            ordered_str = self._fmt_dt(ordered)
            order_rows.append([oid, ordered_str, status, None,
                               random.choice(customer_ids), None])
            for _ in range(random.randint(1, 4)):
                pid = random.choice(product_ids)
                puid_, u_id, price, cost, rate = random.choice(product_units[pid])
                discount = random.choice([Decimal("0"), Decimal("0.05"),
                                          Decimal("0.10"), Decimal("0.15")])
                rid += 1
                record_rows.append([
                    rid, random.randint(1, 5), price, cost, rate, discount,
                    ordered_str, random.choice(emp_ids), None, oid, pid, u_id,
                ])
        self._write(out_dir, "orders",
                    ["id", "ordered_date", "status", "deleted_at",
                     "customer_id", "deleted_by_id"], order_rows)
        self._write(out_dir, "order_record",
                    ["id", "quantity", "price", "cost", "conversion_rate", "discount",
                     "created_at", "created_by_id", "deleted_by_id",
                     "order_id", "product_id", "unit_id"], record_rows)

        self.stdout.write(self.style.SUCCESS(
            f"\n完成！CSV 已輸出至 {out_dir}/\n"
            f"  員工 {len(emp_rows)} / 單位 {len(unit_rows)} / 分類 {len(cat_rows)} / "
            f"商品 {len(product_rows)} / 商品單位 {len(pu_rows)} / 客戶 {len(cust_rows)} / "
            f"庫存 {len(stock_rows)} / 訂單 {len(order_rows)} / 明細 {len(record_rows)}\n"
            f"匯入順序建議：employees → units → categories → "
            f"products → product_unit → customers → "
            f"stocks → orders → order_record"
        ))

    @transaction.atomic
    def _seed_to_db(self, opts):
        """用 ORM 直接把示範資料寫入資料庫（等同舊版行為）。"""
        # 延遲匯入，避免純產 CSV 時載入這些 model
        from catalog.models import Category, Product, Unit, ProductUnit
        from customers.models import Customer
        from orders.models import Order, OrderRecord
        from inventory.models import Stock

        if opts["clean"]:
            self.stdout.write("清空舊資料...")
            OrderRecord.objects.all().delete()
            Order.objects.all().delete()
            Stock.objects.all().delete()
            ProductUnit.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Unit.objects.all().delete()
            Customer.objects.all().delete()
            Employee.objects.exclude(username="admin").delete()

        admin = Employee.objects.filter(lv=LV_ADMIN).first()
        if not admin:
            admin = Employee.objects.create_user(
                username="admin", password="admin12345",
                name="管理員", cellphone="0900000000", lv=LV_ADMIN,
            )
            self.stdout.write(self.style.WARNING("已建立 admin/admin12345"))

        # 員工
        emp_levels = [(LV_SALES, "業務"), (LV_SALES, "業務"), (LV_MANAGER, "主管"),
                      (LV_EMPLOYEE, "員工"), (LV_EMPLOYEE, "員工")]
        employees = [admin]
        for i, (lv, role) in enumerate(emp_levels, 1):
            emp, _ = Employee.objects.get_or_create(
                username=f"staff{i}",
                defaults={
                    "name": f"{random.choice(CUSTOMER_SURNAMES)}{role}{i}",
                    "cellphone": f"09{random.randint(10000000, 99999999)}",
                    "lv": lv,
                },
            )
            if not emp.has_usable_password():
                emp.set_password("staff12345")
                emp.save(update_fields=["password"])
            employees.append(emp)
        self.stdout.write(f"員工: {len(employees)} 位")

        # 單位
        units = {name: Unit.objects.get_or_create(name=name)[0] for name in UNITS}
        self.stdout.write(f"單位: {len(units)} 個")

        # 分類
        cats = {name: Category.objects.get_or_create(name=name)[0] for name in CATEGORIES}
        self.stdout.write(f"分類: {len(cats)} 個")

        # 商品 + 基準 ProductUnit + 部分加箱單位
        products = []
        for cat_name, names in PRODUCTS.items():
            for name in names:
                base = random.choice([units["個"], units["瓶"], units["罐"], units["包"], units["盒"]])
                price = Decimal(random.randint(15, 200))
                cost = (price * Decimal("0.6")).quantize(Decimal("0.01"))
                p, created = Product.objects.get_or_create(
                    name=name,
                    defaults={"category": cats[cat_name], "base_unit": base, "created_by": admin},
                )
                if created:
                    ProductUnit.objects.create(
                        product=p, unit=base, conversion_rate=1,
                        price=price, cost=cost, created_by=admin,
                    )
                    if random.random() < 0.5:
                        rate = random.choice([6, 12, 24])
                        ProductUnit.objects.create(
                            product=p, unit=units["箱"], conversion_rate=rate,
                            price=price * rate * Decimal("0.9"),
                            cost=cost * rate * Decimal("0.95"),
                            created_by=admin,
                        )
                products.append(p)
        self.stdout.write(f"商品: {len(products)} 個")

        # 客戶
        for i in range(opts["customers"]):
            name = f"{random.choice(CUSTOMER_SURNAMES)}{random.choice(CUSTOMER_GIVENNAMES)}"
            Customer.objects.get_or_create(
                name=f"{name}{i:02d}",
                defaults={
                    "cellphone": f"09{random.randint(10000000, 99999999)}",
                    "address": f"台北市信義區范例路{random.randint(1, 200)}號",
                    "note": "",
                },
            )
        customers = list(Customer.objects.all())
        self.stdout.write(f"客戶: {len(customers)} 位")

        # 進貨：每個商品 1-3 批
        Stock.objects.all().delete()  # 重置庫存以免訂單跑出來變負很多
        today = date(2026, 5, 25)
        for p in products:
            for _ in range(random.randint(1, 3)):
                pcs_pu = p.product_units.filter(unit=p.base_unit, status=ProductUnit.Status.ACTIVE).first()
                qty_base = random.randint(50, 300)
                Stock.objects.create(
                    product=p, unit=p.base_unit,
                    quantity=qty_base, quantity_remaining=qty_base,
                    unit_cost=pcs_pu.cost,
                    restocked_date=today - timedelta(days=random.randint(0, 90)),
                    restocked_by=random.choice(employees),
                )
        self.stdout.write(f"進貨批次: {Stock.objects.count()} 筆")

        # 訂單
        statuses = [Order.Status.PENDING, Order.Status.CONFIRMED, Order.Status.COMPLETED, Order.Status.CANCELLED]
        weights = [2, 3, 4, 1]
        for i in range(opts["orders"]):
            customer = random.choice(customers)
            status = random.choices(statuses, weights=weights)[0]
            ordered = timezone.make_aware(datetime.combine(
                today - timedelta(days=random.randint(0, 60)),
                datetime.min.time().replace(hour=random.randint(9, 20))
            ))
            order = Order.objects.create(customer=customer, ordered_date=ordered, status=status)
            for _ in range(random.randint(1, 4)):
                p = random.choice(products)
                pus = list(p.product_units.filter(status=ProductUnit.Status.ACTIVE))
                pu = random.choice(pus)
                discount = random.choice([Decimal("0"), Decimal("0.05"), Decimal("0.10"), Decimal("0.15")])
                OrderRecord.objects.create(
                    order=order, product=p, unit=pu.unit,
                    quantity=random.randint(1, 5),
                    price=pu.price, cost=pu.cost,
                    conversion_rate=pu.conversion_rate,
                    discount=discount,
                    created_by=random.choice(employees),
                )

        self.stdout.write(self.style.SUCCESS(
            f"\n完成（寫入資料庫）！訂單: {Order.objects.count()} / 明細: {OrderRecord.objects.count()} / "
            f"商品: {Product.objects.count()} / 客戶: {Customer.objects.count()} / 庫存批次: {Stock.objects.count()}"
        ))

    def _fmt_dt(self, dt):
        """aware datetime -> UTC 字串（對齊 Django 在 MySQL 的存法）"""
        return dt.astimezone(dt_timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    def _write(self, out_dir, table, header, rows):
        self._seq += 1
        filename = f"{self._seq:02d}_{table}.csv"  # 序號 = 匯入順序
        path = os.path.join(out_dir, filename)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            for row in rows:
                w.writerow([self.null if v is None else v for v in row])
        self.stdout.write(f"  {filename}: {len(rows)} 列")
