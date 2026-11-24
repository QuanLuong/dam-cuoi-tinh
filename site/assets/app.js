(function () {
  // Đếm ngược tới ngày cưới
  var cd = document.querySelector(".cd");
  if (cd) {
    var target = new Date(cd.dataset.date).getTime();
    var el = { d: document.getElementById("d"), h: document.getElementById("h"),
               m: document.getElementById("m"), s: document.getElementById("s") };
    var tick = function () {
      var t = Math.max(0, target - Date.now()) / 1000;
      el.d.textContent = Math.floor(t / 86400);
      el.h.textContent = String(Math.floor(t / 3600) % 24).padStart(2, "0");
      el.m.textContent = String(Math.floor(t / 60) % 60).padStart(2, "0");
      el.s.textContent = String(Math.floor(t) % 60).padStart(2, "0");
    };
    tick(); setInterval(tick, 1000);
  }

  // Xem ảnh lớn
  var lb = document.getElementById("lb");
  if (lb && lb.showModal) {
    var img = lb.querySelector("img");
    document.querySelectorAll(".ph").forEach(function (b) {
      b.addEventListener("click", function () { img.src = b.dataset.full; lb.showModal(); });
    });
    lb.addEventListener("click", function () { lb.close(); });
  }
})();
