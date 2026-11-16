document.addEventListener('DOMContentLoaded', function() {
    // Filtros de búsqueda
    const buscarInput = document.getElementById('buscarCuenta');
    const filtroTipo = document.getElementById('filtroTipo');
    const filtroNivel = document.getElementById('filtroNivel');
    const filas = document.querySelectorAll('tbody tr');
    
    function aplicarFiltros() {
        const textoBusqueda = buscarInput.value.toLowerCase();
        const tipoSeleccionado = filtroTipo.value;
        const nivelSeleccionado = filtroNivel.value;
        
        filas.forEach(fila => {
            const textoFila = fila.textContent.toLowerCase();
            const tipoFila = fila.querySelector('td:nth-child(4)')?.textContent.toLowerCase() || '';
            const nivelFila = fila.querySelector('td:nth-child(3)')?.textContent.toLowerCase() || '';
            
            const coincideTexto = textoBusqueda === '' || textoFila.includes(textoBusqueda);
            const coincideTipo = tipoSeleccionado === '' || tipoFila.includes(tipoSeleccionado);
            const coincideNivel = nivelSeleccionado === '' || nivelFila.includes(nivelSeleccionado);
            
            if (coincideTexto && coincideTipo && coincideNivel) {
                fila.style.display = '';
            } else {
                fila.style.display = 'none';
            }
        });
    }
    
    buscarInput.addEventListener('input', aplicarFiltros);
    filtroTipo.addEventListener('change', aplicarFiltros);
    filtroNivel.addEventListener('change', aplicarFiltros);
});