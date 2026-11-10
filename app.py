import hmac
import os
import re
import secrets
import tempfile
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

import services
from database import close_db, ensure_database, get_db, register_cli, init_db
from services import (
    BULAN,
    BULAN_SINGKAT,
    HARI,
    HARI_SINGKAT,
    format_clock,
    format_date,
    format_date_short,
    format_datetime,
    format_range,
    get_settings,
    now_local,
    relative_day,
)

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"

# Vercel/Lambda menyediakan filesystem read-only kecuali direktori temp.
IS_SERVERLESS = bool(
    os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
)
DATA_DIR = Path(tempfile.gettempdir()) / "idb_room" if IS_SERVERLESS else INSTANCE_DIR


def load_secret_key():
    for directory in (DATA_DIR, INSTANCE_DIR):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / "secret_key"
            if path.exists():
                return path.read_text().strip()
            key = secrets.token_hex(32)
            path.write_text(key)
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
            return key
        except OSError:
            continue
    return secrets.token_hex(32)


app = Flask(__name__, instance_relative_config=False)
app.config.update(
    SECRET_KEY=os.environ.get("IDB_SECRET_KEY") or load_secret_key(),
    DATABASE=os.environ.get("IDB_DATABASE", str(DATA_DIR / "idb_room.sqlite")),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    MAX_CONTENT_LENGTH=1_000_000,
    TEMPLATES_AUTO_RELOAD=True,
)

app.teardown_appcontext(close_db)
register_cli(app)
ensure_database(app)


@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' "
        "https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
        "script-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'",
    )
    return response


# ---------------------------------------------------------------------------
# Request context, auth, CSRF
# ---------------------------------------------------------------------------


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def load_user():
    g.user = None
    user_id = session.get("user_id")
    if user_id:
        user = get_db().execute(
            "SELECT * FROM users WHERE id = ? AND active = 1", (user_id,)
        ).fetchone()
        if user:
            g.user = user
        else:
            session.pop("user_id", None)

    if request.method == "POST":
        token = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
        expected = session.get("csrf")
        if not token or not expected or not hmac.compare_digest(token, expected):
            abort(400, description="Sesi formulir kedaluwarsa. Muat ulang halaman lalu coba lagi.")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        if g.user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def safe_next(target):
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/"):
        return None
    return target


@app.context_processor
def inject_globals():
    db = get_db()
    unread = services.unread_notifications(db, g.user["id"]) if g.user else 0
    settings = get_settings(db) if g.user else None
    return {
        "now": now_local(),
        "today": now_local().date(),
        "unread_count": unread,
        "campus_settings": settings,
        "active_endpoint": request.endpoint,
    }


@app.template_filter("tgl")
def filter_date(value):
    return format_date(value)


@app.template_filter("tgl_singkat")
def filter_date_short(value):
    return format_date_short(value)


@app.template_filter("jam")
def filter_clock(value):
    return format_clock(value)


@app.template_filter("rentang")
def filter_range(value):
    return format_range(value[0], value[1])


@app.template_filter("waktu")
def filter_datetime(value):
    return format_datetime(value)


@app.template_filter("inisial")
def filter_initials(value):
    return services.initials(value)


@app.template_filter("gedung")
def filter_building(value):
    return services.building_key(value)


@app.template_filter("bulan")
def filter_month(value):
    if isinstance(value, str):
        value = date.fromisoformat(value)
    return BULAN_SINGKAT[value.month - 1]


@app.template_filter("status_state")
def filter_status_state(row):
    return services.booking_state(row)


@app.template_filter("relatif")
def filter_relative(value):
    return relative_day(value)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    username = ""
    error = None
    next_target = request.args.get("next") or request.form.get("next") or ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""
        if not username or not password:
            error = "Masukkan email dan kata sandi untuk melanjutkan."
        else:
            db = get_db()
            user = db.execute(
                "SELECT * FROM users WHERE lower(username) = ? OR lower(email) = ?",
                (username, username),
            ).fetchone()
            if not user or not user["active"] or not check_password_hash(user["password_hash"], password):
                error = "Email atau kata sandi tidak cocok. Periksa kembali lalu coba lagi."
            else:
                session.clear()
                session["user_id"] = user["id"]
                session["csrf"] = secrets.token_urlsafe(32)
                session.permanent = True
                target = safe_next(request.args.get("next") or request.form.get("next"))
                return redirect(target or url_for("dashboard"))
    return render_template("login.html", username=username, error=error, next_target=next_target)


