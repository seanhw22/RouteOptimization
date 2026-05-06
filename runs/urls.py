from django.urls import path

from . import views

app_name = 'runs'

urlpatterns = [
    path('configure/<int:dataset_id>/', views.configure, name='configure'),
    path('<int:batch_id>/', views.viewer, name='viewer'),
    path('<int:batch_id>/status/', views.status, name='status'),
    path('<int:batch_id>/experiments/<int:exp_id>/kill/', views.kill, name='kill'),
    path('<int:batch_id>/share/', views.generate_share_link, name='generate_share_link'),
]
