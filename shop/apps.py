from django.apps import AppConfig


class ShopConfig(AppConfig):
    name = "shop"

    def ready(self):
        from django.db.backends.signals import connection_created

        from .search import register_sqlite_search

        connection_created.connect(register_sqlite_search, dispatch_uid="shop.sqlite_search", weak=False)

        from django.db.models.signals import post_delete, post_save

        from .models import Category, Product, ProductVariant, Review
        from .recommendations import catalog_changed

        for model in (Category, Product, ProductVariant, Review):
            for signal in (post_save, post_delete):
                signal.connect(
                    catalog_changed,
                    sender=model,
                    dispatch_uid=f"shop.recommendations.{model.__name__}.{id(signal)}",
                    weak=False,
                )
