# Phase 4: Update Payment model for Razorpay integration
# - Update provider choices to RAZORPAY only
# - Update status choices to CREATED/SUCCESS/FAILED/REFUNDED
# - Add customer FK, razorpay_order_id, razorpay_payment_id, payment_method, signature_verified, currency

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Update provider choices to RAZORPAY only
        migrations.AlterField(
            model_name="payment",
            name="provider",
            field=models.CharField(
                choices=[("RAZORPAY", "Razorpay")],
                default="RAZORPAY",
                max_length=20,
            ),
        ),
        # Update status choices
        migrations.AlterField(
            model_name="payment",
            name="status",
            field=models.CharField(
                choices=[
                    ("CREATED", "Created"),
                    ("SUCCESS", "Success"),
                    ("FAILED", "Failed"),
                    ("REFUNDED", "Refunded"),
                ],
                default="CREATED",
                max_length=20,
            ),
        ),
        # Add customer foreign key
        migrations.AddField(
            model_name="payment",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Add razorpay_order_id
        migrations.AddField(
            model_name="payment",
            name="razorpay_order_id",
            field=models.CharField(
                blank=True, max_length=100, null=True, unique=True
            ),
        ),
        # Add razorpay_payment_id
        migrations.AddField(
            model_name="payment",
            name="razorpay_payment_id",
            field=models.CharField(
                blank=True, max_length=100, null=True, unique=True
            ),
        ),
        # Add payment_method
        migrations.AddField(
            model_name="payment",
            name="payment_method",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        # Add signature_verified
        migrations.AddField(
            model_name="payment",
            name="signature_verified",
            field=models.BooleanField(default=False),
        ),
        # Add currency
        migrations.AddField(
            model_name="payment",
            name="currency",
            field=models.CharField(default="INR", max_length=3),
        ),
    ]
