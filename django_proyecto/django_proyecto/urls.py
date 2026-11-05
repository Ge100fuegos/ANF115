"""
URL configuration for django_proyecto project.

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