@app.post("/logout")
@login_required
def logout():
    session.clear()
    flash("Anda telah keluar dari sistem.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard and rooms
# ---------------------------------------------------------------------------


@app.route("/")
@login_required
def dashboard():
    today = now_local().date()
    if g.user["role"] == "admin":
        return redirect(url_for("admin_dashboard"))
    db = get_db()
    organization_id = g.user["organization_id"]
    stats = services.org_stats(db, organization_id)
    upcoming = services.organization_agenda(db, organization_id, limit=4)
    all_rooms = db.execute("SELECT * FROM rooms WHERE active = 1 ORDER BY sort_order").fetchall()
    room_states = [(room, services.room_now_state(db, room)) for room in all_rooms]
    available = [item for item in room_states if item[1]["key"] == "available"][:3]
    in_use = [item for item in room_states if item[1]["key"] == "in_use"][:2]
    today_agenda = services.agenda_for_day(db, today.isoformat())[:5]
    return render_template(
        "dashboard.html",
        stats=stats,
        upcoming=upcoming,
        available=available,
        in_use=in_use,
        today_agenda=today_agenda,
        room_states=room_states,
    )


@app.route("/ruangan")
@login_required
def rooms():
    db = get_db()
    query_text = (request.args.get("q") or "").strip()
    building = (request.args.get("gedung") or "").strip()
    sql = "SELECT * FROM rooms WHERE active = 1"
    params = []
    if query_text:
        sql += " AND (code LIKE ? OR name LIKE ? OR kind LIKE ?)"
        term = f"%{query_text}%"
        params.extend([term, term, term])
    if building:
        sql += " AND building = ?"
        params.append(building)
    sql += " ORDER BY sort_order"
    rows = db.execute(sql, params).fetchall()
    room_states = [(room, services.room_now_state(db, room)) for room in rows]
    buildings = [
        row[0]
        for row in db.execute(
            "SELECT DISTINCT building FROM rooms WHERE active = 1 ORDER BY building"
        ).fetchall()
    ]
    return render_template(
        "rooms.html",
        room_states=room_states,
        buildings=buildings,
        query_text=query_text,
        building=building,
    )


@app.route("/ruangan/<int:room_id>")
@login_required
def room_detail(room_id):
    today = now_local().date()
    db = get_db()
    room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if not room:
        abort(404)
    day_value = request.args.get("tanggal") or today.isoformat()
    try:
        selected = date.fromisoformat(day_value)
    except ValueError:
        selected = today
    bookings = services.bookings_for_room_day(db, room_id, selected.isoformat())
    settings = get_settings(db)
    board = []
    now_marker = None
    now = now_local()
    for booking in bookings:
        board.append({"kind": "booking", "row": booking})
    if selected == now.date():
        current = now.strftime("%H:%M")
        marker = {"kind": "now", "time": current}
        insert_at = len(board)
        for index, item in enumerate(board):
            if item["row"]["start_time"] > current:
                insert_at = index
                break
        board.insert(insert_at, marker)
        now_marker = current
    return render_template(
        "room_detail.html",
        room=room,
        selected=selected,
        bookings=bookings,
        settings=settings,
        state=services.room_now_state(db, room),
        board=board,
        now_marker=now_marker,
        prev_day=selected - timedelta(days=1),
        next_day=selected + timedelta(days=1),
    )


@app.route("/kalender")
@login_required
def calendar_view():
    today = now_local().date()
    db = get_db()
    month_value = request.args.get("bulan")
    try:
        year, month = [int(part) for part in month_value.split("-")]
        anchor = date(year, month, 1)
    except (AttributeError, ValueError):
        anchor = today.replace(day=1)
    if month_value is None:
        anchor = today.replace(day=1)
    room_id = request.args.get("ruangan", type=int)
    summary = services.calendar_month(db, anchor.year, anchor.month, room_id)
    selected_value = request.args.get("tanggal")
    try:
        selected = date.fromisoformat(selected_value) if selected_value else today
    except ValueError:
        selected = today
    weeks = services.month_matrix(anchor.year, anchor.month)
    agenda = services.agenda_for_day(db, selected.isoformat(), room_id)
    room_rows = db.execute("SELECT * FROM rooms WHERE active = 1 ORDER BY sort_order").fetchall()
    previous_month = (anchor - timedelta(days=1)).replace(day=1)
    next_month = (anchor + timedelta(days=32)).replace(day=1)
    return render_template(
        "calendar.html",
        anchor=anchor,
        weeks=weeks,
        summary=summary,
        selected=selected,
        agenda=agenda,
        rooms=room_rows,
        room_id=room_id,
        previous_month=previous_month,
        next_month=next_month,
        weekdays=HARI_SINGKAT,
        month_label=f"{services.month_name(anchor.month)} {anchor.year}",
    )


# ---------------------------------------------------------------------------
# Reservations (organization)
# ---------------------------------------------------------------------------


def _reservation_form_context(room_id=None, day=None):
    today = now_local().date()
    db = get_db()
    room_rows = db.execute("SELECT * FROM rooms WHERE active = 1 ORDER BY sort_order").fetchall()
    grouped = {}
    for room in room_rows:
        grouped.setdefault(room["building"], []).append(room)
    settings = get_settings(db)
    return {
        "rooms_grouped": grouped,
        "settings": settings,
        "selected_room": room_id,
        "selected_date": day or today.isoformat(),
        "min_date": today.isoformat(),
        "max_date": (today + timedelta(days=settings["max_advance_days"])).isoformat(),
    }


def _validate_reservation_form(form):
    today = now_local().date()
    errors = {}
    db = get_db()
    settings = get_settings(db)
    values = {
        "room_id": form.get("room_id") or "",
        "custom_room": (form.get("custom_room") or "").strip(),
        "date": form.get("date") or "",
        "start_time": form.get("start_time") or "",
        "end_time": form.get("end_time") or "",
        "purpose": (form.get("purpose") or "").strip(),
        "borrower_type": (form.get("borrower_type") or "mahasiswa").strip(),
        "identity_number": (form.get("identity_number") or "").strip(),
        "pic_name": (form.get("pic_name") or "").strip(),
        "pic_phone": (form.get("pic_phone") or "").strip(),
    }

    borrower_type, borrower_name_label, identity_label = services.borrower_labels(
        values["borrower_type"]
    )
    if values["borrower_type"] not in ("mahasiswa", "dosen"):
        errors["borrower_type"] = "Pilih jenis peminjam."

    if values["room_id"] == "other":
        if len(values["custom_room"]) < 3:
            errors["custom_room"] = "Tuliskan nama ruangan yang ingin dipakai (minimal 3 karakter)."
        room = None
    elif values["room_id"]:
        try:
            room = db.execute(
                "SELECT * FROM rooms WHERE id = ? AND active = 1", (int(values["room_id"]),)
            ).fetchone()
        except ValueError:
            room = None
        if not room:
            errors["room_id"] = "Pilih ruangan yang masih aktif."
    else:
        room = None
        errors["room_id"] = "Pilih ruangan terlebih dahulu."

    try:
        chosen_date = date.fromisoformat(values["date"])
    except ValueError:
        chosen_date = None
        errors["date"] = "Pilih tanggal kegiatan."
    if chosen_date:
        if chosen_date < today:
            errors["date"] = "Tanggal kegiatan tidak boleh di masa lalu."
        elif chosen_date > today + timedelta(days=settings["max_advance_days"]):
            errors["date"] = (
                f"Pengajuan paling jauh {settings['max_advance_days']} hari ke depan."
            )

    time_pattern = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
    for field, label in (("start_time", "Jam mulai"), ("end_time", "Jam selesai")):
        if not time_pattern.match(values[field]):
            errors[field] = f"{label} belum diisi dengan benar."

    if not errors.get("start_time") and not errors.get("end_time"):
        start_minutes = services.minutes_of(values["start_time"])
        end_minutes = services.minutes_of(values["end_time"])
        open_minutes = services.minutes_of(settings["open_time"])
        close_minutes = services.minutes_of(settings["close_time"])
        if end_minutes <= start_minutes:
            errors["end_time"] = "Jam selesai harus lebih lambat daripada jam mulai."
        elif start_minutes < open_minutes or end_minutes > close_minutes:
            errors["start_time"] = (
                f"Ruangan hanya dapat dipakai antara {format_clock(settings['open_time'])} "
                f"dan {format_clock(settings['close_time'])} WITA."
            )
        else:
            duration = end_minutes - start_minutes
            if duration < settings["min_duration_minutes"]:
                errors["end_time"] = (
                    f"Durasi minimal {settings['min_duration_minutes']} menit."
                )
            if duration > settings["max_duration_hours"] * 60:
                errors["end_time"] = (
                    f"Durasi maksimal {settings['max_duration_hours']} jam per pengajuan."
                )
        if chosen_date == today and not errors.get("start_time"):
            current = now_local().strftime("%H:%M")
            if values["start_time"] <= current:
                errors["start_time"] = "Untuk hari ini, pilih jam mulai setelah waktu sekarang."

    if len(values["purpose"]) < 10:
        errors["purpose"] = "Jelaskan tujuan kegiatan minimal 10 karakter."
    elif len(values["purpose"]) > 500:
        errors["purpose"] = "Tujuan kegiatan maksimal 500 karakter."

    if len(values["pic_name"]) < 3:
        errors["pic_name"] = f"Tuliskan {borrower_name_label.lower()}."
    identity_digits = re.sub(r"\D", "", values["identity_number"])
    if len(identity_digits) < 6:
        errors["identity_number"] = f"Tuliskan {identity_label} minimal 6 angka."
    elif len(identity_digits) > 20:
        errors["identity_number"] = f"{identity_label} maksimal 20 angka."
    if len(re.sub(r"\D", "", values["pic_phone"])) < 8:
        errors["pic_phone"] = "Tuliskan nomor kontak yang dapat dihubungi (minimal 8 angka)."

    conflicts = []
    if not errors and chosen_date:
        if room:
            conflicts = services.room_conflicts(
                db,
                room["id"],
                values["date"],
                values["start_time"],
                values["end_time"],
                include_pending=True,
            )
        else:
            conflicts = services.custom_room_conflicts(
                db,
                values["custom_room"],
                values["date"],
                values["start_time"],
                values["end_time"],
            )
        if conflicts:
            errors["slot"] = "Jadwal ini bertabrakan dengan pengajuan lain. Pilih waktu lain."

    return values, errors, conflicts, room


@app.route("/reservasi/baru", methods=["GET", "POST"])
@login_required
def reservation_new():
    today = now_local().date()
    if g.user["role"] == "admin":
        flash("Admin tidak membuat pengajuan dari akun ini.", "info")
        return redirect(url_for("admin_dashboard"))
    db = get_db()
    room_id = request.args.get("ruangan", type=int)
    day = request.args.get("tanggal")
    organization = db.execute(
        "SELECT name FROM organizations WHERE id = ?", (g.user["organization_id"],)
    ).fetchone()
    default_name = ""
    if organization and organization["name"] != g.user["name"]:
        default_name = g.user["name"]
    default_type = g.user["borrower_type"] or "mahasiswa"
    if default_type not in ("mahasiswa", "dosen"):
        default_type = "mahasiswa"
    values = {
        "room_id": str(room_id) if room_id else "",
        "custom_room": "",
        "date": day or today.isoformat(),
        "start_time": "",
        "end_time": "",
        "purpose": "",
        "borrower_type": default_type,
        "identity_number": "",
        "pic_name": default_name,
        "pic_phone": g.user["phone"] or "",
    }
    errors = {}
    conflicts = []
    if request.method == "POST":
        values, errors, conflicts, _room = _validate_reservation_form(request.form)
        if not errors:
            payload = {
                "room_id": int(values["room_id"]) if values["room_id"] != "other" else None,
                "custom_room": values["custom_room"] if values["room_id"] == "other" else None,
                "date": values["date"],
                "start_time": values["start_time"],
                "end_time": values["end_time"],
                "purpose": values["purpose"],
                "borrower_type": values["borrower_type"],
                "identity_number": re.sub(r"\D", "", values["identity_number"]),
                "pic_name": values["pic_name"],
                "pic_phone": values["pic_phone"],
            }
            reservation_id, conflicts = services.create_reservation(db, g.user, payload)
            if reservation_id:
                row = services.get_reservation(db, reservation_id)
                flash(
                    f"Permohonan {row['code']} terkirim. Admin akan meninjau jadwal Anda.",
                    "success",
                )
                return redirect(url_for("reservation_detail", reservation_id=reservation_id))
            errors["slot"] = "Jadwal ini baru saja dipesan pengguna lain. Pilih waktu lain."
    context = _reservation_form_context(room_id, values["date"])
    return render_template(
        "reservation_new.html",
        values=values,
        errors=errors,
        conflicts=conflicts,
        **context,
    )


@app.route("/reservasi")
@login_required
def reservations():
    if g.user["role"] == "admin":
        return redirect(url_for("admin_reservations"))
    db = get_db()
    status = request.args.get("status") or "semua"
    if status not in ("semua", "pending", "approved", "completed", "rejected", "cancelled"):
        status = "semua"
    rows = services.list_reservations(
        db, organization_id=g.user["organization_id"], status=status, limit=200
    )
    counts = services.status_counts(db, organization_id=g.user["organization_id"])
    items = [{"row": row, "state": services.booking_state(row)} for row in rows]
    return render_template("reservations.html", items=items, status=status, counts=counts)


@app.route("/reservasi/<int:reservation_id>")
@login_required
def reservation_detail(reservation_id):
    db = get_db()
    row = services.get_reservation(db, reservation_id)
    if not row:
        abort(404)
    if g.user["role"] != "admin" and row["organization_id"] != g.user["organization_id"]:
        abort(403)
    state = services.booking_state(row)
    events = services.reservation_events(db, reservation_id)
    conflicts = []
    pending_conflicts = []
    if row["status"] == "pending" and g.user["role"] == "admin":
        conflicts = services.slot_conflicts(
            db,
            row["room_id"],
            row["custom_room"],
            row["date"],
            row["start_time"],
            row["end_time"],
            exclude_id=row["id"],
            include_pending=False,
        )
        pending_conflicts = [
            item
            for item in services.slot_conflicts(
                db,
                row["room_id"],
                row["custom_room"],
                row["date"],
                row["start_time"],
                row["end_time"],
                exclude_id=row["id"],
                include_pending=True,
            )
            if item["status"] == "pending"
        ]
    settings = get_settings(db)
    can_cancel = row["status"] in ("pending", "approved") and (
        g.user["role"] == "admin"
        or (
            row["organization_id"] == g.user["organization_id"]
            and now_local()
            <= services.start_datetime(row) - timedelta(hours=settings["cancel_deadline_hours"])
        )
    )
    return render_template(
        "reservation_detail.html",
        row=row,
        state=state,
        events=events,
        conflicts=conflicts,
        pending_conflicts=pending_conflicts,
        can_cancel=can_cancel,
    )


@app.post("/reservasi/<int:reservation_id>/batal")
@login_required
def reservation_cancel(reservation_id):
    db = get_db()
    row = services.get_reservation(db, reservation_id)
    if not row:
        abort(404)
    if g.user["role"] != "admin" and row["organization_id"] != g.user["organization_id"]:
        abort(403)
    note = (request.form.get("note") or "").strip() or ("Dibatalkan oleh admin." if g.user["role"] == "admin" else "Dibatalkan oleh pemohon.")
    result = services.cancel_reservation(db, row, g.user, note)
    if result == "ok":
        flash(f"Reservasi {row['code']} dibatalkan. Kalender sudah diperbarui.", "success")
    elif result == "too_late":
        flash("Batas waktu pembatalan untuk reservasi ini sudah lewat.", "error")
    else:
        flash("Reservasi ini tidak dapat dibatalkan lagi.", "error")
    return redirect(url_for("reservation_detail", reservation_id=reservation_id))


@app.route("/api/ketersediaan")
@login_required
def availability_api():
    db = get_db()
    room_value = request.args.get("room_id") or ""
    day = request.args.get("date") or ""
    start = request.args.get("start_time") or ""
    end = request.args.get("end_time") or ""
    try:
        chosen = date.fromisoformat(day)
    except ValueError:
        return jsonify({"ok": False, "message": "Tanggal belum valid."}), 200

    if room_value == "other":
        custom = (request.args.get("custom_room") or "").strip()
        bookings = services.custom_room_day_bookings(db, custom, day) if custom else []
        room_label = custom or "Ruangan lain"
        conflicts = (
            services.custom_room_conflicts(db, custom, day, start, end)
            if custom and start and end
            else []
        )
    else:
        try:
            room = db.execute(
                "SELECT * FROM rooms WHERE id = ? AND active = 1", (int(room_value),)
            ).fetchone()
        except (ValueError, TypeError):
            room = None
        if not room:
            return jsonify({"ok": False, "message": "Pilih ruangan terlebih dahulu."})
        room_label = f"{room['code']} · {room['name']}"
        bookings = services.bookings_for_room_day(db, room["id"], day)
        conflicts = (
            services.room_conflicts(db, room["id"], day, start, end)
            if start and end
            else []
        )

    payload = {
        "ok": True,
        "room": room_label,
        "date": format_date(chosen),
        "buffer_minutes": get_settings(db)["buffer_minutes"],
        "conflicts": [
            {
                "code": row["code"],
                "start": format_clock(row["start_time"]),
                "end": format_clock(row["end_time"]),
                "borrower": row["pic_name"],
                "status": row["status"],
                "status_label": (
                    "Menunggu persetujuan" if row["status"] == "pending" else "Disetujui"
                ),
            }
            for row in conflicts
        ],
        "bookings": [
            {
                "start": format_clock(row["start_time"]),
                "end": format_clock(row["end_time"]),
                "borrower": row["pic_name"],
                "status": row["status"],
                "status_label": (
                    "Menunggu persetujuan" if row["status"] == "pending" else "Disetujui"
                ),
            }
            for row in bookings
        ],
    }
    return jsonify(payload)


@app.route("/notifikasi")
@login_required
def notifications():
    db = get_db()
    rows = db.execute(
        """SELECT n.*, r.code AS reservation_code
           FROM notifications n
           LEFT JOIN reservations r ON r.id = n.reservation_id
           WHERE n.user_id = ?
           ORDER BY n.created_at DESC
           LIMIT 100""",
        (g.user["id"],),
    ).fetchall()
    db.execute(
        "UPDATE notifications SET read_at = ? WHERE user_id = ? AND read_at IS NULL",
        (now_local().isoformat(timespec="seconds"), g.user["id"]),
    )
    return render_template("notifications.html", rows=rows)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


@app.route("/admin")
@admin_required
def admin_dashboard():
    today = now_local().date()
    db = get_db()
    stats = services.room_usage_stats(db)
    pending_raw = services.list_reservations(db, status="pending", ascending=True)
    pending = []
    for row in pending_raw:
        conflicts = services.slot_conflicts(
            db,
            row["room_id"],
            row["custom_room"],
            row["date"],
            row["start_time"],
            row["end_time"],
            exclude_id=row["id"],
            include_pending=True,
        )
        approved = [item for item in conflicts if item["status"] == "approved"]
        waiting = [item for item in conflicts if item["status"] == "pending"]
        pending.append(
            {"row": row, "approved_conflicts": approved, "pending_conflicts": waiting}
        )
    today_agenda = services.agenda_for_day(db, today.isoformat())
    recent = services.list_reservations(
        db, status="semua", date_from=(today - timedelta(days=14)).isoformat(), limit=6
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        pending=pending,
        today_agenda=today_agenda,
        recent=recent,
    )


@app.route("/admin/reservasi")
@admin_required
def admin_reservations():
    db = get_db()
    status = request.args.get("status") or "semua"
    if status not in ("semua", "pending", "approved", "completed", "rejected", "cancelled"):
        status = "semua"
    room_id = request.args.get("ruangan", type=int)
    date_from = request.args.get("dari") or ""
    date_to = request.args.get("sampai") or ""
    query_text = (request.args.get("q") or "").strip()
    rows = services.list_reservations(
        db,
        status=status,
        room_id=room_id,
        date_from=date_from or None,
        date_to=date_to or None,
        query_text=query_text or None,
        limit=300,
    )
    counts = services.status_counts(db, room_id=room_id)
    rooms = db.execute("SELECT * FROM rooms ORDER BY sort_order").fetchall()
    items = [{"row": row, "state": services.booking_state(row)} for row in rows]
    return render_template(
        "admin/reservations.html",
        items=items,
        status=status,
        counts=counts,
        rooms=rooms,
        room_id=room_id,
        date_from=date_from,
        date_to=date_to,
        query_text=query_text,
    )


@app.post("/admin/reservasi/<int:reservation_id>/keputusan")
@admin_required
def admin_decision(reservation_id):
    db = get_db()
    row = services.get_reservation(db, reservation_id)
    if not row:
        abort(404)
    action = request.form.get("action")
    if action not in ("approve", "reject"):
        abort(400)
    note = (request.form.get("note") or "").strip()
    if action == "approve" and services.end_datetime(row) < now_local():
        flash("Jadwal pengajuan ini sudah lewat sehingga tidak dapat disetujui.", "error")
        return redirect(url_for("reservation_detail", reservation_id=reservation_id))
    if action == "approve":
        result, approved_conflicts, pending_conflicts = services.decide_reservation(
            db, row, action, note, g.user
        )
        if result == "conflict":
            labels = []
            for item in approved_conflicts:
                labels.append(f"{item['code']} (disetujui)")
            for item in pending_conflicts:
                labels.append(f"{item['code']} (menunggu)")
            if approved_conflicts:
                guidance = "Slot sudah dipakai reservasi yang disetujui. Tolak permohonan atau minta pemohon memilih waktu lain."
            else:
                guidance = "Selesaikan pengajuan lain terlebih dahulu (tolak atau setujui) agar tidak ada dua persetujuan pada slot yang sama."
            flash(
                "Belum bisa disetujui: jadwal bertabrakan dengan "
                + ", ".join(labels)
                + ". "
                + guidance,
                "error",
            )
            return redirect(url_for("reservation_detail", reservation_id=reservation_id))
        if result == "not_pending":
            flash("Pengajuan ini sudah diproses admin lain.", "info")
            return redirect(url_for("reservation_detail", reservation_id=reservation_id))
        flash(f"Reservasi {row['code']} disetujui. Pemohon telah diberi notifikasi.", "success")
    else:
        if not note:
            note = "Tidak disetujui oleh admin."
        services.decide_reservation(db, row, action, note, g.user)
        flash(f"Reservasi {row['code']} ditolak dengan catatan.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/ruangan")
@admin_required
def admin_rooms():
    db = get_db()
    query_text = (request.args.get("q") or "").strip()
    sql = "SELECT * FROM rooms"
    params = []
    if query_text:
        sql += " WHERE code LIKE ? OR name LIKE ? OR building LIKE ? OR kind LIKE ?"
        term = f"%{query_text}%"
        params.extend([term, term, term, term])
    sql += " ORDER BY sort_order"
    rooms = db.execute(sql, params).fetchall()
    counts = {
        row["id"]: db.execute(
            "SELECT COUNT(*) FROM reservations WHERE room_id = ?", (row["id"],)
        ).fetchone()[0]
        for row in rooms
    }
    return render_template(
        "admin/rooms.html", rooms=rooms, counts=counts, query_text=query_text
    )


@app.route("/admin/ruangan/baru", methods=["GET", "POST"])
@admin_required
def admin_room_new():
    values = {"code": "", "name": "", "building": "", "floor": "", "kind": "", "description": ""}
    errors = {}
    if request.method == "POST":
        values, errors = _validate_room_form(request.form, None)
        if not errors:
            db = get_db()
            sort_order = db.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM rooms").fetchone()[0]
            db.execute(
                """INSERT INTO rooms (code, name, building, floor, kind, description, active, sort_order, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                (
                    values["code"].upper(),
                    values["name"],
                    values["building"],
                    values["floor"],
                    values["kind"],
                    values["description"],
                    sort_order,
                    now_local().isoformat(timespec="seconds"),
                ),
            )
            flash(f"Ruangan {values['name']} ditambahkan.", "success")
            return redirect(url_for("admin_rooms"))
    return render_template("admin/room_form.html", values=values, errors=errors, room=None)


@app.route("/admin/ruangan/<int:room_id>/ubah", methods=["GET", "POST"])
@admin_required
def admin_room_edit(room_id):
    db = get_db()
    room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if not room:
        abort(404)
    values = dict(room)
    errors = {}
    if request.method == "POST":
        values, errors = _validate_room_form(request.form, room_id)
        if not errors:
            db.execute(
                """UPDATE rooms SET code = ?, name = ?, building = ?, floor = ?, kind = ?, description = ?
                   WHERE id = ?""",
                (
                    values["code"].upper(),
                    values["name"],
                    values["building"],
                    values["floor"],
                    values["kind"],
                    values["description"],
                    room_id,
                ),
            )
            flash(f"Ruangan {values['name']} diperbarui.", "success")
            return redirect(url_for("admin_rooms"))
    return render_template("admin/room_form.html", values=values, errors=errors, room=room)


def _validate_room_form(form, room_id):
    db = get_db()
    values = {
        "code": (form.get("code") or "").strip(),
        "name": (form.get("name") or "").strip(),
        "building": (form.get("building") or "").strip(),
        "floor": (form.get("floor") or "").strip(),
        "kind": (form.get("kind") or "").strip(),
        "description": (form.get("description") or "").strip(),
    }
    errors = {}
    if not values["code"]:
        errors["code"] = "Kode ruangan wajib diisi."
    else:
        exists = db.execute(
            "SELECT id FROM rooms WHERE lower(code) = lower(?) AND id != ?",
            (values["code"], room_id or 0),
        ).fetchone()
        if exists:
            errors["code"] = "Kode ruangan sudah dipakai."
    if len(values["name"]) < 3:
        errors["name"] = "Nama ruangan minimal 3 karakter."
    if not values["building"]:
        errors["building"] = "Gedung wajib diisi."
    if not values["kind"]:
        errors["kind"] = "Jenis ruangan wajib diisi."
    if len(values["description"]) > 300:
        errors["description"] = "Deskripsi maksimal 300 karakter."
    return values, errors


@app.post("/admin/ruangan/<int:room_id>/status")
@admin_required
def admin_room_status(room_id):
    db = get_db()
    room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if not room:
        abort(404)
    new_status = 0 if room["active"] else 1
    db.execute("UPDATE rooms SET active = ? WHERE id = ?", (new_status, room_id))
    flash(
        f"Ruangan {room['name']} {'diaktifkan' if new_status else 'dinonaktifkan'}.",
        "success",
    )
    return redirect(url_for("admin_rooms"))


@app.route("/admin/pengguna")
@admin_required
def admin_users():
    db = get_db()
    query_text = (request.args.get("q") or "").strip()
    sql = """SELECT u.*, (SELECT COUNT(*) FROM reservations r WHERE r.user_id = u.id) AS total
             FROM users u
             WHERE u.role = 'org'"""
    params = []
    if query_text:
        sql += " AND (u.name LIKE ? OR u.email LIKE ? OR u.username LIKE ?)"
        term = f"%{query_text}%"
        params.extend([term, term, term])
    sql += " ORDER BY u.name"
    rows = db.execute(sql, params).fetchall()
    return render_template("admin/users.html", rows=rows, query_text=query_text)


@app.post("/admin/pengguna/<int:user_id>/status")
@admin_required
def admin_user_status(user_id):
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ? AND role = 'org'", (user_id,)
    ).fetchone()
    if not user:
        abort(404)
    new_status = 0 if user["active"] else 1
    db.execute("UPDATE users SET active = ? WHERE id = ?", (new_status, user_id))
    flash(
        f"Akun {user['name']} {'diaktifkan' if new_status else 'dinonaktifkan'}.",
        "success",
    )
    return redirect(url_for("admin_users"))


@app.post("/admin/pengguna/<int:user_id>/reset")
@admin_required
def admin_user_reset(user_id):
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ? AND role = 'org'", (user_id,)
    ).fetchone()
    if not user:
        abort(404)
    temporary = "idb-" + secrets.token_urlsafe(4)
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(temporary, method="pbkdf2:sha256:600000"), user_id),
    )
    flash(
        f"Kata sandi {user['name']} direset. Kata sandi sementara: {temporary} "
        "(tampilkan sekali ini, minta pengguna segera menggantinya lewat admin).",
        "info",
    )
    return redirect(url_for("admin_users"))


@app.route("/admin/pengaturan", methods=["GET", "POST"])
@admin_required
def admin_settings():
    db = get_db()
    if request.method == "POST":
        errors = []
        try:
            buffer_minutes = int(request.form.get("buffer_minutes") or 0)
            max_advance_days = int(request.form.get("max_advance_days") or 180)
            cancel_deadline_hours = int(request.form.get("cancel_deadline_hours") or 0)
            min_duration = int(request.form.get("min_duration_minutes") or 30)
            max_duration = int(request.form.get("max_duration_hours") or 8)
        except ValueError:
            errors.append("Semua angka harus berupa bilangan bulat.")
            buffer_minutes = max_advance_days = cancel_deadline_hours = None
            min_duration = max_duration = None
        open_time = request.form.get("open_time") or "07:00"
        close_time = request.form.get("close_time") or "22:00"
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", open_time) or not re.match(
            r"^([01]\d|2[0-3]):[0-5]\d$", close_time
        ):
            errors.append("Format jam harus HH:MM.")
        elif services.minutes_of(close_time) <= services.minutes_of(open_time):
            errors.append("Jam tutup harus lebih lambat daripada jam buka.")
        if buffer_minutes is not None and not 0 <= buffer_minutes <= 120:
            errors.append("Jeda persiapan harus antara 0 dan 120 menit.")
        if max_advance_days is not None and not 1 <= max_advance_days <= 365:
            errors.append("Batas pengajuan harus antara 1 dan 365 hari.")
        if cancel_deadline_hours is not None and not 0 <= cancel_deadline_hours <= 168:
            errors.append("Batas pembatalan harus antara 0 dan 168 jam.")
        if min_duration is not None and not 15 <= min_duration <= 240:
            errors.append("Durasi minimal harus antara 15 dan 240 menit.")
        if max_duration is not None and not 1 <= max_duration <= 12:
            errors.append("Durasi maksimal harus antara 1 dan 12 jam.")
        if errors:
            for message in errors:
                flash(message, "error")
        else:
            updates = {
                "buffer_minutes": str(buffer_minutes),
                "max_advance_days": str(max_advance_days),
                "cancel_deadline_hours": str(cancel_deadline_hours),
                "min_duration_minutes": str(min_duration),
                "max_duration_hours": str(max_duration),
                "open_time": open_time,
                "close_time": close_time,
            }
            for key, value in updates.items():
                db.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, value),
                )
            flash("Pengaturan reservasi disimpan.", "success")
            return redirect(url_for("admin_settings"))
    settings = get_settings(db)
    return render_template("admin/settings.html", settings=settings)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


@app.errorhandler(400)
def bad_request(error):
    return render_template("error.html", code=400, title="Permintaan tidak valid", message=str(error.description)), 400


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, title="Tidak punya akses", message="Halaman ini hanya dapat dibuka oleh pengguna yang berwenang."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, title="Halaman tidak ditemukan", message="Tautan yang Anda buka tidak tersedia atau sudah dipindahkan."), 404


@app.errorhandler(500)
def server_error(_error):
    return render_template("error.html", code=500, title="Ada gangguan di server", message="Coba muat ulang halaman. Jika masih gagal, hubungi pengelola sistem."), 500


if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
        host=os.environ.get("IDB_HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5001")),
    )
