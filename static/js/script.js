// Auto-dismiss flash messages after a few seconds
document.addEventListener("DOMContentLoaded", function () {
    var alerts = document.querySelectorAll(".alert");
    alerts.forEach(function (alertEl) {
        setTimeout(function () {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 6000);
    });
});

// Live score validation on the result-entry form (CA max 30, exam max 70).
// The server checks again on submit, so this is only for quick feedback.
document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("score-form");
    if (!form) return;

    var inputs = form.querySelectorAll("input[data-max]");
    var buttons = form.querySelectorAll("button[type=submit]");

    function isBad(input) {
        var raw = input.value.trim();
        if (raw === "") return true;
        var value = Number(raw);
        return !isFinite(value) || value < 0 || value > Number(input.dataset.max);
    }

    function refresh() {
        var anyBad = false;
        inputs.forEach(function (input) {
            var bad = isBad(input);
            var touched = input.dataset.touched === "1" || input.classList.contains("is-invalid");
            var feedback = input.parentElement.querySelector(".score-feedback");
            anyBad = anyBad || bad;
            input.classList.toggle("is-invalid", bad && touched);
            if (feedback && bad && touched) {
                feedback.textContent = "Invalid " + input.dataset.label + ": enter a number from 0 to " + input.dataset.max + ".";
            }
        });
        buttons.forEach(function (button) { button.disabled = anyBad; });
    }

    inputs.forEach(function (input) {
        input.addEventListener("input", function () {
            input.dataset.touched = "1";
            refresh();
        });
    });
    refresh();
});
