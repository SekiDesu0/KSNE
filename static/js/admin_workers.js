function toggleOtroBanco(selectEl, wrapperId) {
    const wrapper = document.getElementById(wrapperId);
    if (!wrapper) return;
    wrapper.style.display = selectEl.value === '__otro__' ? '' : 'none';
}

document.addEventListener("DOMContentLoaded", function () {
    const editWorkerModal = document.getElementById('editWorkerModal');
    const confirmResetModal = document.getElementById('confirmResetPass');

    if (editWorkerModal) {
        editWorkerModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            if (!button || !button.hasAttribute('data-id')) return;

            const id = button.getAttribute('data-id');
            const name = button.getAttribute('data-name');

            const editForm = editWorkerModal.querySelector('#editWorkerForm');
            const resetForm = confirmResetModal ? confirmResetModal.querySelector('form') : null;

            editForm.action = "/admin/workers/edit/" + id;
            if (resetForm) resetForm.action = "/admin/workers/reset_password/" + id;

            if (confirmResetModal) {
                confirmResetModal.querySelector('.modal-body').textContent =
                    `¿Estás seguro de generar una nueva contraseña para ${name}? La anterior dejará de funcionar.`;
            }

            editWorkerModal.querySelector('#edit_worker_rut').value = button.getAttribute('data-rut');
            editWorkerModal.querySelector('#edit_worker_name').value = name;
            editWorkerModal.querySelector('#edit_worker_phone').value = button.getAttribute('data-phone');
            editWorkerModal.querySelector('#edit_worker_modulo').value = button.getAttribute('data-modulo');
            editWorkerModal.querySelector('#edit_worker_tipo').value = button.getAttribute('data-tipo');
            const bancoVal = button.getAttribute('data-nombre-banco');
            const bancoSelect = editWorkerModal.querySelector('#edit_worker_nombre_banco');
            const otroWrapper = editWorkerModal.querySelector('#edit_otro_banco_wrapper');
            const otroInput = editWorkerModal.querySelector('#edit_worker_nombre_banco_otro');

            const isCustom = bancoVal && !Array.from(bancoSelect.options).some(o => o.value === bancoVal);
            if (isCustom) {
                bancoSelect.value = '__otro__';
                otroWrapper.style.display = '';
                otroInput.value = bancoVal;
            } else {
                bancoSelect.value = bancoVal;
                otroWrapper.style.display = 'none';
                otroInput.value = '';
            }
            editWorkerModal.querySelector('#edit_worker_numero_cuenta').value = button.getAttribute('data-numero-cuenta');
            editWorkerModal.querySelector('#edit_worker_rut_banco').value = button.getAttribute('data-rut-banco');
            editWorkerModal.querySelector('#edit_worker_tipo_cuenta').value = button.getAttribute('data-tipo-cuenta');
        });
    }

    if (editWorkerModal && confirmResetModal) {
        const btnCancelar = confirmResetModal.querySelector('.btn-secondary');
        const btnCerrarX = confirmResetModal.querySelector('.btn-close');

        const reabrirEdicion = () => {
            const modalEdicion = new bootstrap.Modal(editWorkerModal);
            modalEdicion.show();
        };

        if (btnCancelar) btnCancelar.addEventListener('click', reabrirEdicion);
        if (btnCerrarX)   btnCerrarX.addEventListener('click', reabrirEdicion);
    }

    const rutInput = document.getElementById('rutInput');
    if (rutInput) {
        window.formatHelpers.bindRutInput('#rutInput');
    }
    const addRutInput = document.getElementById('addRutInput');
    if (addRutInput) {
        window.formatHelpers.bindRutInput('#addRutInput');
    }

    window.formatHelpers.bindPhoneInput('.phone-input, #phoneInput, #addPhoneInput');

    const searchInputWorker = document.getElementById('searchWorker');
    const moduleSelectFilter = document.getElementById('filterModule');
    const typeSelectFilter = document.getElementById('filterType');
    const workerRows = document.querySelectorAll('.worker-row');

    function filterWorkers() {
        if (!searchInputWorker) return;
        const searchTerm = searchInputWorker.value.toLowerCase();
        const selectedModule = moduleSelectFilter ? moduleSelectFilter.value : 'all';
        const selectedType = typeSelectFilter ? typeSelectFilter.value : 'all';

        workerRows.forEach(row => {
            const rut = row.cells[0].textContent.toLowerCase();
            const name = row.cells[1].textContent.toLowerCase();
            const rowModule = row.getAttribute('data-modulo');
            const rowType = row.getAttribute('data-tipo');

            const matchesSearch = rut.includes(searchTerm) || name.includes(searchTerm);
            const matchesModule = selectedModule === 'all' || rowModule === selectedModule;
            const matchesType = selectedType === 'all' || rowType === selectedType;

            row.style.display = (matchesSearch && matchesModule && matchesType) ? '' : 'none';
        });
    }

    if (searchInputWorker) searchInputWorker.addEventListener('input', filterWorkers);
    if (moduleSelectFilter) moduleSelectFilter.addEventListener('change', filterWorkers);
    if (typeSelectFilter) typeSelectFilter.addEventListener('change', filterWorkers);
});
