document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.sidebar-submenu').forEach((submenu) => {
        if (!submenu.querySelector('.active')) return;

        const boton = document.querySelector(`[data-bs-target="#${submenu.id}"]`);
        submenu.classList.add('show');

        if (boton) {
            boton.classList.remove('collapsed');
            boton.classList.add('tiene-activo');
            boton.setAttribute('aria-expanded', 'true');
        }
    });
});


document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.sidebar-submenuDos').forEach((submenu) => {
        if (!submenu.querySelector('.active')) return;

        const boton = document.querySelector(`[data-bs-target="#${submenu.id}"]`);
        submenu.classList.add('show');

        if (boton) {
            boton.classList.remove('collapsed');
            boton.classList.add('tiene-activo');
            boton.setAttribute('aria-expandedDos', 'true');
        }
    });
});