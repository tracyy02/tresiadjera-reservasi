(() => {
  "use strict";

  if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    });
  }

  // Avoid duplicating the primary CTA that is already visible in the page header
  const fab = document.querySelector(".fab");
  if (
    fab &&
    (document.querySelector(".page-actions .btn") ||
      document.querySelector("[data-reservation-form]") ||
      document.querySelector(".error-page"))
  ) {
    fab.remove();
  }

  // ---------------------------------------------------------------------------
  // Flash messages
  // ---------------------------------------------------------------------------
  document.querySelectorAll("[data-dismiss-alert]").forEach((button) => {
    button.addEventListener("click", () => {
      const alert = button.closest(".alert");
      if (alert) alert.remove();
    });
  });

  const loginError = document.getElementById("login-error");
  if (loginError) loginError.focus();

  // ---------------------------------------------------------------------------
  // Password visibility
  // ---------------------------------------------------------------------------
  document.querySelectorAll("[data-toggle-password]").forEach((button) => {
    const input = button.closest(".input-with-action")?.querySelector("input");
    if (!input) return;
    button.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.setAttribute("aria-pressed", String(show));
      button.setAttribute("aria-label", show ? "Sembunyikan kata sandi" : "Tampilkan kata sandi");
      const eyeShow = button.querySelector("[data-eye-show]");
      const eyeHide = button.querySelector("[data-eye-hide]");
      if (eyeShow) eyeShow.hidden = show;
      if (eyeHide) eyeHide.hidden = !show;
    });
  });

  // ---------------------------------------------------------------------------
  // Dialogs — native <dialog> handles focus trapping and Esc
  // ---------------------------------------------------------------------------
  document.querySelectorAll("[data-dialog-open]").forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const dialog = document.getElementById(trigger.dataset.dialogOpen);
      if (dialog && typeof dialog.showModal === "function") dialog.showModal();
    });
  });

  document.querySelectorAll("dialog").forEach((dialog) => {
    dialog.querySelectorAll("[data-dialog-close]").forEach((button) => {
      button.addEventListener("click", () => dialog.close());
    });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  });

  // ---------------------------------------------------------------------------
  // Confirm destructive form submissions with a specific consequence
  // ---------------------------------------------------------------------------
  const confirmDialog = document.getElementById("confirm-dialog");
  let pendingForm = null;
  if (confirmDialog) {
    const messageEl = confirmDialog.querySelector("[data-confirm-message]");
    const acceptButton = confirmDialog.querySelector("[data-confirm-accept]");
    document.querySelectorAll("form[data-confirm]").forEach((formEl) => {
      formEl.addEventListener("submit", (event) => {
        if (formEl.dataset.confirmed === "1") return;
        event.preventDefault();
        if (messageEl) messageEl.textContent = formEl.dataset.confirm || "Lanjutkan tindakan ini?";
        if (acceptButton) {
          acceptButton.textContent = formEl.dataset.confirmLabel || "Ya, lanjutkan";
          acceptButton.className =
            formEl.dataset.confirmTone === "primary" ? "btn btn--primary" : "btn btn--danger";
        }
        pendingForm = formEl;
        confirmDialog.showModal();
      });
    });
    acceptButton?.addEventListener("click", () => {
      if (!pendingForm) return;
      const target = pendingForm;
      pendingForm = null;
      confirmDialog.close();
      target.dataset.confirmed = "1";
      target.requestSubmit();
    });
  }

  // ---------------------------------------------------------------------------
  // Character count
  // ---------------------------------------------------------------------------
  document.querySelectorAll("[data-char-count]").forEach((counter) => {
    const field = counter.closest(".field")?.querySelector("textarea");
    if (!field) return;
    const update = () => {
      counter.textContent = `${field.value.length}/${field.maxLength}`;
    };
    update();
    field.addEventListener("input", update);
  });

  // ---------------------------------------------------------------------------
  // Reservation form: custom room + availability + summary
  // ---------------------------------------------------------------------------
  const form = document.querySelector("[data-reservation-form]");
  if (!form) return;

  const roomSelect = form.querySelector("[data-room-select]");
  const customField = form.querySelector("[data-custom-room]");
  const customInput = customField?.querySelector("input");
  const dateInput = form.querySelector("#date");
  const startInput = form.querySelector("#start_time");
  const endInput = form.querySelector("#end_time");
  const panel = form.querySelector("[data-availability]");
  const statusEl = form.querySelector("[data-availability-status]");
  const detailEl = form.querySelector("[data-availability-detail]");
  const submitButton = form.querySelector("[data-submit]");
  const endpoint = form.dataset.availabilityUrl;

  const borrowerType = form.querySelector("[data-borrower-type]");
  const borrowerNameLabel = form.querySelector("[data-borrower-name-label]");
  const borrowerIdLabel = form.querySelector("[data-borrower-id-label]");
  const identityInput = form.querySelector("#identity_number");
  const identityHint = form.querySelector("[data-identity-hint]");

  const updateBorrowerLabels = () => {
    const isDosen = borrowerType?.value === "dosen";
    if (borrowerNameLabel) borrowerNameLabel.textContent = isDosen ? "Nama dosen" : "Nama mahasiswa";
    if (borrowerIdLabel) borrowerIdLabel.textContent = isDosen ? "NIDN/NIP" : "NIM";
    if (identityHint) {
      identityHint.textContent = isDosen
        ? "NIDN atau NIP dosen."
        : "NIM peminjam (organisasi mahasiswa juga memakai NIM pengurus).";
    }
    if (identityInput) {
      identityInput.placeholder = isDosen ? "contoh: 0012345678" : "contoh: 2023010101";
      identityInput.inputMode = "numeric";
    }
  };

  const summaryRoom = form.querySelector("[data-summary-room]");
  const summaryDate = form.querySelector("[data-summary-date]");
  const summaryTime = form.querySelector("[data-summary-time]");
  const summaryDuration = form.querySelector("[data-summary-duration]");

  let controller = null;
  let timer = null;

  const formatClock = (value) => value.replace(":", ".");
  const formatDate = (value) => {
    if (!value) return "—";
    const date = new Date(`${value}T00:00:00`);
    return new Intl.DateTimeFormat("id-ID", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    }).format(date);
  };
  const durationLabel = (start, end) => {
    if (!start || !end) return "—";
    const [sh, sm] = start.split(":").map(Number);
    const [eh, em] = end.split(":").map(Number);
    const total = eh * 60 + em - (sh * 60 + sm);
    if (total <= 0) return "—";
    const hours = Math.floor(total / 60);
    const minutes = total % 60;
    if (hours && minutes) return `${hours} jam ${minutes} menit`;
    if (hours) return `${hours} jam`;
    return `${minutes} menit`;
  };

  const updateSummary = () => {
    const selected = roomSelect.options[roomSelect.selectedIndex];
    if (summaryRoom) {
      summaryRoom.textContent =
        roomSelect.value === "other"
          ? customInput?.value || "Ruangan lain"
          : roomSelect.value
            ? selected.textContent.trim().replace(/\s*\([^)]*\)$/, "")
            : "Belum dipilih";
    }
    if (summaryDate) summaryDate.textContent = formatDate(dateInput.value);
    if (summaryTime) {
      summaryTime.textContent =
        startInput.value && endInput.value
          ? `${formatClock(startInput.value)}–${formatClock(endInput.value)} WITA`
          : "—";
    }
    if (summaryDuration) summaryDuration.textContent = durationLabel(startInput.value, endInput.value);
  };

  const toggleCustomRoom = () => {
    const isOther = roomSelect.value === "other";
    if (customField) customField.hidden = !isOther;
    if (customInput) {
      customInput.disabled = !isOther;
      customInput.required = isOther;
    }
    updateSummary();
  };

  const resetAvailability = (message) => {
    if (!panel) return;
    panel.classList.remove("is-ok", "is-conflict", "is-loading");
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.removeAttribute("aria-describedby");
    }
    if (statusEl) statusEl.textContent = message;
    if (detailEl) detailEl.replaceChildren();
  };

  const addBookingLine = (booking) => {
    if (!detailEl) return;
    const row = document.createElement("div");
    row.className = "availability-booking";
    const time = document.createElement("strong");
    time.textContent = `${booking.start}–${booking.end}`;
    const org = document.createElement("span");
    org.textContent = booking.organization;
    const status = document.createElement("span");
    status.className = `badge badge--${booking.status === "pending" ? "warning" : "success"}`;
    status.textContent = booking.status_label;
    row.append(time, org, status);
    detailEl.appendChild(row);
  };

  const checkAvailability = async () => {
    updateSummary();
    if (!endpoint || !panel) return;

    const room = roomSelect.value;
    const day = dateInput.value;
    const start = startInput.value;
    const end = endInput.value;

    if (!room || !day || !start || !end) {
      resetAvailability("Pilih ruangan, tanggal, jam mulai, dan jam selesai untuk memeriksa bentrok.");
      return;
    }
    if (end <= start) {
      resetAvailability("Jam selesai harus lebih lambat daripada jam mulai.");
      return;
    }
    if (room === "other" && !(customInput?.value || "").trim()) {
      resetAvailability("Isi nama ruangan lain agar ketersediaan dapat diperiksa.");
      return;
    }

    if (controller) controller.abort();
    controller = new AbortController();
    panel.classList.remove("is-ok", "is-conflict");
    panel.classList.add("is-loading");
    if (statusEl) statusEl.textContent = "Memeriksa ketersediaan…";

    const params = new URLSearchParams({
      room_id: room,
      date: day,
      start_time: start,
      end_time: end,
    });
    if (room === "other") params.set("custom_room", customInput.value.trim());

    try {
      const response = await fetch(`${endpoint}?${params.toString()}`, {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("request failed");
      const data = await response.json();
      panel.classList.remove("is-loading");
      if (detailEl) detailEl.replaceChildren();

      if (!data.ok) {
        resetAvailability(data.message || "Ketersediaan belum dapat diperiksa.");
        return;
      }

      if (data.conflicts.length) {
        panel.classList.add("is-conflict");
        const count = data.conflicts.length;
        statusEl.textContent = `Tidak tersedia: bentrok dengan ${count} pengajuan pada ${data.date}. Pilih waktu lain sebelum mengirim.`;
        if (submitButton) {
          submitButton.disabled = true;
          submitButton.setAttribute("aria-describedby", "availability-status");
        }
        data.conflicts.forEach(addBookingLine);
      } else {
        panel.classList.add("is-ok");
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.removeAttribute("aria-describedby");
        }
        statusEl.textContent = `Tersedia. Tidak ada bentrok pada ${data.date} untuk ${data.room}.`;
        const others = data.bookings.filter(
          (booking) => booking.end <= start || booking.start >= end
        );
        if (others.length) {
          const label = document.createElement("p");
          label.className = "hint";
          label.textContent = "Jadwal lain pada hari itu:";
          detailEl?.appendChild(label);
          others.forEach(addBookingLine);
        }
      }
    } catch (error) {
      if (error.name === "AbortError") return;
      panel.classList.remove("is-loading");
      resetAvailability("Pemeriksaan ketersediaan gagal. Periksa koneksi lalu coba lagi.");
    }
  };

  const scheduleCheck = () => {
    updateSummary();
    window.clearTimeout(timer);
    timer = window.setTimeout(checkAvailability, 350);
  };

  borrowerType?.addEventListener("change", updateBorrowerLabels);
  updateBorrowerLabels();

  roomSelect?.addEventListener("change", () => {
    toggleCustomRoom();
    scheduleCheck();
  });
  customInput?.addEventListener("input", scheduleCheck);
  [dateInput, startInput, endInput].forEach((input) => {
    input?.addEventListener("change", scheduleCheck);
    input?.addEventListener("input", updateSummary);
  });

  form.addEventListener("submit", (event) => {
    if (panel?.classList.contains("is-conflict")) {
      event.preventDefault();
      if (statusEl) {
        statusEl.tabIndex = -1;
        statusEl.focus();
      }
      return;
    }
    if (submitButton) {
      submitButton.setAttribute("aria-busy", "true");
      submitButton.disabled = true;
      submitButton.textContent = "Mengirim permohonan…";
    }
  });

  toggleCustomRoom();
  updateSummary();
  if (roomSelect?.value && dateInput?.value && startInput?.value && endInput?.value) {
    checkAvailability();
  }
})();
