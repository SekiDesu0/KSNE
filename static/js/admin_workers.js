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

    window.formatHelpers.bindPhoneInput('.phone-input, #phoneInput');

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
