from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(name="customer", table="customers"),
    ]
