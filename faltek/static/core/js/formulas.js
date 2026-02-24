function applyColorCondition(bar, actual, required) {
    if (actual < required) {
        bar.style.backgroundColor = "red";
    } else {
        bar.style.backgroundColor = "green";
    }
}
