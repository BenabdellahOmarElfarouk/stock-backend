from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_organisation_is_active_user_is_platform_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisation",
            name="locale",
            field=models.CharField(
                choices=[("fr", "Français"), ("ar", "العربية")],
                default="fr",
                max_length=8,
                verbose_name="Langue",
            ),
        ),
    ]
