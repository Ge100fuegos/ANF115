from django.urls import path
from ChivoBits_app.views import estadosFinancieros

urlpatterns = [
    path('estadosFinancieros/', estadosFinancieros.financiero, name='estadosFinancieros'),

    path('ajustesContables/', estadosFinancieros.ajustes_contables, name='ajustes_contables'),
    path('ajustes/crear/', estadosFinancieros.crear_ajuste, name='crear_ajuste'),
    path('ajustes/cerrar-periodo/', estadosFinancieros.cerrar_periodo, name='cerrar_periodo'),
    path('generar-estados/', estadosFinancieros.generar_estados_financieros, name='generar_estados_financieros'),
    path('balanceComprobacion/', estadosFinancieros.balance_comprobacion, name='balance_comprobacion'),

    path('estado-resultados/', estadosFinancieros.estado_resultados, name='estado_resultados'),
    path('estado-capital/', estadosFinancieros.estado_capital, name='estado_capital'),
    path('balance-general/', estadosFinancieros.balance_general, name='balance_general'),

]