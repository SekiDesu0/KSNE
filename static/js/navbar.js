document.addEventListener("DOMContentLoaded", function () {
    const brandIcon = document.getElementById("brandIcon");
    if (!brandIcon) return;

    let clickCount = 0;
    let clickResetTimer;

    brandIcon.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();

        clickCount++;
        clearTimeout(clickResetTimer);
        clickResetTimer = setTimeout(() => { clickCount = 0; }, 800);

        if (clickCount >= 5) {
            clickCount = 0;
            clearTimeout(clickResetTimer);

            const originalClass = this.className;
            this.className = "fs-3 me-2 baguette-spin";
            this.innerHTML = "&#129366;";

            setTimeout(() => {
                this.className = originalClass;
                this.innerHTML = "";
            }, 1000);
        }
    });
});
