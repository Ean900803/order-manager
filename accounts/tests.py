from datetime import date
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Employee, LV_EMPLOYEE, LV_SALES, LV_MANAGER, LV_ADMIN
from catalog.models import Category, Product, Unit, ProductUnit
from customers.models import Customer
from orders.models import Order, OrderRecord
from inventory.models import Stock
from inventory.services import consume_for_order, estimate_shortage


def make_employee(username, lv=LV_EMPLOYEE, resigned=False, **kwargs):
    emp = Employee.objects.create_user(
        username=username,
        password="testpass123",
        name=kwargs.get("name", username),
        cellphone=kwargs.get("cellphone", "0912345678"),
        lv=lv,
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
            lv=LV_ADMIN,
        )
    return _admin_for_fixtures


def make_unit(name="個"):
    return Unit.objects.get_or_create(name=name)[0]


def make_category(name="測試分類", disabled=False):
    cat = Category.objects.create(name=name)
    if disabled:
        cat.disable()
    return cat


def make_product(category, name="測試商品", price=Decimal("100.00"), cost=Decimal("60.00"),
                 base_unit=None, disabled=False, created_by=None):
    base_unit = base_unit or make_unit("個")
    user = created_by or _fixture_user()
    p = Product.objects.create(category=category, name=name, base_unit=base_unit, created_by=user)
    ProductUnit.objects.create(
        product=p, unit=base_unit, conversion_rate=1,
        price=Decimal(price), cost=Decimal(cost), created_by=user,
    )
    if disabled:
        p.disable(by=user)
    return p


def make_customer(name="測試客戶"):
    return Customer.objects.create(name=name, cellphone="0987654321")


def make_order(customer, status=Order.Status.PENDING):
    return Order.objects.create(customer=customer, status=status)


def make_record(order, product, qty=1, discount=Decimal("0"), unit=None):
    unit = unit or product.base_unit
    pu = product.active_unit(unit)
    return OrderRecord.objects.create(
        order=order, product=product, unit=unit,
        quantity=qty, price=pu.price, cost=pu.cost,
        conversion_rate=pu.conversion_rate,
        discount=Decimal(discount),
        created_by=_fixture_user(),
    )


