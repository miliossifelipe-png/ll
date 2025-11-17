"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from accounts import views as accounts_views
from django.conf import settings
from django.conf.urls.static import static
from logs.views import log_list

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', accounts_views.login_view, name='login'),
    path('logout/', accounts_views.logout_view, name='logout'),
    path('', accounts_views.dashboard, name='dashboard'),
    path('dashboard/data/', accounts_views.dashboard_data, name='dashboard_data'),
    path('dashboard/logs_data/', accounts_views.dashboard_logs_data, name='dashboard_logs_data'),
    path('canais/', include('channels.urls')),
    path('mensagens/', include('scheduled_messages.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('mensagens/canais/', accounts_views.canais_list, name='canais_list'),
    path('accounts/usuarios/', accounts_views.usuarios_list, name='usuarios_list'),
    path('logs/', log_list, name='log_list'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler500 = 'core.views.erro_500'
handler404 = 'core.views.erro_404'
