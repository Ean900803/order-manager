from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Employee, LV_EMPLOYEE, LV_SALES, LV_MANAGER, LV_ADMIN
from catalog.models import Category, Product
from customers.models import Customer
from orders.models import Order, OrderRecord


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
        emp.is_active = False
        emp.save()
    return emp


def make_category(name="測試分類", disabled=False):
    cat = Category.objects.create(name=name)
    if disabled:
        cat.disable()
    return cat


def make_product(category, name="測試商品", price="100.00", cost="60.00", disabled=False):
    p = Product.objects.create(category=category, name=name, price=price, cost=cost)
    if disabled:
        p.disable()
    return p


def make_customer(name="測試客戶"):
    return Customer.objects.create(name=name, cellphone="0987654321")


def make_order(customer, status=Order.STATUS_PENDING):
    return Order.objects.create(customer=customer, status=status)


def make_record(order, product, qty=1, discount="0"):
    return OrderRecord.objects.create(
        order=order, product=product,
        quantity=qty, price=product.price, cost=product.cost, discount=discount,
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
        """lv=1 員工無法修改訂單狀態"""
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


# ── Order calculation ──────────────────────────────────────────────────────────

class OrderCalculationTests(TestCase):
    def setUp(self):
        self.cat = make_category()
        self.product = make_product(self.cat, price="200.00", cost="100.00")
        self.customer = make_customer()

    def test_subtotal_no_discount(self):
        order = make_order(self.customer)
        rec = make_record(order, self.product, qty=3, discount="0")
        self.assertAlmostEqual(float(rec.subtotal), 600.0)

    def test_subtotal_with_discount(self):
        order = make_order(self.customer)
        rec = make_record(order, self.product, qty=2, discount="10")
        # 200 * 2 * (1 - 10/100) = 360
        self.assertAlmostEqual(float(rec.subtotal), 360.0)

    def test_order_total(self):
        order = make_order(self.customer)
        make_record(order, self.product, qty=1, discount="0")   # 200
        make_record(order, self.product, qty=2, discount="50")  # 200 * 2 * 0.5 = 200
        self.assertAlmostEqual(float(order.total), 400.0)

    def test_order_total_excludes_soft_deleted_records(self):
        order = make_order(self.customer)
        rec1 = make_record(order, self.product, qty=1, discount="0")   # 200
        rec2 = make_record(order, self.product, qty=1, discount="0")   # 200 (but deleted)
        rec2.deleted_at = timezone.now()
        rec2.save()
        self.assertAlmostEqual(float(order.total), 200.0)


# ── Order cancel ───────────────────────────────────────────────────────────────

class OrderCancelTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = make_employee("mgr2", lv=LV_MANAGER)
        self.client.login(username="mgr2", password="testpass123")
        self.customer = make_customer()

    def test_cancel_order_sets_status(self):
        order = make_order(self.customer, status=Order.STATUS_CONFIRMED)
        self.client.post(reverse("orders:cancel", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELLED)

    def test_disabled_product_not_in_order_form(self):
        cat = make_category()
        active = make_product(cat, name="啟用商品")
        disabled = make_product(cat, name="停用商品", disabled=True)
        emp = make_employee("emp2", lv=LV_EMPLOYEE)
        self.client.login(username="emp2", password="testpass123")
        resp = self.client.get(reverse("orders:create"))
        # 抓 formset 第一個 form 的 product queryset
        qs = list(resp.context["formset"].forms[0].fields["product"].queryset)
        self.assertIn(active, qs)
        self.assertNotIn(disabled, qs)
