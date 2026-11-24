from django.urls import path
from ChivoBits_app.views import contaGeneral
from ChivoBits_app.views import pronosticos
from ChivoBits_app.views import ratios
from ChivoBits_app.views import analisis_vh
from ChivoBits_app.views import dupont_proforma
from ChivoBits_app.views import reporte

urlpatterns = [
    path('libroMayor/', contaGeneral.libro, name='libroMayor'),
        path("ratios/<int:pk>/reporte/", reporte.reporte_analisis, name="reporte_analisis"),
    path('catalogoCuentas/', contaGeneral.catalogo_cuentas, name='catalogoCuentas'),
    path('catalogoCuentas/nueva/', contaGeneral.crear_cuenta, name='crear_cuenta'),
    path('catalogoCuentas/importar/', contaGeneral.catalogo_importar, name='catalogo_importar'),
path('catalogoCuentas/plantilla/', contaGeneral.catalogo_plantilla, name='catalogo_plantilla'),
    path('libro-mayor/', contaGeneral.libro_mayor, name='libro_mayor'),
    path('crear-periodo/', contaGeneral.crear_periodo_contable, name='crear_periodo_contable'),
    path('crear-transaccion/', contaGeneral.crear_transaccion, name='crear_transaccion'),
    path('detalle-transaccion/<int:numero_transaccion>/', contaGeneral.detalle_transaccion, name='detalle_transaccion'),
    path('menu/', contaGeneral.menu_conta, name='menu_conta'),
    path("pronosticos/", pronosticos.pronostico_lista, name="pronostico_lista"),
    path("pronosticos/nueva/", pronosticos.crear_manual, name="pronostico_crear_manual"),
    path("pronosticos/importar/", pronosticos.importar_excel, name="pronostico_importar"),
    path("pronosticos/<int:pk>/", pronosticos.pronostico_detalle, name="pronostico_detalle"),
    path("pronosticos/<int:pk>/eliminar/", pronosticos.pronostico_eliminar, name="pronostico_eliminar"),
    

        path("ratios/<int:pk>/dupont/", dupont_proforma.dupont_detalle, name="dupont_detalle"),
    path("ratios/<int:pk>/proforma/", dupont_proforma.proforma_detalle, name="proforma_detalle"),
    path("ratios/<int:pk>/proforma/importar/", dupont_proforma.proforma_importar, name="proforma_importar"),
    path("ratios/<int:pk>/proforma/plantilla/", dupont_proforma.proforma_plantilla, name="proforma_plantilla"),

    path("ratios/", ratios.ratios_lista, name="ratios_lista"),
path("ratios/nuevo/", ratios.ratios_crear, name="ratios_crear"),
path("ratios/<int:pk>/", ratios.ratios_detalle, name="ratios_detalle"),
path("ratios/<int:pk>/eliminar/", ratios.ratios_eliminar, name="ratios_eliminar"),
path("ratios/<int:pk>/periodo/nuevo/", ratios.ratios_periodo, name="ratios_periodo_nuevo"),
path("ratios/<int:pk>/periodo/<int:periodo_id>/", ratios.ratios_periodo, name="ratios_periodo_editar"),
path("ratios/<int:pk>/periodo/<int:periodo_id>/eliminar/", ratios.ratios_periodo_eliminar, name="ratios_periodo_eliminar"),
path("ratios/<int:pk>/importar/", ratios.ratios_importar, name="ratios_importar"),
path("ratios/<int:pk>/plantilla/", ratios.ratios_plantilla, name="ratios_plantilla"),

path("ratios/<int:pk>/vertical-horizontal/", analisis_vh.vh_detalle, name="vh_detalle"),
path("ratios/<int:pk>/vertical-horizontal/cargar/", analisis_vh.vh_cargar, name="vh_cargar"),
path("ratios/<int:pk>/vertical-horizontal/<str:estado>/base/", analisis_vh.vh_cambiar_base, name="vh_cambiar_base"),
path("ratios/<int:pk>/vertical-horizontal/<str:estado>/eliminar/", analisis_vh.vh_eliminar, name="vh_eliminar"),
]