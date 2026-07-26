document.addEventListener("DOMContentLoaded", function () {
  var root = document.documentElement;
  var toggle = document.getElementById("theme-toggle");

  function currentTheme() {
    return root.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function updateLabel() {
    toggle.textContent = currentTheme() === "dark" ? "Light mode" : "Dark mode";
  }

  updateLabel();

  toggle.addEventListener("click", function () {
    var next = currentTheme() === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    updateLabel();
  });
});
