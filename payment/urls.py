from django.urls import path
from .views import anypay_webhook

urlpatterns = [
    path('', anypay_webhook, name="webhook"),
]
