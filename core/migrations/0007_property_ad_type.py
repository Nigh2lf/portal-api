from django.db import migrations, models


def copiar_destaque(apps, schema_editor):
    Property = apps.get_model("core", "Property")
    Property.objects.filter(is_featured=True).update(ad_type="FEATURED")


def reverter_destaque(apps, schema_editor):
    Property = apps.get_model("core", "Property")
    Property.objects.exclude(ad_type="NORMAL").update(is_featured=True)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_postal_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="ad_type",
            field=models.CharField(
                choices=[("NORMAL", "Normal"), ("FEATURED", "Destaque"), ("SUPER_FEATURED", "Superdestaque")],
                db_index=True,
                default="NORMAL",
                help_text="Legado: Destaque 0/1/2.",
                max_length=16,
            ),
        ),
        migrations.RunPython(copiar_destaque, reverter_destaque),
        migrations.RemoveField(model_name="property", name="is_featured"),
        migrations.AlterModelOptions(
            name="property",
            options={"ordering": ("-updated_at",), "verbose_name_plural": "properties"},
        ),
    ]
