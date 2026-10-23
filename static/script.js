document.addEventListener("DOMContentLoaded", () => {
  // Give forms a quick client-side check before they are sent to Flask.
  document.querySelectorAll("form").forEach(form => {
    form.addEventListener("submit", event => {
      const requiredFields = form.querySelectorAll("[required]");
      for (const field of requiredFields) {
        if (!field.value.trim()) {
          event.preventDefault();
          field.focus();
          field.setCustomValidity("Please fill in this field.");
          field.reportValidity();
          field.addEventListener("input", () => field.setCustomValidity(""), { once: true });
          return;
        }
      }
    });
  });

  // Auto-dismiss status messages to keep the page tidy.
  document.querySelectorAll(".flash").forEach(message => {
    setTimeout(() => {
      message.style.transition = "opacity .35s ease";
      message.style.opacity = "0";
      setTimeout(() => message.remove(), 400);
    }, 5000);
  });
});