def make_stock(product, qty_base, unit_cost=Decimal("10"), restocked_date=None):
    unit = product.base_unit
    return Stock.objects.create(
        product=product, unit=unit,
        quantity=qty_base, quantity_remaining=qty_base,
        unit_cost=Decimal(unit_cost),
        restocked_date=restocked_date or date(2026, 1, 1),
        restocked_by=_fixture_user(),
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


# ── Permission guards ──────────────────────────────────────────────────────────

class PermissionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.employee = make_employee("emp", lv=LV_EMPLOYEE)
        self.sales = make_employee("sales", lv=LV_SALES)
        self.manager = make_employee("mgr", lv=LV_MANAGER)
        self.admin = make_employee("admin", lv=LV_ADMIN)
        self.cat = make_category()
        self.product = make_product(self.cat)
        self.customer = make_customer()

    def _login(self, emp):
        self.client.login(username=emp.username, password="testpass123")

    def test_employee_cannot_create_product(self):
        self._login(self.employee)
        resp = self.client.get(reverse("catalog:product_create"))
        self.assertRedirects(resp, reverse("orders:list"), fetch_redirect_response=False)

    def test_sales_can_create_product(self):
        self._login(self.sales)
        resp = self.client.get(reverse("catalog:product_create"))
        self.assertEqual(resp.status_code, 200)

    def test_employee_cannot_create_category(self):
        self._login(self.employee)
        resp = self.client.get(reverse("catalog:category_create"))
        self.assertRedirects(resp, reverse("orders:list"), fetch_redirect_response=False)

    def test_employee_cannot_create_customer(self):
        self._login(self.employee)
        resp = self.client.get(reverse("customers:customer_create"))
        self.assertRedirects(resp, reverse("orders:list"), fetch_redirect_response=False)

    def test_employee_cannot_access_employee_create(self):
        self._login(self.employee)
        resp = self.client.get(reverse("accounts:employee_create"))
        self.assertRedirects(resp, reverse("orders:list"), fetch_redirect_response=False)

    def test_employee_can_edit_self(self):
        self._login(self.employee)
        resp = self.client.get(reverse("accounts:employee_edit", args=[self.employee.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_employee_cannot_edit_others(self):
        self._login(self.employee)
        resp = self.client.get(reverse("accounts:employee_edit", args=[self.sales.pk]))
        self.assertRedirects(resp, reverse("accounts:employee_list"), fetch_redirect_response=False)

    def test_admin_can_edit_all_employees(self):
        self._login(self.admin)
        resp = self.client.get(reverse("accounts:employee_edit", args=[self.employee.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_manager_cannot_change_order_without_permission(self):
        order = make_order(self.customer)
        self._login(self.employee)
        resp = self.client.get(reverse("orders:status", args=[order.pk]))
        self.assertRedirects(resp, reverse("orders:list"), fetch_redirect_response=False)

    def test_manager_can_change_order_status(self):
        order = make_order(self.customer)
        self._login(self.manager)
        resp = self.client.get(reverse("orders:status", args=[order.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_non_admin_cannot_restore_category(self):
        cat = make_category(disabled=True)
        self._login(self.sales)
        resp = self.client.post(reverse("catalog:category_restore", args=[cat.pk]))
        self.assertRedirects(resp, reverse("orders:list"), fetch_redirect_response=False)

    def test_admin_can_restore_category(self):
        cat = make_category(disabled=True)
        self._login(self.admin)
        resp = self.client.post(reverse("catalog:category_restore", args=[cat.pk]))
        cat.refresh_from_db()
        self.assertIsNone(cat.deleted_at)


# ── Catalog rules ──────────────────────────────────────────────────────────────

class CatalogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.sales = make_employee("sales2", lv=LV_SALES)
        self.client.login(username="sales2", password="testpass123")
        self.cat = make_category()

    def test_disabled_category_not_in_product_form(self):
        disabled_cat = make_category("停用分類", disabled=True)
        resp = self.client.get(reverse("catalog:product_create"))
        choices = list(resp.context["form"].fields["category"].queryset)
        self.assertNotIn(disabled_cat, choices)
        self.assertIn(self.cat, choices)

    def test_disable_and_restore_product(self):
        p = make_product(self.cat)
        admin = make_employee("admin2", lv=LV_ADMIN)
        self.client.login(username="admin2", password="testpass123")

        self.client.post(reverse("catalog:product_disable", args=[p.pk]))
        p.refresh_from_db()
        self.assertIsNotNone(p.deleted_at)

        self.client.post(reverse("catalog:product_restore", args=[p.pk]))
        p.refresh_from_db()
        self.assertIsNone(p.deleted_at)


# ── ProductUnit (multi-unit pricing) ───────────────────────────────────────────

class ProductUnitTests(TestCase):
    def setUp(self):
        self.user = make_employee("pu_user", lv=LV_SALES)
        self.cat = make_category()
        self.pcs = make_unit("個")
        self.box = make_unit("箱")
        self.product = make_product(self.cat, base_unit=self.pcs, price=Decimal("30"), cost=Decimal("15"))

    def test_only_one_active_per_unit(self):
        """同 product+unit 建新 active 時，舊 active 變 inactive"""
        ProductUnit.objects.create(
            product=self.product, unit=self.pcs, conversion_rate=1,
            price=Decimal("40"), cost=Decimal("20"),
            created_by=self.user,
        )
        # 模擬 form 的 deactivate 邏輯
        active_existing = self.product.product_units.filter(unit=self.pcs, status=ProductUnit.Status.ACTIVE).first()
        # 模擬 form 內邏輯：建新 active 前，把舊 active 改 inactive
        self.product.product_units.filter(
            unit=self.pcs, status=ProductUnit.Status.ACTIVE
        ).exclude(pk=active_existing.pk).update(status=ProductUnit.Status.INACTIVE)
        actives = self.product.product_units.filter(unit=self.pcs, status=ProductUnit.Status.ACTIVE).count()
        self.assertEqual(actives, 1)

    def test_box_pricing_independent_from_base(self):
        ProductUnit.objects.create(
            product=self.product, unit=self.box, conversion_rate=12,
            price=Decimal("320"), cost=Decimal("170"),
            created_by=self.user,
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

    def test_order_total_excludes_soft_deleted_records(self):
        order = make_order(self.customer)
        make_record(order, self.product, qty=1, discount=Decimal("0"))
        rec2 = make_record(order, self.product, qty=1, discount=Decimal("0"))
        rec2.deleted_at = timezone.now()
        rec2.save()
        self.assertEqual(order.total, Decimal("200.00"))


# ── Order cancel ───────────────────────────────────────────────────────────────

class OrderCancelTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = make_employee("mgr2", lv=LV_MANAGER)
        self.client.login(username="mgr2", password="testpass123")
        self.customer = make_customer()

    def test_cancel_order_sets_status(self):
        order = make_order(self.customer, status=Order.Status.CONFIRMED)
        self.client.post(reverse("orders:cancel", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)

    def test_disabled_product_not_in_order_form(self):
        cat = make_category()
        active = make_product(cat, name="啟用商品")
        disabled = make_product(cat, name="停用商品", disabled=True)
        emp = make_employee("emp2", lv=LV_EMPLOYEE)
        self.client.login(username="emp2", password="testpass123")
        resp = self.client.get(reverse("orders:create"))
        qs = list(resp.context["formset"].forms[0].fields["product"].queryset)
        self.assertIn(active, qs)
        self.assertNotIn(disabled, qs)

    def test_completed_order_cannot_cancel(self):
        order = make_order(self.customer, status=Order.Status.COMPLETED)
        resp = self.client.post(reverse("orders:cancel", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)


# ── FIFO inventory ─────────────────────────────────────────────────────────────

class FIFOTests(TestCase):
    def setUp(self):
        self.cat = make_category()
        self.product = make_product(self.cat, price=Decimal("30"), cost=Decimal("15"))
        self.customer = make_customer()

    def test_fifo_consumes_earliest_batch_first(self):
        make_stock(self.product, qty_base=20, restocked_date=date(2026, 1, 1))
        make_stock(self.product, qty_base=20, restocked_date=date(2026, 2, 1))
        order = make_order(self.customer)
        make_record(order, self.product, qty=15)

        consume_for_order(order, by=_fixture_user())
        batches = list(Stock.objects.filter(product=self.product).order_by("restocked_date"))
        self.assertEqual(batches[0].quantity_remaining, 5)   # 20 - 15
        self.assertEqual(batches[1].quantity_remaining, 20)  # 未動

    def test_fifo_negative_remainder_on_shortage(self):
        make_stock(self.product, qty_base=10, restocked_date=date(2026, 1, 1))
        order = make_order(self.customer)
        make_record(order, self.product, qty=25)

        shortage = consume_for_order(order, by=_fixture_user())
        batch = Stock.objects.get(product=self.product)
        self.assertEqual(batch.quantity_remaining, -15)  # 10 - 25
        self.assertEqual(shortage[self.product], 15)

    def test_estimate_shortage(self):
        make_stock(self.product, qty_base=5, restocked_date=date(2026, 1, 1))
        order = make_order(self.customer)
        make_record(order, self.product, qty=8)
        shortage = estimate_shortage(order.records.all())
        self.assertEqual(shortage[self.product], 3)
