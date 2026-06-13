from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(name="stock", table="stocks"),
    ]
