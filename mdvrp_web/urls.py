"""URL configuration for mdvrp_web project."""

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path


def root_redirect(request):
    if request.user.is_authenticated or request.session.get('is_guest'):
        return redirect('datasets:list')
    return redirect('accounts:login')


urlpatterns = [
    path('', root_redirect, name='root'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('datasets/', include('datasets.urls', namespace='datasets')),
    path('runs/', include('runs.urls', namespace='runs')),
    path('results/', include('results.urls', namespace='results')),
]
