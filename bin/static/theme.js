(function () {
  try {
    var t = localStorage.getItem("digest-theme");
    if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
    localStorage.removeItem("digest-read"); localStorage.removeItem("digest-view");   // from the old star map
  } catch (e) {}
})();
