from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.EmailLoginView.as_view(), name='login'),
    path('logout/', views.EmailLogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('guest/', views.continue_as_guest, name='guest'),
]
