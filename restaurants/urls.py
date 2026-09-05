from django.urls import path
from . import views

urlpatterns = [
    path('', views.storefront_view, name='storefront'),
    path('review/submit/', views.submit_review_view, name='submit_review'),
]