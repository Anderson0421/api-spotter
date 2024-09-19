from .views import ServiceDNIAPIView
from django.urls import path

urlpatterns = [
    path('dni/', ServiceDNIAPIView.as_view(), name='service-dni'),
]
