from django.shortcuts import redirect, render
from ChivoBits_app.models.usuario import *
from django.contrib import messages

def login_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            usuario = Usuario.objects.get(username=username)
            if usuario.check_password(password):
                # Guardar en sesión
                request.session['usuario_id'] = usuario.id
                request.session['username'] = usuario.username
                messages.success(request, f'¡Bienvenido {usuario.username}!')
                return redirect('menu_conta')  # Cambia 'home' por tu vista principal
            else:
                return render(request, 'Usuario/login.html', {'error': 'Contraseña incorrecta'})
        except Usuario.DoesNotExist:
            return render(request, 'Usuario/login.html', {'error': 'Usuario no encontrado'})

    return render(request, 'Usuario/login.html')

def home_view(request):
    # Verificar si está autenticado
    if 'usuario_id' not in request.session:
        return redirect('login')
    
    return render(request, 'Usuario/home.html')  # Tu vista principal

def logout_view(request):
    request.session.flush()
    return redirect('login')