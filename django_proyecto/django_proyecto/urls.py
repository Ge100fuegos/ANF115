

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.shortcuts import redirect
from django.contrib.auth.views import LogoutView, LoginView
from ChivoBits_app.views import usuario

urlpatterns = [
    path('', lambda request: redirect('login')),  # Redirige la raíz al login
    path('login/', usuario.login_usuario, name='login'),
    path('admin/', admin.site.urls),
    path('ChivoBits_app/', include('ChivoBits_app.urls')),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('login/', LoginView.as_view(template_name='usuarios/login.html'), name='login'),
]
"""if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)"""
