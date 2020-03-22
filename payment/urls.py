from django.urls import path
from .views import xsollaWebhook

urlpatterns = [
    path('', xsollaWebhook, name="webhook"),
]
