window.formatHelpers = (function () {
    function formatRutInput(input) {
        let value = input.value.replace(/[^0-9kK]/g, '').toUpperCase();
        if (value.length > 9) value = value.slice(0, 9);
        if (value.length > 1) {
            let body = value.slice(0, -1);
            let dv = value.slice(-1);
            body = body.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
            input.value = `${body}-${dv}`;
        } else {
            input.value = value;
        }
    }

    function bindRutInput(selector) {
        document.querySelectorAll(selector).forEach(function (inp) {
            inp.addEventListener('input', function () { formatRutInput(inp); });
        });
    }

    function formatPhone(input) {
        let value = input.value.replace(/\D/g, '');
        if (value.startsWith('56')) value = value.substring(2);
        value = value.substring(0, 9);
        if (value.length > 5)      input.value = value.replace(/(\d{1})(\d{4})(\d+)/, '$1 $2 $3');
        else if (value.length > 1) input.value = value.replace(/(\d{1})(\d+)/, '$1 $2');
        else                       input.value = value;
    }

    function bindPhoneInput(selector) {
        document.querySelectorAll(selector).forEach(function (inp) {
            inp.addEventListener('input', function () { formatPhone(inp); });
        });
    }

    function formatMoneyInput(input) {
        if (input.dataset.formatted === '1') return;
        let value = input.value.replace(/\D/g, '');
        input.value = value === '' ? '' : parseInt(value, 10).toLocaleString('es-CL');
        input.dataset.formatted = '1';
    }

    function bindMoneyInput(selector) {
        document.querySelectorAll(selector).forEach(function (input) {
            formatMoneyInput(input);
            input.addEventListener('input', function () {
                let value = input.value.replace(/\D/g, '');
                input.value = value === '' ? '' : parseInt(value, 10).toLocaleString('es-CL');
            });
        });
    }

    function parseMoney(value) {
        return parseInt(String(value).replace(/\D/g, ''), 10) || 0;
    }

    function getMoneyInputValue(id) {
        return parseMoney(document.getElementById(id).value);
    }

    return {
        formatRutInput: formatRutInput,
        bindRutInput: bindRutInput,
        formatPhone: formatPhone,
        bindPhoneInput: bindPhoneInput,
        formatMoneyInput: formatMoneyInput,
        bindMoneyInput: bindMoneyInput,
        parseMoney: parseMoney,
        getMoneyInputValue: getMoneyInputValue
    };
})();
