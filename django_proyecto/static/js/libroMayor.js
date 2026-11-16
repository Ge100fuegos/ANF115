    document.addEventListener('DOMContentLoaded', function () {
        // Inicializar tooltips
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl)
        });

        // Filtro por cuenta
        const selectCuenta = document.getElementById('selectCuenta');
        const btnFiltrar = document.getElementById('btnFiltrar');
        const cuentasT = document.querySelectorAll('.cuenta-t');

        function filtrarCuentas() {
            const cuentaSeleccionada = selectCuenta.value;
            const fechaDesde = document.getElementById('fechaDesde').value;
            const fechaHasta = document.getElementById('fechaHasta').value;

            cuentasT.forEach(cuenta => {
                const mostrarCuenta = cuentaSeleccionada === 'todas' || cuenta.getAttribute('data-cuenta') === cuentaSeleccionada;
                cuenta.style.display = mostrarCuenta ? 'block' : 'none';
            });
        }

        btnFiltrar.addEventListener('click', filtrarCuentas);

        // Funcionalidad para ver detalle de transacción
        document.addEventListener('click', function (e) {
            if (e.target.closest('.ver-detalle')) {
                const boton = e.target.closest('.ver-detalle');
                const numeroTransaccion = boton.getAttribute('data-numero');

                fetch(`/contabilidad/detalle-transaccion/${numeroTransaccion}/?periodo_id={{ periodo_seleccionado.id }}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            document.getElementById('detalleNumero').textContent = data.transaccion.numero;
                            document.getElementById('detalleFecha').textContent = data.transaccion.fecha;
                            document.getElementById('detalleDescripcion').textContent = data.transaccion.descripcion;

                            const detalleCuentas = document.getElementById('detalleCuentas');
                            detalleCuentas.innerHTML = '';

                            data.transaccion.cuentas.forEach(cuenta => {
                                const li = document.createElement('li');
                                li.className = 'list-group-item d-flex justify-content-between align-items-center';
                                li.innerHTML = `
                                    <div>
                                        <strong>${cuenta.cuenta}</strong><br>
                                        <small class="text-muted">${cuenta.tipo}</small>
                                    </div>
                                    <span class="badge ${cuenta.tipo === 'DEBE' ? 'bg-success' : 'bg-danger'} rounded-pill">
                                        $ ${parseFloat(cuenta.monto).toFixed(2)}
                                    </span>
                                `;
                                detalleCuentas.appendChild(li);
                            });

                            new bootstrap.Modal(document.getElementById('detalleTransaccionModal')).show();
                        }
                    });
            }
        });

        // Funcionalidad del modal de nueva transacción
        const agregarCuentaBtn = document.getElementById('agregarCuenta');
        const cuentasContainer = document.getElementById('cuentasContainer');
        const formTransaccion = document.getElementById('formTransaccion');

        // Establecer fecha actual por defecto
        document.getElementById('fechaTransaccion').valueAsDate = new Date();

        if (agregarCuentaBtn && cuentasContainer) {
            agregarCuentaBtn.addEventListener('click', function () {
                const nuevaFila = document.querySelector('.cuenta-fila').cloneNode(true);
                const quitarBtn = nuevaFila.querySelector('.quitar-cuenta');
                quitarBtn.disabled = false;

                nuevaFila.querySelector('.select-cuenta').value = '';
                nuevaFila.querySelector('.tipo-movimiento').value = '';
                nuevaFila.querySelector('.monto').value = '';

                cuentasContainer.appendChild(nuevaFila);
                actualizarTotales();
            });

            cuentasContainer.addEventListener('click', function (e) {
                if (e.target.closest('.quitar-cuenta')) {
                    const fila = e.target.closest('.cuenta-fila');
                    if (document.querySelectorAll('.cuenta-fila').length > 1) {
                        fila.remove();
                        actualizarTotales();
                    }
                }
            });

            cuentasContainer.addEventListener('input', actualizarTotales);

            function actualizarTotales() {
                let totalDebe = 0;
                let totalHaber = 0;

                document.querySelectorAll('.cuenta-fila').forEach(fila => {
                    const tipo = fila.querySelector('.tipo-movimiento').value;
                    const monto = parseFloat(fila.querySelector('.monto').value) || 0;

                    if (tipo === 'debe') {
                        totalDebe += monto;
                    } else if (tipo === 'haber') {
                        totalHaber += monto;
                    }
                });

                document.getElementById('totalDebe').textContent = '$ ' + totalDebe.toFixed(2);
                document.getElementById('totalHaber').textContent = '$ ' + totalHaber.toFixed(2);

                const diferencia = totalDebe - totalHaber;
                document.getElementById('diferencia').textContent = '$ ' + Math.abs(diferencia).toFixed(2);

                const estadoBalance = document.getElementById('estadoBalance');
                const btnGuardar = document.getElementById('btnGuardar');

                if (diferencia === 0 && totalDebe > 0) {
                    estadoBalance.className = 'alert alert-success mb-0 w-100';
                    estadoBalance.innerHTML = '<i class="bi bi-check-circle me-2"></i><span>Transacción balanceada</span>';
                    btnGuardar.disabled = false;
                } else {
                    estadoBalance.className = 'alert alert-warning mb-0 w-100';
                    estadoBalance.innerHTML = '<i class="bi bi-exclamation-triangle me-2"></i><span>Transacción desbalanceada</span>';
                    btnGuardar.disabled = true;
                }
            }

            // Enviar formulario de transacción
            formTransaccion.addEventListener('submit', function (e) {
                e.preventDefault();

                const fecha = document.getElementById('fechaTransaccion').value;
                const descripcion = document.getElementById('descripcion').value;
                const cuentasAfectadas = [];

                document.querySelectorAll('.cuenta-fila').forEach(fila => {
                    const cuentaId = fila.querySelector('.select-cuenta').value;
                    const tipo = fila.querySelector('.tipo-movimiento').value;
                    const monto = parseFloat(fila.querySelector('.monto').value);

                    if (cuentaId && tipo && monto > 0) {
                        cuentasAfectadas.push({
                            cuenta_id: cuentaId,
                            tipo: tipo,
                            monto: monto
                        });
                    }
                });

                const data = {
                    fecha: fecha,
                    descripcion: descripcion,
                    cuentas_afectadas: cuentasAfectadas
                };

                fetch('{% url "crear_transaccion" %}', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': '{{ csrf_token }}'
                    },
                    body: JSON.stringify(data)
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('Transacción creada exitosamente');
                            window.location.reload();
                        } else {
                            alert('Error: ' + data.message);
                        }
                    })
                    .catch(error => {
                        alert('Error al crear la transacción');
                        console.error('Error:', error);
                    });
            });
        }
    });