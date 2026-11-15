// Mood tracker interaction script
document.addEventListener("DOMContentLoaded", function () {
    // Mood emoji card selection
    const moodCards = document.querySelectorAll(".mood-option-card");
    const moodInput = document.getElementById("selectedMoodInput");

    moodCards.forEach(function (card) {
        card.addEventListener("click", function () {
            moodCards.forEach(c => c.classList.remove("selected"));
            this.classList.add("selected");
            const moodVal = this.getAttribute("data-mood");
            if (moodInput) {
                moodInput.value = moodVal;
            }
        });
    });

    // Stress slider dynamic value update
    const stressSlider = document.getElementById("stressLevelSlider");
    const stressDisplay = document.getElementById("stressLevelDisplay");
    if (stressSlider && stressDisplay) {
        stressSlider.addEventListener("input", function () {
            stressDisplay.textContent = this.value;
        });
    }

    // Energy slider dynamic value update
    const energySlider = document.getElementById("energyLevelSlider");
    const energyDisplay = document.getElementById("energyLevelDisplay");
    if (energySlider && energyDisplay) {
        energySlider.addEventListener("input", function () {
            energyDisplay.textContent = this.value;
        });
    }
});
