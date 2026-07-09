document.addEventListener("DOMContentLoaded", function () {
    window.formatHelpers.bindMoneyInput('.money-input');

    const companionSelect = document.getElementById('companion_select');
    if (companionSelect) {
        companionSelect.addEventListener('change', function () {
            const timeDiv = document.getElementById('companion_times_div');
            const compIn = document.getElementById('comp_in');
            const compOut = document.getElementById('comp_out');
            if (this.value) {
                timeDiv.style.display = 'block';
                compIn.required = true;
                compOut.required = true;
            } else {
                timeDiv.style.display = 'none';
                compIn.required = false;
                compOut.required = false;
                compIn.value = '';
                compOut.value = '';
            }
        });
    }

    function getVal(id) {
        return window.formatHelpers.getMoneyInputValue(id);
    }

    function checkWarnings() {
        const totalProductos = displayTotalProductos ? (parseInt(displayTotalProductos.dataset.raw) || 0) : 0;
        const totalDeclarado = getVal('total_general');
        const gastos = getVal('gastos');
        const efectivo = getVal('venta_efectivo');

        let warnings = [];
        if ((totalProductos > 0 || totalDeclarado > 0) && totalProductos !== totalDeclarado) {
            warnings.push("El <strong>Total Venta por Productos</strong> no coincide con el <strong>Total Ventas Declaradas</strong>.");
        }
        if (gastos > efectivo) {
            warnings.push("El <strong>Monto de Gastos</strong> es mayor que el <strong>Efectivo</strong> declarado.");
        }

        const warningContainer = document.getElementById('discrepancy_warning');
        const warningText = document.getElementById('discrepancy_text');
        if (warnings.length > 0) {
            warningText.innerHTML = warnings.join("<br>");
            warningContainer.style.display = 'block';
        } else {
            warningContainer.style.display = 'none';
        }
    }

    const inputsCantidad = document.querySelectorAll('input[name^="qty_"]');
    const displayTotalProductos = document.getElementById('total_productos_calc');

    function calcularVentaProductos() {
        if (!displayTotalProductos) return;
        let granTotal = 0;
        const filas = document.querySelectorAll('tbody tr');

        filas.forEach(fila => {
            const inputQty = fila.querySelector('input[name^="qty_"]');
            if (inputQty) {
                if (parseInt(inputQty.value) < 0) inputQty.value = 0;
                const cantidad = parseInt(inputQty.value) || 0;
                const precioTexto = fila.cells[1].innerText.replace(/\D/g, '');
                const precio = parseInt(precioTexto) || 0;
                granTotal += (cantidad * precio);
            }
        });
        displayTotalProductos.textContent = granTotal.toLocaleString('es-CL');
        displayTotalProductos.dataset.raw = granTotal;
        checkWarnings();
    }

    inputsCantidad.forEach(input => {
        input.addEventListener('keydown', function (e) {
            if (['Backspace', 'Tab', 'ArrowLeft', 'ArrowRight', 'Delete', 'Enter'].includes(e.key) || e.ctrlKey || e.metaKey) return;
            if (e.key < '0' || e.key > '9') e.preventDefault();
        });

        input.addEventListener('input', function () {
            this.value = this.value.replace(/\D/g, '');
            calcularVentaProductos();
        });
    });

    const inputsVenta = document.querySelectorAll('.sale-input');
    const displayDigital = document.getElementById('total_digital');
    const displayGeneral = document.getElementById('total_general');

    function calcularTotales() {
        const debito = getVal('venta_debito');
        const credito = getVal('venta_credito');
        const mp = getVal('venta_mp');
        const efectivo = getVal('venta_efectivo');

        const totalDigital = debito + credito + mp;
        const totalGeneral = totalDigital + efectivo;

        if (displayDigital) displayDigital.value = totalDigital.toLocaleString('es-CL');
        if (displayGeneral) displayGeneral.value = totalGeneral.toLocaleString('es-CL');

        checkWarnings();
    }

    inputsVenta.forEach(input => {
        input.addEventListener('input', calcularTotales);
    });

    document.querySelectorAll('.money-input').forEach(function (input) {
        input.addEventListener('keydown', function (e) {
            if (['Backspace', 'Tab', 'ArrowLeft', 'ArrowRight', 'Delete', 'Enter'].includes(e.key) || e.ctrlKey || e.metaKey) return;
            if (e.key < '0' || e.key > '9') e.preventDefault();
        });

        input.addEventListener('focus', function () {
            if (this.value === '0') this.value = '';
        });

        input.addEventListener('blur', function () {
            if (this.value.trim() === '' || this.value.trim() === '0') this.value = '0';
            calcularTotales();
        });

        input.addEventListener('input', function () {
            let value = this.value.replace(/\D/g, '');
            if (value !== '') this.value = parseInt(value, 10).toLocaleString('es-CL');
            calcularTotales();
        });
    });

    const submitModal = document.getElementById('confirmSubmitModal');
    const mainForm = document.querySelector('form');
    const alertModalEl = document.getElementById('globalAlertModal');
    const alertModal = alertModalEl ? new bootstrap.Modal(alertModalEl) : null;

    function mostrarError(mensaje) {
        const body = document.getElementById('globalAlertModalBody');
        if (body) body.textContent = mensaje;
        if (alertModal) alertModal.show();
    }

    function validarFormulario() {
        if (!mainForm) return false;
        const requiredInputs = mainForm.querySelectorAll('[required]');
        let valid = true;

        requiredInputs.forEach(input => {
            const isMoney = input.classList.contains('money-input');
            if (!input.value.trim() || (isMoney && input.value === '')) {
                input.classList.add('is-invalid');
                valid = false;
            } else {
                input.classList.remove('is-invalid');
            }
        });
        return valid;
    }

    if (submitModal) {
        const confirmBtn = submitModal.querySelector('button[type="submit"]');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', function (e) {
                e.preventDefault();
                if (validarFormulario()) {
                    mainForm.submit();
                } else {
                    const submitInstance = bootstrap.Modal.getInstance(submitModal);
                    if (submitInstance) submitInstance.hide();
                    mostrarError("Por favor, rellena los campos obligatorios (Fecha y Hora) antes de enviar.");
                }
            });
        }
    }

    if (mainForm) {
        mainForm.addEventListener('submit', function (e) {
            const requiredInputs = this.querySelectorAll('[required]');
            let valid = true;

            requiredInputs.forEach(input => {
                const isMoney = input.classList.contains('money-input');
                if (!input.value.trim() || (isMoney && input.value === '')) {
                    input.classList.add('is-invalid');
                    valid = false;
                } else {
                    input.classList.remove('is-invalid');
                }
            });

            if (!valid) {
                e.preventDefault();
                if (alertModalEl) {
                    const inst = bootstrap.Modal.getOrCreateInstance(alertModalEl);
                    mostrarError("Por favor, rellena todos los campos obligatorios antes de enviar.");
                    inst.show();
                } else {
                    alert("Por favor, rellena todos los campos obligatorios.");
                }
            }
        });
    }

    document.querySelectorAll('.money-input').forEach(input => {
        if (!input.value.trim()) input.value = '0';
    });
});
