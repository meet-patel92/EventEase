from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"stats", views.DashboardStatViewSet)

urlpatterns = [
    path("overview/", views.DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("", include(router.urls)),
]
