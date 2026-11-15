// Admin dashboard charts (aggregate data only)
document.addEventListener("DOMContentLoaded", function () {
    const data = window.adminChartData;
    if (!data || typeof Chart === "undefined") return;

    const common = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 7 } },
            y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#eae1da" } }
        }
    };

    const signups = document.getElementById("signupsChart");
    if (signups) {
        new Chart(signups, {
            type: "bar",
            data: { labels: data.signups.labels, datasets: [{ label: "New accounts", data: data.signups.values, backgroundColor: "#00685f", borderRadius: 6 }] },
            options: common
        });
    }

    const events = document.getElementById("eventsChart");
    if (events) {
        new Chart(events, {
            type: "line",
            data: {
                labels: data.events.labels,
                datasets: [{
                    label: "Security events", data: data.events.values,
                    borderColor: "#ba1a1a", backgroundColor: "rgba(186, 26, 26, 0.10)",
                    fill: true, tension: 0.35, pointRadius: 3, borderWidth: 2
                }]
            },
            options: common
        });
    }
});
