(() => {
  const button = document.getElementById("location-button");
  const form = document.getElementById("attendance-form");
  const status = document.getElementById("location-status");
  if (!button || !form) return;

  button.addEventListener("click", () => {
    if (!navigator.geolocation) {
      status.textContent = "Geolocation is not supported by this browser.";
      return;
    }
    button.disabled = true;
    status.textContent = "Getting your current location…";
    navigator.geolocation.getCurrentPosition(
      (position) => {
        document.getElementById("latitude").value = position.coords.latitude;
        document.getElementById("longitude").value = position.coords.longitude;
        document.getElementById("accuracy").value = position.coords.accuracy;
        status.textContent = `Location acquired (accuracy ±${Math.round(position.coords.accuracy)} m).`;
        form.submit();
      },
      (error) => {
        status.textContent = `Location failed: ${error.message}`;
        button.disabled = false;
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  });
})();
