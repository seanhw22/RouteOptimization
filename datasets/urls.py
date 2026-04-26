from django.urls import path

from . import views

app_name = 'datasets'

urlpatterns = [
    path('', views.dataset_list, name='list'),
    path('upload/', views.upload, name='upload'),
    path('<int:dataset_id>/', views.detail, name='detail'),
]
