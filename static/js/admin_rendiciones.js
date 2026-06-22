document.addEventListener("DOMContentLoaded", function () {
    window.formatHelpers.bindMoneyInput('.money-input');

    window.updateBadge = function (selectElement, badgeId) {
        const option = selectElement.options[selectElement.selectedIndex];
        const tipo = option ? option.getAttribute('data-tipo') : null;
        const badgeDiv = document.getElementById(badgeId);
        if (!badgeDiv) return;

        if (!tipo) {
            badgeDiv.innerHTML = '';
            return;
        }

        const color = (tipo === 'Full Time') ? 'bg-success' : 'bg-secondary';
        badgeDiv.innerHTML = `<span class="badge ${color}">${tipo}</span>`;
    };

    window.toggleCompDiv = function (id, select) {
        const compDiv = document.getElementById(`comp_com_div_${id}`);
        if (compDiv) compDiv.style.display = select.value ? 'flex' : 'none';
        window.updateBadge(select, `badge_comp_${id}`);
        window.updateComisionToggle(select, `cc_${id}`);
    };

    window.toggleComp2Div = function (id, select) {
        const compDiv = document.getElementById(`comp2_com_div_${id}`);
        if (compDiv) compDiv.style.display = select.value ? 'flex' : 'none';
        window.updateBadge(select, `badge_comp2_${id}`);
        window.updateComisionToggle(select, `cc2_${id}`);
    };

    window.updateComisionToggle = function (selectElement, toggleId) {
        const option = selectElement.options[selectElement.selectedIndex];
        const tipoJornada = option ? option.getAttribute('data-tipo') : null;
        const toggleSwitch = document.getElementById(toggleId);

        if (toggleSwitch && tipoJornada) {
            toggleSwitch.checked = (tipoJornada === 'Full Time');
        } else if (toggleSwitch && !selectElement.value) {
            toggleSwitch.checked = false;
        }

        const baseId = toggleId.split('_')[1];
        const targetBadge = toggleId.startsWith('wc') ? `badge_worker_${baseId}` : `badge_comp_${baseId}`;
        window.updateBadge(selectElement, targetBadge);
    };

    window.recalcProductLine = function (input) {
        const qty = parseInt(input.value) || 0;
        const price = parseInt(input.getAttribute('data-price')) || 0;
        const rid = input.getAttribute('data-rid');
        const row = input.closest('tr');

        const lineTotal = qty * price;
        const lineCell = row.querySelector('.item-total-line');
        if (lineCell) lineCell.innerText = '$' + lineTotal.toLocaleString('es-CL');

        const modal = document.getElementById(`editRendicion${rid}`);
        let newSysTotal = 0;
        if (modal) {
            modal.querySelectorAll('.prod-qty-input').forEach(inp => {
                newSysTotal += (parseInt(inp.value) || 0) * (parseInt(inp.getAttribute('data-price')) || 0);
            });
        }
        const sysTotalEl = document.getElementById(`sys_total_${rid}`);
        if (sysTotalEl) sysTotalEl.innerText = '$' + newSysTotal.toLocaleString('es-CL');
    };

    window.calcTotalEdit = function (id) {
        const getVal = (inputId) => window.formatHelpers.getMoneyInputValue(inputId);
        const total = getVal(`edit_debito_${id}`) + getVal(`edit_credito_${id}`)
                    + getVal(`edit_mp_${id}`) + getVal(`edit_efectivo_${id}`);
        const el = document.getElementById(`display_nuevo_total_${id}`);
        if (el) el.innerText = '$' + total.toLocaleString('es-CL');
    };

    const editModals = document.querySelectorAll('[id^="editRendicion"]');
    const editForms = document.querySelectorAll('form[action*="/admin/rendiciones/edit/"]');
    const errorModalEl = document.getElementById('errorPersonaModal');
    const errorModal = errorModalEl ? new bootstrap.Modal(errorModalEl) : null;
    const errorBody = document.getElementById('errorPersonaModalBody');

    editForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            const workerId = this.querySelector('select[name="worker_id"]').value;
            const companionId = this.querySelector('select[name="companion_id"]').value;

            if (companionId && workerId === companionId) {
                e.preventDefault();
                if (errorModal && errorBody) {
                    errorBody.innerHTML = "<strong>Error:</strong> El trabajador titular y el acompañante no pueden ser la misma persona. Por favor, selecciona a alguien más.";
                    errorModal.show();
                } else {
                    alert("Un trabajador no puede ser su propio acompañante. Por favor, corrige la selección.");
                }
            }
        });
    });

    editModals.forEach(modal => {
        modal.addEventListener('show.bs.modal', function () {
            const rid = this.id.replace('editRendicion', '');
            const workerSelect = this.querySelector('select[name="worker_id"]');
            if (workerSelect) window.updateBadge(workerSelect, `badge_worker_${rid}`);

            const compSelect = this.querySelector('select[name="companion_id"]');
            if (compSelect && compSelect.value) window.updateBadge(compSelect, `badge_comp_${rid}`);

            const comp2Select = this.querySelector('select[name="companion2_id"]');
            if (comp2Select && comp2Select.value) window.updateBadge(comp2Select, `badge_comp2_${rid}`);
        });

        modal.addEventListener('hidden.bs.modal', function () {
            const form = this.querySelector('form');
            if (!form) return;
            form.reset();
            const rid = this.id.replace('editRendicion', '');
            window.calcTotalEdit(rid);
            this.querySelectorAll('.prod-qty-input').forEach(inp => window.recalcProductLine(inp));
        });
    });

    const zonaSelect = document.getElementById('zonaSelect');
    const moduloSelect = document.getElementById('moduloSelect');

    if (zonaSelect && moduloSelect) {
        const moduloOptions = Array.from(moduloSelect.options);

        function filterModulos() {
            const selectedZona = zonaSelect.value;
            moduloOptions.forEach(option => {
                if (option.value === "") {
                    option.style.display = '';
                } else if (!selectedZona || option.dataset.zona === selectedZona) {
                    option.style.display = '';
                } else {
                    option.style.display = 'none';
                    if (option.selected) moduloSelect.value = "";
                }
            });
        }

        zonaSelect.addEventListener('change', filterModulos);
        filterModulos();
    }
});
