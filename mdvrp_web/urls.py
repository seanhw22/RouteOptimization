"""URL configuration for mdvrp_web project."""

from django.contrib import admin
from django.urls import include, path

from mdvrp_web.views import homepage
from runs.admin_views import stats_dashboard


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('', homepage, name='root'),
    path('admin/stats/', admin.site.admin_view(stats_dashboard), name='admin_stats'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('datasets/', include('datasets.urls', namespace='datasets')),
    path('runs/', include('runs.urls', namespace='runs')),
    path('results/', include('results.urls', namespace='results')),
]
