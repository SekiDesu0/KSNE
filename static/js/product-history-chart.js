document.addEventListener("DOMContentLoaded", function () {
    if (typeof Chart === "undefined") return;

    const COLORS = ['#0d6efd', '#198754', '#dc3545', '#ffc107', '#0dcaf0'];
    let priceChartInstance = null;
    let rawChartData = [];
    let currentProdId = null;
    let currentProdName = "";

    window.showHistory = async function (prodId, prodName) {
        currentProdId = prodId;
        currentProdName = prodName;

        const modal = new bootstrap.Modal(document.getElementById('chartModal'));
        document.getElementById('chartModalTitle').innerText = 'Fluctuación de Precio: ' + prodName;
        modal.show();

        const res = await fetch(`/admin/api/productos/${prodId}/historial`);
        rawChartData = await res.json();

        // Initialize dates in input fields if not set or reset
        const dates = rawChartData.map(d => d.fecha.split(' ')[0]);
        if (dates.length > 0) {
            document.getElementById('chartFilterDesde').value = dates[0];
            document.getElementById('chartFilterHasta').value = dates[dates.length - 1];
        } else {
            document.getElementById('chartFilterDesde').value = '';
            document.getElementById('chartFilterHasta').value = '';
        }

        renderChart();
    };

    function renderChart() {
        const desde = document.getElementById('chartFilterDesde').value;
        const hasta = document.getElementById('chartFilterHasta').value;

        let filteredData = rawChartData;
        if (desde) {
            filteredData = filteredData.filter(d => d.fecha.split(' ')[0] >= desde);
        }
        if (hasta) {
            filteredData = filteredData.filter(d => d.fecha.split(' ')[0] <= hasta);
        }

        const zonas = [...new Set(filteredData.map(d => d.zona))];
        const fechas = [...new Set(filteredData.map(d => d.fecha.split(' ')[0]))].sort();

        const datasets = zonas.map((zona, index) => {
            let lastPrice = 0;
            const dataPoints = fechas.map(f => {
                const hits = filteredData.filter(d => d.zona === zona && d.fecha.startsWith(f));
                if (hits.length > 0) {
                    lastPrice = hits[hits.length - 1].price;
                }
                return lastPrice;
            });
            return {
                label: zona,
                data: dataPoints,
                borderColor: COLORS[index % COLORS.length],
                backgroundColor: COLORS[index % COLORS.length],
                stepped: true,
                borderWidth: 2
            };
        });

        const ctx = document.getElementById('priceChart').getContext('2d');
        if (priceChartInstance) priceChartInstance.destroy();

        priceChartInstance = new Chart(ctx, {
            type: 'line',
            data: { labels: fechas, datasets: datasets },
            options: {
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: v => '$' + v.toLocaleString('es-CL') }
                    }
                }
            }
        });
    }

    const btnFilter = document.getElementById('btnFilterChart');
    if (btnFilter) {
        btnFilter.addEventListener('click', renderChart);
    }
});
