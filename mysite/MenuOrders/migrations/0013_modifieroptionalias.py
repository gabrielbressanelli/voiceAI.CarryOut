from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("MenuOrders", "0012_modifieroption_price_multiplier"),
    ]

    operations = [
        migrations.CreateModel(
            name="ModifierOptionAlias",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("alias", models.CharField(max_length=100)),
                ("option", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="aliases", to="MenuOrders.modifieroption")),
            ],
            options={"unique_together": {("option", "alias")}},
        ),
    ]
