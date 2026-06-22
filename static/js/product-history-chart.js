document.addEventListener("DOMContentLoaded", function () {
    if (typeof Chart === "undefined") return;

    const COLORS = ['#0d6efd', '#198754', '#dc3545', '#ffc107', '#0dcaf0'];
    let priceChartInstance = null;

    window.showHistory = async function (prodId, prodName) {
        const modal = new bootstrap.Modal(document.getElementById('chartModal'));
        document.getElementById('chartModalTitle').innerText = 'Fluctuación de Precio: ' + prodName;
        modal.show();

        const res = await fetch(`/admin/api/productos/${prodId}/historial`);
        const data = await res.json();

        const zonas = [...new Set(data.map(d => d.zona))];
        const fechas = [...new Set(data.map(d => d.fecha.split(' ')[0]))].sort();

        const datasets = zonas.map((zona, index) => {
            let lastPrice = 0;
            const dataPoints = fechas.map(f => {
                const hits = data.filter(d => d.zona === zona && d.fecha.startsWith(f));
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
    };
});
