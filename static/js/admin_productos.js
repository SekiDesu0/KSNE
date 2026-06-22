document.addEventListener("DOMContentLoaded", function () {
    window.formatHelpers.bindMoneyInput('.money-input');

    const editModal = document.getElementById('editProductModal');
    if (editModal) {
        editModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            if (!button || !button.hasAttribute('data-id')) return;

            const id = button.getAttribute('data-id');
            const name = button.getAttribute('data-name');
            const price = button.getAttribute('data-price');
            const commission = button.getAttribute('data-commission');
            const zonaId = button.getAttribute('data-zona');

            const form = editModal.querySelector('#editProductForm');
            form.action = `/admin/productos/edit/${id}`;

            editModal.querySelector('#edit_name').value = name;
            editModal.querySelector('#edit_price').value = price;
            editModal.querySelector('#edit_commission').value = commission;
            editModal.querySelector('#edit_zona_id').value = zonaId;

            editModal.querySelectorAll('.money-input').forEach(input => {
                input.dispatchEvent(new Event('input'));
            });
        });
    }

    const searchInput = document.getElementById('searchProduct');
    const productRows = document.querySelectorAll('.product-row');

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const term = this.value.toLowerCase();
            productRows.forEach(row => {
                const name = row.cells[0].textContent.toLowerCase();
                row.style.display = name.includes(term) ? '' : 'none';
            });
        });
    }

    window.toggleNuevoComplementoInput = function(prodId, selectEl) {
        const wrapper = document.getElementById(`nuevo_comp_wrapper_${prodId}`);
        if (wrapper) {
            if (selectEl.value === '__nuevo__') {
                wrapper.style.display = 'block';
                wrapper.querySelector('input').setAttribute('required', 'required');
            } else {
                wrapper.style.display = 'none';
                wrapper.querySelector('input').removeAttribute('required');
            }
        }
    };
});
