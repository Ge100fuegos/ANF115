from django.urls import path
from ChivoBits_app.views import usuario

urlpatterns = [
    path('login/', usuario.login_usuario, name='login'),
    path('logout/', usuario.logout_view, name='logout'),
]