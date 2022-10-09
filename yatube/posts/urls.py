from django.urls import path
from . import views


urlpatterns = [
    path('', views.index),
    path('group/<int:pk>/', views.group_posts)
]