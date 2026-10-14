"""Dynamic/API responses are not reusable caches of private data or live stock."""

from django.utils.cache import patch_cache_control


class APINoStoreMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(("/api/v1/", "/orders/api/v1/")):
            patch_cache_control(response, private=True, no_store=True)
        return response
