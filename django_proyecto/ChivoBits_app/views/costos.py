from django.shortcuts import redirect, render


def costo(request):
    return render(request, 'Costos/costo.html')
def ucp(request):
    return render(request, 'costos/UCP.html')
def cif(request):
    return render(request, 'costos/CIF.html')
def cmo(request):
    return render(request, 'costos/CMO.html')
def costo_total(request):
    return render(request, 'costos/costoTotal.html')