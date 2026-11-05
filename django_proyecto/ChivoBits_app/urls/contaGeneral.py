from django.urls import path
from ChivoBits_app.views import contaGeneral

urlpatterns = [
    path('libroMayor/', contaGeneral.libro, name='libroMayor'),
    path('catalogoCuentas/', contaGeneral.catalogo_cuentas, name='catalogoCuentas'),
    path('libro-mayor/', contaGeneral.libro_mayor, name='libro_mayor'),
    path('crear-periodo/', contaGeneral.crear_periodo_contable, name='crear_periodo_contable'),
    path('crear-transaccion/', contaGeneral.crear_transaccion, name='crear_transaccion'),
    path('detalle-transaccion/<int:numero_transaccion>/', contaGeneral.detalle_transaccion, name='detalle_transaccion'),
    path('menu/', contaGeneral.menu_conta, name='menu_conta'),
]