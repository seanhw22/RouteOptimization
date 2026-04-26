from django.urls import path

from . import views

app_name = 'results'

urlpatterns = [
    path('<int:batch_id>/', views.dashboard, name='dashboard'),
    path('<int:batch_id>/<int:exp_id>/csv/', views.download_csv, name='download_csv'),
    path('<int:batch_id>/<int:exp_id>/pdf/', views.download_pdf, name='download_pdf'),
    path('<int:batch_id>/<int:exp_id>/geojson/', views.download_geojson, name='download_geojson'),
]
