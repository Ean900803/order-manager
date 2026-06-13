from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(name="order", table="orders"),
        migrations.AlterModelTable(name="orderrecord", table="order_record"),
    ]
