from django.apps import AppConfig


class ShopConfig(AppConfig):
    name = "shop"

    def ready(self):
        from django.db.backends.signals import connection_created

        from .search import register_sqlite_search

        connection_created.connect(register_sqlite_search, dispatch_uid="shop.sqlite_search", weak=False)
