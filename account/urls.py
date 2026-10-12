from django.urls import path
from . import views

app_name = 'account'

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
]