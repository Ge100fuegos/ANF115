from django.urls import path
from ChivoBits_app.views import costos

urlpatterns = [
    path('costo/', costos.costo, name='costo'),
    path('ucp/', costos.ucp, name='ucp'),
    path('cif/', costos.cif, name='cif'),
    path('cmo/', costos.cmo, name='cmo'),
    path('costo-total/', costos.costo_total, name='costo_total'),
]