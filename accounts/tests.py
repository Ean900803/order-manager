from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Employee
from catalog.models import Category, Product, Unit, ProductUnit
from customers.models import Customer
from orders.models import Order, OrderRecord
from inventory.models import Stock
from inventory.services import consume_for_order, estimate_shortage


def make_employee(username, resigned=False, **kwargs):
    emp = Employee.objects.create_user(
        username=username,
        password="testpass123",
        name=kwargs.get("name", username),
        cellphone=kwargs.get("cellphone", "0912345678"),
    )
    if resigned:
        emp.resigned_date = timezone.now()
        emp.save(update_fields=["resigned_date"])
    return emp


_admin_for_fixtures = None


def _fixture_user():
    global _admin_for_fixtures
    if _admin_for_fixtures is None or not Employee.objects.filter(pk=_admin_for_fixtures.pk).exists():
        _admin_for_fixtures = Employee.objects.create_user(
            username="_fixture_admin",
            password="fixture",
            name="Fixture",
            cellphone="0900000000",
        )
    return _admin_for_fixtures


def make_unit(name="個"):
    return Unit.objects.get_or_create(name=name)[0]


def make_category(name="測試分類"):
    return Category.objects.create(name=name)


def make_product(category, name="測試商品", price=Decimal("100.00"), cost=Decimal("60.00"),
                 unit=None, created_by=None):
    unit = unit or make_unit("個")
    user = created_by or _fixture_user()
    p = Product.objects.create(category=category, name=name, created_by=user)
    ProductUnit.objects.create(
        product=p, unit=unit, conversion_rate=1,
        price=Decimal(price), cost=Decimal(cost),
    )
    return p


def make_customer(name="測試客戶"):
    return Customer.objects.create(name=name, cellphone="0987654321")


def make_order(customer, status=Order.Status.PENDING):
    return Order.objects.create(customer=customer, status=status, created_by=_fixture_user())


def make_record(order, product, qty=1, discount=Decimal("0")):
    pu = product.product_units.filter(status=ProductUnit.Status.ACTIVE).first()
    return OrderRecord.objects.create(
        order=order, product=product,
        quantity=qty, price=pu.price, cost=pu.cost,
        conversion_rate=pu.conversion_rate,
        discount=Decimal(discount),
    )


def make_stock(product, qty_base, unit_cost=Decimal("10")):
    unit = product.product_units.first().unit
    return Stock.objects.create(
        product=product, unit=unit,
        quantity=qty_base, quantity_remaining=qty_base,
        unit_cost=Decimal(unit_cost),
    )


# ── Authentication ─────────────────────────────────────────────────────────────

