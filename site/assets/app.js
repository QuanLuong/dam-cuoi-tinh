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

  // Cánh hoa rơi nhẹ
  var box = document.querySelector(".petals");
  if (box && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    var n = window.innerWidth < 700 ? 10 : 18;
    for (var i = 0; i < n; i++) {
      var p = document.createElement("i");
      p.className = "petal";
      var sc = 0.6 + Math.random() * 0.8, dur = 11 + Math.random() * 10;
      p.style.left = Math.random() * 100 + "vw";
      p.style.width = 14 * sc + "px"; p.style.height = 18 * sc + "px";
      p.style.animationDuration = dur + "s, " + (3 + Math.random() * 3) + "s";
      p.style.animationDelay = -Math.random() * dur + "s, 0s";
      p.style.opacity = 0.45 + Math.random() * 0.4;
      box.appendChild(p);
    }
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
