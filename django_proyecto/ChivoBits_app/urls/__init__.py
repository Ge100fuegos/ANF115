from django.urls import path, include

urlpatterns = [
    path('', include('ChivoBits_app.urls.usuario')),
    path('', include('ChivoBits_app.urls.contaGeneral')),
    path('', include('ChivoBits_app.urls.costos')),
    path('', include('ChivoBits_app.urls.estadosFinancieros')),
]