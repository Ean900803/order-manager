"""
產生示範資料供查詢測試。

用法：
  python manage.py seed_demo            # 預設量：5 員工 / 40 商品 / 40 客戶 / 100 訂單
  python manage.py seed_demo --clean    # 先清空（保留 admin 帳號）後重建
"""
import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Employee, LV_EMPLOYEE, LV_SALES, LV_MANAGER, LV_ADMIN
from catalog.models import Category, Product, Unit, ProductUnit
from customers.models import Customer
from orders.models import Order, OrderRecord
from inventory.models import Stock


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
    help = "產生示範資料供查詢測試"

    def add_arguments(self, parser):
        parser.add_argument("--clean", action="store_true", help="清空舊資料後重建（保留 admin）")
        parser.add_argument("--orders", type=int, default=100)
        parser.add_argument("--customers", type=int, default=40)

    @transaction.atomic
    def handle(self, *args, **opts):
        random.seed(42)

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
                    # 50% 機率加箱單位
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
            # 1-4 筆明細
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
            f"\n完成！訂單: {Order.objects.count()} / 明細: {OrderRecord.objects.count()} / "
            f"商品: {Product.objects.count()} / 客戶: {Customer.objects.count()} / 庫存批次: {Stock.objects.count()}"
        ))
