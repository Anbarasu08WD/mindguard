// Analytics & Chart.js Integration
document.addEventListener("DOMContentLoaded", function () {
    const moodCanvas = document.getElementById("moodTrendChart");
    const stressEnergyCanvas = document.getElementById("stressEnergyChart");
    const distributionCanvas = document.getElementById("moodDistributionChart");

    if (!window.analyticsData) {
        return;
    }

    const data = window.analyticsData;

    // 1. Mood Trend Chart
    if (moodCanvas && data.labels.length > 0) {
        const moodLabels = {
            1: "Very Low",
            2: "Sad",
            3: "Neutral",
            4: "Happy",
            5: "Very Happy"
        };

        new Chart(moodCanvas, {
            type: "line",
            data: {
                labels: data.labels,
                datasets: [{
                    label: "Emotional State",
                    data: data.mood_scores,
                    borderColor: "#00685f",
                    backgroundColor: "rgba(0, 104, 95, 0.12)",
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2.5,
                    pointBackgroundColor: "#00685f",
                    pointRadius: 4.5,
                    pointHoverRadius: 6,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 1,
                        max: 5,
                        ticks: {
                            stepSize: 1,
                            callback: function (val) {
                                return moodLabels[val] || val;
                            }
                        },
                        grid: {
                            color: "#eae1da",
                        }
                    },
                    x: {
                        grid: {
                            display: false,
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return "Mood: " + (moodLabels[ctx.raw] || ctx.raw);
                            }
                        }
                    }
                }
            }
        });
    }

    // 2. Stress & Energy Comparison Chart
    if (stressEnergyCanvas && data.labels.length > 0) {
        new Chart(stressEnergyCanvas, {
            type: "bar",
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: "Stress Level (1-10)",
                        data: data.stress_levels,
                        backgroundColor: "rgba(220, 107, 115, 0.8)",
                        borderRadius: 6,
                        borderSkipped: false,
                    },
                    {
                        label: "Energy Level (1-10)",
                        data: data.energy_levels,
                        backgroundColor: "rgba(118, 185, 176, 0.8)",
                        borderRadius: 6,
                        borderSkipped: false,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 0,
                        max: 10,
                        ticks: { stepSize: 2 },
                        grid: { color: "#eae1da" }
                    },
                    x: {
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            boxWidth: 14,
                            usePointStyle: true,
                        }
                    }
                }
            }
        });
    }

    // 3. Mood Distribution Pie/Doughnut Chart
    if (distributionCanvas && data.mood_distribution) {
        const dist = data.mood_distribution;
        const labels = Object.keys(dist);
        const counts = Object.values(dist);

        const totalEntries = counts.reduce((a, b) => a + b, 0);

        if (totalEntries > 0) {
            new Chart(distributionCanvas, {
                type: "doughnut",
                data: {
                    labels: labels,
                    datasets: [{
                        data: counts,
                        backgroundColor: [
                            "#006947", // Very Happy
                            "#2fa89b", // Happy
                            "#4b41e1", // Neutral
                            "#d99a3d", // Sad
                            "#ba1a1a", // Very Low
                        ],
                        borderWidth: 2,
                        borderColor: "#FFFFFF"
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "68%",
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: {
                                boxWidth: 12,
                                usePointStyle: true,
                            }
                        }
                    }
                }
            });
        }
    }
});