class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.emp = make_employee("staff1")
        self.resigned = make_employee("resigned1", resigned=True)

    def test_login_success(self):
        resp = self.client.post(reverse("accounts:login"), {"username": "staff1", "password": "testpass123"})
        self.assertRedirects(resp, reverse("orders:list"), fetch_redirect_response=False)

    def test_login_wrong_password(self):
        resp = self.client.post(reverse("accounts:login"), {"username": "staff1", "password": "wrong"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["user"].is_authenticated)

    def test_resigned_employee_cannot_login(self):
        resp = self.client.post(reverse("accounts:login"), {"username": "resigned1", "password": "testpass123"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["user"].is_authenticated)

    def test_logout(self):
        self.client.login(username="staff1", password="testpass123")
        resp = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(resp, reverse("accounts:login"), fetch_redirect_response=False)


# ── Access：登入後即可使用（權限系統已移除）──────────────────────────────────────

class AccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.emp = make_employee("emp")
        self.client.login(username="emp", password="testpass123")
        self.cat = make_category()

    def test_logged_in_can_create_product(self):
        resp = self.client.get(reverse("catalog:product_create"))
        self.assertEqual(resp.status_code, 200)

    def test_logged_in_can_create_customer(self):
        resp = self.client.get(reverse("customers:customer_create"))
        self.assertEqual(resp.status_code, 200)

    def test_logged_in_can_access_employee_create(self):
        resp = self.client.get(reverse("accounts:employee_create"))
        self.assertEqual(resp.status_code, 200)

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        resp = self.client.get(reverse("catalog:product_create"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url)


# ── Catalog ──────────────────────────────────────────────────────────────────

class CatalogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_employee("sales2")
        self.client.login(username="sales2", password="testpass123")
        self.cat = make_category()

    def test_create_product_creates_initial_pricing(self):
        unit = make_unit("個")
        resp = self.client.post(reverse("catalog:product_create"), {
            "category": self.cat.pk, "name": "新商品", "description": "",
            "unit": unit.pk, "price": "50", "cost": "30",
        })
        self.assertRedirects(resp, reverse("catalog:product_list"), fetch_redirect_response=False)
        p = Product.objects.get(name="新商品")
        self.assertEqual(p.product_units.filter(status=ProductUnit.Status.ACTIVE).count(), 1)

    def test_delete_product(self):
        p = make_product(self.cat)
        self.client.post(reverse("catalog:product_delete", args=[p.pk]))
        self.assertFalse(Product.objects.filter(pk=p.pk).exists())


# ── ProductUnit (multi-unit pricing) ───────────────────────────────────────────

class ProductUnitTests(TestCase):
    def setUp(self):
        self.cat = make_category()
        self.pcs = make_unit("個")
        self.box = make_unit("箱")
        self.product = make_product(self.cat, unit=self.pcs, price=Decimal("30"), cost=Decimal("15"))

    def test_box_pricing_independent_from_base(self):
        ProductUnit.objects.create(
            product=self.product, unit=self.box, conversion_rate=12,
            price=Decimal("320"), cost=Decimal("170"),
        )
        active_box = self.product.active_unit(self.box)
        self.assertEqual(active_box.conversion_rate, 12)
        self.assertEqual(active_box.price, Decimal("320"))


# ── Order calculation (discount 0-1) ───────────────────────────────────────────

class OrderCalculationTests(TestCase):
    def setUp(self):
        self.cat = make_category()
        self.product = make_product(self.cat, price=Decimal("200"), cost=Decimal("100"))
        self.customer = make_customer()

    def test_subtotal_no_discount(self):
        order = make_order(self.customer)
        rec = make_record(order, self.product, qty=3, discount=Decimal("0"))
        self.assertEqual(rec.subtotal, Decimal("600.00"))

    def test_subtotal_with_discount(self):
        order = make_order(self.customer)
        rec = make_record(order, self.product, qty=2, discount=Decimal("0.10"))
        # 200 * 2 * (1 - 0.10) = 360
        self.assertEqual(rec.subtotal, Decimal("360.00"))

    def test_order_total(self):
        order = make_order(self.customer)
        make_record(order, self.product, qty=1, discount=Decimal("0"))      # 200
        make_record(order, self.product, qty=2, discount=Decimal("0.50"))   # 200
        self.assertEqual(order.total, Decimal("400.00"))


# ── Order cancel ───────────────────────────────────────────────────────────────

class OrderCancelTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = make_employee("mgr2")
        self.client.login(username="mgr2", password="testpass123")
        self.customer = make_customer()

    def test_cancel_order_sets_status(self):
        order = make_order(self.customer, status=Order.Status.CONFIRMED)
        self.client.post(reverse("orders:cancel", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)

    def test_completed_order_cannot_cancel(self):
        order = make_order(self.customer, status=Order.Status.COMPLETED)
        self.client.post(reverse("orders:cancel", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)


# ── FIFO inventory ─────────────────────────────────────────────────────────────

class FIFOTests(TestCase):
    def setUp(self):
        self.cat = make_category()
        self.product = make_product(self.cat, price=Decimal("30"), cost=Decimal("15"))
        self.customer = make_customer()

    def test_fifo_consumes_earliest_batch_first(self):
        b1 = make_stock(self.product, qty_base=20)
        b2 = make_stock(self.product, qty_base=20)
        order = make_order(self.customer)
        make_record(order, self.product, qty=15)

        consume_for_order(order, by=_fixture_user())
        b1.refresh_from_db()
        b2.refresh_from_db()
        self.assertEqual(b1.quantity_remaining, 5)   # 20 - 15（較早批次先扣）
        self.assertEqual(b2.quantity_remaining, 20)  # 未動

    def test_fifo_negative_remainder_on_shortage(self):
        make_stock(self.product, qty_base=10)
        order = make_order(self.customer)
        make_record(order, self.product, qty=25)

        shortage = consume_for_order(order, by=_fixture_user())
        batch = Stock.objects.get(product=self.product)
        self.assertEqual(batch.quantity_remaining, -15)  # 10 - 25
        self.assertEqual(shortage[self.product], 15)

    def test_estimate_shortage(self):
        make_stock(self.product, qty_base=5)
        order = make_order(self.customer)
        make_record(order, self.product, qty=8)
        shortage = estimate_shortage(order.records.all())
        self.assertEqual(shortage[self.product], 3)
