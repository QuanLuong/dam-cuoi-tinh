(function () {
  // Đếm ngược tới ngày cưới
  var cd = document.querySelector(".seg, .cd");
  if (cd) {
    var target = new Date(cd.dataset.date).getTime();
    var el = { d: document.getElementById("d"), h: document.getElementById("h"),
               m: document.getElementById("m"), s: document.getElementById("s") };
    var tick = function () {
      var t = Math.max(0, target - Date.now()) / 1000;
      el.d.textContent = String(Math.floor(t / 86400)).padStart(2, "0");
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

  // Xác nhận tham dự -> Google Sheet (qua Google Apps Script)
  var form = document.querySelector(".rsvp-card");
  if (form) {
    var msg = form.querySelector(".rsvp-msg");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var fd = new FormData(form);
      if (!String(fd.get("ten") || "").trim()) { msg.textContent = "Bạn cho chúng mình biết tên nhé."; return; }
      if (!fd.get("tham_du")) { msg.textContent = "Bạn chọn giúp chúng mình một lựa chọn tham dự nhé."; return; }
      if (!form.dataset.url) { msg.textContent = "Chức năng xác nhận đang được chuẩn bị, bạn quay lại sau nhé!"; return; }
      fd.append("khach_moi", form.dataset.guest || "(trang chung)");
      fd.append("trang", location.href);
      var btn = form.querySelector(".send");
      btn.disabled = true; msg.textContent = "Đang gửi…";
      fetch(form.dataset.url, { method: "POST", mode: "no-cors", body: new URLSearchParams(fd) })
        .then(function () {
          form.classList.add("done");
          msg.textContent = fd.get("tham_du") === "Sẽ tham dự"
            ? "Cảm ơn " + fd.get("ten") + "! Hẹn gặp bạn trong ngày vui nhé ♥"
            : "Cảm ơn " + fd.get("ten") + " đã gửi lời nhắn tới chúng mình ♥";
        })
        .catch(function () { msg.textContent = "Gửi chưa được, bạn thử lại giúp chúng mình nhé."; })
        .then(function () { btn.disabled = false; });
    });
  }

  // Nhạc nền: phát từ lần chạm/cuộn đầu tiên (trình duyệt chặn tự phát), nút ở góc trái dưới
  var mb = document.querySelector(".music");
  if (mb) {
    var audio = new Audio(mb.dataset.src);
    audio.loop = true; audio.preload = "auto"; audio.volume = 0.7;
    var userOff = false, noteTimer = null, notesBox = mb.querySelector(".notes");
    var glyphs = ["♪", "♫", "♩", "♬"];
    var spawn = function () {
      var n = document.createElement("i");
      n.textContent = glyphs[Math.floor(Math.random() * glyphs.length)];
      n.style.setProperty("--dx", (Math.random() * 30 - 15) + "px");
      notesBox.appendChild(n);
      setTimeout(function () { n.remove(); }, 2700);
    };
    var setUi = function (on) {
      mb.classList.toggle("on", on); mb.setAttribute("aria-pressed", on);
      clearInterval(noteTimer);
      if (on) { spawn(); noteTimer = setInterval(spawn, 700); }
    };
    var play = function () { return audio.play().then(function () { setUi(true); }).catch(function () {}); };
    var pause = function () { audio.pause(); setUi(false); };
    mb.addEventListener("click", function (e) {
      e.stopPropagation();
      if (audio.paused) { userOff = false; play(); } else { userOff = true; pause(); }
    });
    var kick = function () {
      if (!userOff && audio.paused) play();
      ["pointerdown", "touchstart", "keydown", "scroll"].forEach(function (ev) { window.removeEventListener(ev, kick); });
    };
    ["pointerdown", "touchstart", "keydown", "scroll"].forEach(function (ev) { window.addEventListener(ev, kick, { passive: true }); });
    play();  // thử tự phát ngay (trình duyệt cho phép thì nhạc chạy luôn)
    // Màn hình "Mở thiệp": chạm 1 lần là phát nhạc ngay (lách chặn tự phát của điện thoại)
    var gate = document.querySelector(".gate");
    if (gate) {
      document.body.classList.add("locked");
      gate.addEventListener("click", function () {
        userOff = false; play();
        gate.classList.add("open"); document.body.classList.remove("locked");
        setTimeout(function () { gate.remove(); }, 1000);
      });
    }
    // tạm dừng nhạc khi xem video cưới, phát lại khi video dừng
    var vid = document.querySelector("video");
    if (vid) {
      vid.addEventListener("play", function () { if (!audio.paused) { pause(); vid._resume = true; } });
      vid.addEventListener("pause", function () { if (vid._resume && !userOff) { vid._resume = false; play(); } });
    }
    document.addEventListener("visibilitychange", function () {
      if (document.hidden && !audio.paused) { pause(); audio._bg = true; }
      else if (!document.hidden && audio._bg) { audio._bg = false; if (!userOff) play(); }
    });
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
