// Dashboard overview script
document.addEventListener("DOMContentLoaded", function () {
    const miniChartCanvas = document.getElementById("dashboardTrendMiniChart");

    if (miniChartCanvas && window.dashboardTrendData && window.dashboardTrendData.labels.length > 0) {
        const trend = window.dashboardTrendData;

        new Chart(miniChartCanvas, {
            type: "line",
            data: {
                labels: trend.labels,
                datasets: [{
                    label: "Mood Score",
                    data: trend.scores,
                    borderColor: "#00685f",
                    backgroundColor: "rgba(0, 104, 95, 0.12)",
                    borderWidth: 2,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 3,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 1,
                        max: 5,
                        display: false,
                    },
                    x: {
                        display: false,
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: true }
                }
            }
        });
    }

    // Modal Activity Start handler
    const activityModal = document.getElementById("activityModal");
    if (activityModal) {
        activityModal.addEventListener("show.bs.modal", function (event) {
            const button = event.relatedTarget;
            const title = button.getAttribute("data-title");
            const category = button.getAttribute("data-category");
            const duration = button.getAttribute("data-duration");
            const desc = button.getAttribute("data-desc");

            document.getElementById("modalActivityTitle").textContent = title;
            document.getElementById("modalActivityCategory").textContent = category;
            document.getElementById("modalActivityDuration").textContent = duration + " mins";
            document.getElementById("modalActivityDesc").textContent = desc;
        });
    }
});
