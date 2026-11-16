# Phase 3: Add booking fields, rename created_at to booking_date, user to customer
# Update status choices (REFUNDED -> EXPIRED)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0005_event_poster_alter_event_slug"),
        ("bookings", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Rename user -> customer
        migrations.RenameField(
            model_name="booking",
            old_name="user",
            new_name="customer",
        ),
        # Rename created_at -> booking_date
        migrations.RenameField(
            model_name="booking",
            old_name="created_at",
            new_name="booking_date",
        ),
        # Add new fields
        migrations.AddField(
            model_name="booking",
            name="booking_reference",
            field=models.CharField(blank=True, max_length=20, unique=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="quantity",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="booking",
            name="unit_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        # Update status choices (REFUNDED -> EXPIRED)
        migrations.AlterField(
            model_name="booking",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("CONFIRMED", "Confirmed"),
                    ("CANCELLED", "Cancelled"),
                    ("EXPIRED", "Expired"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
        # Update ordering
        migrations.AlterModelOptions(
            name="booking",
            options={"ordering": ("-booking_date",)},
        ),
    ]
