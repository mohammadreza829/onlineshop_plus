from django.db import migrations


class Migration(migrations.Migration):
    """
    `stock_updated` meant "stock was deducted for this order" (only after payment).
    In phase 1 stock is deducted when the order is created (reservation), so the
    same flag now means "this order currently holds stock". Existing paid orders
    (stock_updated=True) keep the correct meaning, so a rename is safe.
    """

    dependencies = [
        ("orders", "0005_order_address_obj"),
    ]

    operations = [
        migrations.RenameField(
            model_name="order",
            old_name="stock_updated",
            new_name="stock_reserved",
        ),
    ]
