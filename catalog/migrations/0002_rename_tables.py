from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(name="unit", table="units"),
        migrations.AlterModelTable(name="category", table="categories"),
        migrations.AlterModelTable(name="product", table="products"),
        migrations.AlterModelTable(name="productunit", table="product_unit"),
    ]
