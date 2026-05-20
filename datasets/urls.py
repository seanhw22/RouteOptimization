from django.urls import path

from . import views

app_name = 'datasets'

urlpatterns = [
    path('', views.dataset_list, name='list'),
    path('upload/', views.upload, name='upload'),
    path('<int:dataset_id>/', views.detail, name='detail'),
    path('<int:dataset_id>/rename/', views.rename_dataset, name='rename'),
    path('<int:dataset_id>/share/', views.generate_share_link, name='generate_share_link'),
    path('<int:dataset_id>/delete/', views.delete_dataset, name='delete'),
    path('load-sample/', views.load_sample, name='load_sample'),
]
