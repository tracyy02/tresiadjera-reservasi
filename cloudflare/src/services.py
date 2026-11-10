import secrets
from datetime import date, datetime, time, timedelta

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Asia/Makassar")
except Exception:  # pragma: no cover
    from datetime import timezone

    TZ = timezone(timedelta(hours=8))

BULAN = [
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
]

BULAN_SINGKAT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
HARI_SINGKAT = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]

BORROWER_TYPE_LABEL = {
    "mahasiswa": "Mahasiswa",
    "organisasi": "Organisasi mahasiswa",
    "dosen": "Dosen",
}


def borrower_labels(kind):
    kind = "organisasi" if kind == "bem" else (kind or "mahasiswa")
    if kind == "dosen":
        return "Dosen", "Nama dosen", "NIDN/NIP"
    return BORROWER_TYPE_LABEL.get(kind, "Mahasiswa"), "Nama mahasiswa", "NIM"


STATUS_LABEL = {
    "pending": "Menunggu persetujuan",
    "approved": "Disetujui",
    "rejected": "Ditolak",
    "cancelled": "Dibatalkan",
    "in_use": "Sedang digunakan",
    "completed": "Selesai",
    "available": "Tersedia",
    "inactive": "Tidak tersedia",
}

STATUS_TONE = {
    "pending": "warning",
    "approved": "success",
    "rejected": "danger",
    "cancelled": "neutral",
    "in_use": "info",
    "completed": "neutral",
    "available": "success",
    "inactive": "neutral",
}


def now_local():
    return datetime.now(TZ)


def minutes_of(value):
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def time_string(total):
    total = max(0, min(int(total), 23 * 60 + 59))
    return f"{total // 60:02d}:{total % 60:02d}"


def end_datetime(row):
    return datetime.combine(date.fromisoformat(row["date"]), time.fromisoformat(row["end_time"]), tzinfo=TZ)


def start_datetime(row):
    return datetime.combine(date.fromisoformat(row["date"]), time.fromisoformat(row["start_time"]), tzinfo=TZ)


def format_date(value, with_day=True):
    if isinstance(value, str):
        value = date.fromisoformat(value)
    if with_day:
        return f"{HARI[value.weekday()]}, {value.day} {BULAN[value.month - 1]} {value.year}"
    return f"{value.day} {BULAN[value.month - 1]} {value.year}"


def format_date_short(value, with_year=True):
    if isinstance(value, str):
        value = date.fromisoformat(value)
    suffix = f" {value.year}" if with_year else ""
    return f"{value.day} {BULAN_SINGKAT[value.month - 1]}{suffix}"


def format_clock(value):
    return value.replace(":", ".")


def format_range(start, end):
    return f"{format_clock(start)}–{format_clock(end)} WITA"


def format_datetime(value):
    if not value:
        return "—"
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return f"{value.day} {BULAN_SINGKAT[value.month - 1]} {value.year}, {value:%H.%M} WITA"


def relative_day(value, today=None):
    today = today or now_local().date()
    if isinstance(value, str):
        value = date.fromisoformat(value)
    delta = (value - today).days
    if delta == 0:
        return "Hari ini"
    if delta == 1:
        return "Besok"
    if delta == -1:
        return "Kemarin"
    return format_date_short(value)


def get_settings(db):
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    settings = {row["key"]: row["value"] for row in rows}
    return {
        "buffer_minutes": int(settings.get("buffer_minutes", 0)),
        "max_advance_days": int(settings.get("max_advance_days", 180)),
        "open_time": settings.get("open_time", "07:00"),
        "close_time": settings.get("close_time", "22:00"),
        "cancel_deadline_hours": int(settings.get("cancel_deadline_hours", 0)),
        "min_duration_minutes": int(settings.get("min_duration_minutes", 30)),
        "max_duration_hours": int(settings.get("max_duration_hours", 8)),
    }


def overlaps(start_a, end_a, start_b, end_b, buffer_minutes=0):
    first = minutes_of(start_a)
    first_end = minutes_of(end_a)
    second = minutes_of(start_b)
    second_end = minutes_of(end_b)
    return first < second_end + buffer_minutes and first_end + buffer_minutes > second


def room_conflicts(db, room_id, day, start, end, exclude_id=None, include_pending=True, buffer_minutes=None):
    if buffer_minutes is None:
        buffer_minutes = get_settings(db)["buffer_minutes"]
    statuses = ("pending", "approved") if include_pending else ("approved",)
    placeholders = ", ".join("?" for _ in statuses)
    query = f"""
        SELECT r.*, o.name AS organization_name, o.short_name AS organization_short,
               rm.code AS room_code, rm.name AS room_name
        FROM reservations r
        JOIN organizations o ON o.id = r.organization_id
        JOIN rooms rm ON rm.id = r.room_id
        WHERE r.room_id = ? AND r.date = ? AND r.status IN ({placeholders})
    """
    params = [room_id, day, *statuses]
    if exclude_id:
        query += " AND r.id != ?"
        params.append(exclude_id)
    query += " ORDER BY r.start_time"
    rows = db.execute(query, params).fetchall()
    return [row for row in rows if overlaps(start, end, row["start_time"], row["end_time"], buffer_minutes)]


def custom_room_conflicts(db, custom_room, day, start, end, exclude_id=None, include_pending=True, buffer_minutes=None):
    if not custom_room:
        return []
    if buffer_minutes is None:
        buffer_minutes = get_settings(db)["buffer_minutes"]
    statuses = ("pending", "approved") if include_pending else ("approved",)
    placeholders = ", ".join("?" for _ in statuses)
    query = f"""
        SELECT r.*, o.name AS organization_name, o.short_name AS organization_short
        FROM reservations r
        JOIN organizations o ON o.id = r.organization_id
        WHERE r.room_id IS NULL AND lower(r.custom_room) = lower(?)
          AND r.date = ? AND r.status IN ({placeholders})
    """
    params = [custom_room, day, *statuses]
    if exclude_id:
        query += " AND r.id != ?"
        params.append(exclude_id)
    query += " ORDER BY r.start_time"
    rows = db.execute(query, params).fetchall()
    return [row for row in rows if overlaps(start, end, row["start_time"], row["end_time"], buffer_minutes)]


def custom_room_day_bookings(db, custom_room, day, include_pending=True):
    if not custom_room:
        return []
    statuses = ("pending", "approved") if include_pending else ("approved",)
    placeholders = ", ".join("?" for _ in statuses)
    return db.execute(
        f"""SELECT r.*, o.name AS organization_name, o.short_name AS organization_short
           FROM reservations r
           JOIN organizations o ON o.id = r.organization_id
           WHERE r.room_id IS NULL AND lower(r.custom_room) = lower(?)
             AND r.date = ? AND r.status IN ({placeholders})
           ORDER BY r.start_time""",
        (custom_room, day, *statuses),
    ).fetchall()


def slot_conflicts(db, room_id, custom_room, day, start, end, exclude_id=None, include_pending=True, buffer_minutes=None):
    if room_id:
        return room_conflicts(
            db, room_id, day, start, end, exclude_id=exclude_id,
            include_pending=include_pending, buffer_minutes=buffer_minutes
        )
    return custom_room_conflicts(
        db, custom_room, day, start, end, exclude_id=exclude_id,
        include_pending=include_pending, buffer_minutes=buffer_minutes
    )


def bookings_for_room_day(db, room_id, day, include_pending=True):
    statuses = ("pending", "approved") if include_pending else ("approved",)
    placeholders = ", ".join("?" for _ in statuses)
    return db.execute(
        f"""SELECT r.*, o.name AS organization_name, o.short_name AS organization_short
           FROM reservations r
           JOIN organizations o ON o.id = r.organization_id
           WHERE r.room_id = ? AND r.date = ? AND r.status IN ({placeholders})
           ORDER BY r.start_time""",
        (room_id, day, *statuses),
    ).fetchall()


def booking_state(row, now=None):
    now = now or now_local()
    status = row["status"]
    if status == "approved":
        start = start_datetime(row)
        end = end_datetime(row)
        if now < start:
            return "approved"
        if now < end:
            return "in_use"
        return "completed"
    return status


def state_label(state):
    return STATUS_LABEL.get(state, state)


def state_tone(state):
    return STATUS_TONE.get(state, "neutral")


def decoration_for(db, row, now=None):
    state = booking_state(row, now)
    return state_label(state), state_tone(state)


def room_now_state(db, room, now=None):
    now = now or now_local()
    if not room["active"]:
        return {"key": "inactive", "label": "Tidak tersedia", "tone": "neutral", "next": None}
    today = now.date().isoformat()
    rows = db.execute(
        """SELECT * FROM reservations
           WHERE room_id = ? AND date = ? AND status = 'approved'
           ORDER BY start_time""",
        (room["id"], today),
    ).fetchall()
    current_minutes = now.hour * 60 + now.minute
    for row in rows:
        if minutes_of(row["start_time"]) <= current_minutes < minutes_of(row["end_time"]):
            return {
                "key": "in_use",
                "label": "Sedang digunakan",
                "tone": "info",
                "booking": dict(row),
                "next": None,
            }
    upcoming = [row for row in rows if minutes_of(row["start_time"]) > current_minutes]
    next_booking = dict(upcoming[0]) if upcoming else None
    return {
        "key": "available",
        "label": "Tersedia",
        "tone": "success",
        "booking": None,
        "next": next_booking,
    }


def reservation_filters(status, now=None):
    now = now or now_local()
    stamp = now.isoformat(timespec="seconds")
    if status == "pending":
        return "r.status = 'pending'", []
    if status == "rejected":
        return "r.status = 'rejected'", []
    if status == "cancelled":
        return "r.status = 'cancelled'", []
    if status == "approved":
        return "r.status = 'approved' AND (r.date > ? OR (r.date = ? AND r.end_time >= ?))", [
            now.date().isoformat(),
            now.date().isoformat(),
            now.strftime("%H:%M"),
        ]
    if status == "completed":
        return "r.status = 'approved' AND (r.date < ? OR (r.date = ? AND r.end_time < ?))", [
            now.date().isoformat(),
            now.date().isoformat(),
            now.strftime("%H:%M"),
        ]
    if status == "active":
        return "r.status IN ('pending', 'approved')", []
    return "1 = 1", []


def list_reservations(
    db,
    organization_id=None,
    status="semua",
    room_id=None,
    date_from=None,
    date_to=None,
    query_text=None,
    limit=None,
    ascending=False,
):
    where, params = reservation_filters(status)
    clauses = [where]
    if organization_id:
        clauses.append("r.organization_id = ?")
        params.append(organization_id)
    if room_id:
        clauses.append("r.room_id = ?")
        params.append(room_id)
    if date_from:
        clauses.append("r.date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("r.date <= ?")
        params.append(date_to)
    if query_text:
        clauses.append("(r.code LIKE ? OR r.purpose LIKE ? OR o.name LIKE ? OR rm.name LIKE ?)")
        term = f"%{query_text}%"
        params.extend([term, term, term, term])

    direction = "ASC" if ascending else "DESC"
    sql = f"""
        SELECT r.*, o.name AS organization_name, o.short_name AS organization_short,
               rm.code AS room_code, rm.name AS room_name, rm.building AS room_building,
               rm.kind AS room_kind,
               u.name AS requester_name, a.name AS admin_name
        FROM reservations r
        JOIN organizations o ON o.id = r.organization_id
        LEFT JOIN rooms rm ON rm.id = r.room_id
        LEFT JOIN users u ON u.id = r.user_id
        LEFT JOIN users a ON a.id = r.admin_id
        WHERE {' AND '.join(clauses)}
        ORDER BY r.date {direction}, r.start_time {direction}
    """
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return db.execute(sql, params).fetchall()


def status_counts(db, organization_id=None, room_id=None):
    now = now_local()
    base = ["1 = 1"]
    params = []
    if organization_id:
        base.append("r.organization_id = ?")
        params.append(organization_id)
    if room_id:
        base.append("r.room_id = ?")
        params.append(room_id)
    counts = {}
    for key in ("semua", "pending", "approved", "completed", "rejected", "cancelled"):
        clause, extra = reservation_filters(key, now)
        counts[key] = db.execute(
            f"SELECT COUNT(*) FROM reservations r WHERE {' AND '.join(base)} AND {clause}",
            params + extra,
        ).fetchone()[0]
    return counts


def get_reservation(db, reservation_id):
    return db.execute(
        """SELECT r.*, o.name AS organization_name, o.short_name AS organization_short,
                  rm.code AS room_code, rm.name AS room_name, rm.building AS room_building,
                  rm.kind AS room_kind, rm.active AS room_active,
                  u.name AS requester_name, u.username AS requester_username,
                  a.name AS admin_name
           FROM reservations r
           JOIN organizations o ON o.id = r.organization_id
           LEFT JOIN rooms rm ON rm.id = r.room_id
           LEFT JOIN users u ON u.id = r.user_id
           LEFT JOIN users a ON a.id = r.admin_id
           WHERE r.id = ?""",
        (reservation_id,),
    ).fetchone()


def get_reservation_by_code(db, code):
    row = db.execute("SELECT id FROM reservations WHERE code = ?", (code,)).fetchone()
    return get_reservation(db, row["id"]) if row else None


def reservation_events(db, reservation_id):
    return db.execute(
        """SELECT e.*, u.name AS actor_name, o.name AS actor_org
           FROM reservation_events e
           LEFT JOIN users u ON u.id = e.actor_id
           LEFT JOIN organizations o ON o.id = u.organization_id
           WHERE e.reservation_id = ?
           ORDER BY e.created_at, e.id""",
        (reservation_id,),
    ).fetchall()


def log_event(db, reservation_id, actor, action, note=None):
    db.execute(
        """INSERT INTO reservation_events (reservation_id, actor_id, actor_role, action, note, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            reservation_id,
            actor["id"] if actor else None,
            actor["role"] if actor else "system",
            action,
            note,
            now_local().isoformat(timespec="seconds"),
        ),
    )


def notify(db, user_id, reservation_id, title, message):
    db.execute(
        """INSERT INTO notifications (user_id, reservation_id, title, message, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, reservation_id, title, message, now_local().isoformat(timespec="seconds")),
    )


def unread_notifications(db, user_id):
    return db.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read_at IS NULL", (user_id,)
    ).fetchone()[0]


def next_reservation_code(db, day):
    prefix = f"RSV-{day.replace('-', '')}-"
    count = db.execute(
        "SELECT COUNT(*) FROM reservations WHERE date = ?", (day,)
    ).fetchone()[0]
    while True:
        count += 1
        code = f"{prefix}{count:03d}"
        exists = db.execute("SELECT 1 FROM reservations WHERE code = ?", (code,)).fetchone()
        if not exists:
            return code


def create_reservation(db, user, payload, now=None):
    """Create a booking inside an IMMEDIATE transaction so concurrent requests cannot double-book."""
    now = now or now_local()
    buffer_minutes = get_settings(db)["buffer_minutes"]
    db.execute("BEGIN IMMEDIATE")
    try:
        conflicts = slot_conflicts(
            db,
            payload.get("room_id"),
            payload.get("custom_room"),
            payload["date"],
            payload["start_time"],
            payload["end_time"],
            include_pending=True,
            buffer_minutes=buffer_minutes,
        )
        if conflicts:
            db.execute("ROLLBACK")
            return None, conflicts
        code = next_reservation_code(db, payload["date"])
        cursor = db.execute(
            """INSERT INTO reservations
               (code, organization_id, user_id, room_id, custom_room, borrower_type,
                identity_number, date, start_time, end_time, purpose, pic_name, pic_phone,
                status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (
                code,
                user["organization_id"],
                user["id"],
                payload.get("room_id"),
                payload.get("custom_room"),
                payload.get("borrower_type", "mahasiswa"),
                payload.get("identity_number"),
                payload["date"],
                payload["start_time"],
                payload["end_time"],
                payload["purpose"],
                payload["pic_name"],
                payload["pic_phone"],
                now.isoformat(timespec="seconds"),
            ),
        )
        reservation_id = cursor.lastrowid
        log_event(db, reservation_id, user, "dibuat", "Permohonan dikirim.")
        db.execute("COMMIT")
        return reservation_id, []
    except Exception:
        db.execute("ROLLBACK")
        raise


def decide_reservation(db, reservation, action, note, admin, now=None):
    now = now or now_local()
    buffer_minutes = get_settings(db)["buffer_minutes"]
    db.execute("BEGIN IMMEDIATE")
    try:
        fresh = db.execute(
            "SELECT * FROM reservations WHERE id = ? AND status = 'pending'", (reservation["id"],)
        ).fetchone()
        if not fresh:
            db.execute("ROLLBACK")
            return "not_pending", [], []
        approved_conflicts = slot_conflicts(
            db,
            fresh["room_id"],
            fresh["custom_room"],
            fresh["date"],
            fresh["start_time"],
            fresh["end_time"],
            exclude_id=fresh["id"],
            include_pending=False,
            buffer_minutes=buffer_minutes,
        )
        pending_conflicts = slot_conflicts(
            db,
            fresh["room_id"],
            fresh["custom_room"],
            fresh["date"],
            fresh["start_time"],
            fresh["end_time"],
            exclude_id=fresh["id"],
            include_pending=True,
            buffer_minutes=buffer_minutes,
        )
        pending_conflicts = [row for row in pending_conflicts if row["status"] == "pending"]
        if action == "approve" and (approved_conflicts or pending_conflicts):
            db.execute("ROLLBACK")
            return "conflict", approved_conflicts, pending_conflicts
        status = "approved" if action == "approve" else "rejected"
        decided_at = now.isoformat(timespec="seconds")
        db.execute(
            """UPDATE reservations SET status = ?, admin_id = ?, note = ?, decided_at = ?
               WHERE id = ?""",
            (status, admin["id"], note or None, decided_at, fresh["id"]),
        )
        log_event(db, fresh["id"], admin, "disetujui" if action == "approve" else "ditolak", note)
        title = "Reservasi disetujui" if action == "approve" else "Reservasi ditolak"
        pretty_day = format_date(fresh["date"], with_day=False)
        pretty_time = f"{format_clock(fresh['start_time'])}–{format_clock(fresh['end_time'])} WITA"
        message = (
            f"{fresh['code']} · {pretty_day}, {pretty_time} "
            f"{'telah disetujui.' if action == 'approve' else 'ditolak.'}"
        )
        if note:
            message += f" Catatan: {note}"
        notify(db, fresh["user_id"], fresh["id"], title, message)
        db.execute("COMMIT")
        return "ok", [], []
    except Exception:
        db.execute("ROLLBACK")
        raise


def cancel_reservation(db, reservation, actor, note=None, now=None):
    now = now or now_local()
    settings = get_settings(db)
    if reservation["status"] not in ("pending", "approved"):
        return "not_cancellable"
    if reservation["status"] == "approved":
        deadline = start_datetime(reservation) - timedelta(hours=settings["cancel_deadline_hours"])
        if now > deadline:
            return "too_late"
    db.execute("BEGIN IMMEDIATE")
    try:
        fresh = db.execute(
            "SELECT * FROM reservations WHERE id = ? AND status IN ('pending', 'approved')",
            (reservation["id"],),
        ).fetchone()
        if not fresh:
            db.execute("ROLLBACK")
            return "not_cancellable"
        db.execute(
            """UPDATE reservations SET status = 'cancelled', cancelled_at = ?, note = COALESCE(?, note)
               WHERE id = ?""",
            (now.isoformat(timespec="seconds"), note, fresh["id"]),
        )
        log_event(db, fresh["id"], actor, "dibatalkan", note)
        if actor["role"] == "admin" and fresh["user_id"] != actor["id"]:
            notify(
                db,
                fresh["user_id"],
                fresh["id"],
                "Reservasi dibatalkan",
                f"{fresh['code']} dibatalkan oleh admin. {note or ''}".strip(),
            )
        db.execute("COMMIT")
        return "ok"
    except Exception:
        db.execute("ROLLBACK")
        raise


def calendar_month(db, year, month, room_id=None):
    first = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    params = [first.isoformat(), next_month.isoformat(), "approved", "pending"]
    sql = """SELECT r.date, r.status, COUNT(*) AS total
             FROM reservations r
             WHERE r.date >= ? AND r.date < ? AND r.status IN (?, ?)"""
    if room_id:
        sql += " AND r.room_id = ?"
        params.append(room_id)
    sql += " GROUP BY r.date, r.status"
    rows = db.execute(sql, params).fetchall()
    summary = {}
    for row in rows:
        entry = summary.setdefault(row["date"], {"approved": 0, "pending": 0, "total": 0})
        entry[row["status"]] += row["total"]
        entry["total"] += row["total"]
    return summary


def agenda_for_day(db, day, room_id=None):
    params = [day, "approved", "pending"]
    sql = """SELECT r.*, o.name AS organization_name, o.short_name AS organization_short,
                    rm.code AS room_code, rm.name AS room_name, rm.building AS room_building
             FROM reservations r
             JOIN organizations o ON o.id = r.organization_id
             JOIN rooms rm ON rm.id = r.room_id
             WHERE r.date = ? AND r.status IN (?, ?)"""
    if room_id:
        sql += " AND r.room_id = ?"
        params.append(room_id)
    sql += " ORDER BY r.start_time, rm.code"
    return db.execute(sql, params).fetchall()


def organization_agenda(db, organization_id, limit=4):
    now = now_local()
    return list_reservations(
        db,
        organization_id=organization_id,
        status="active",
        date_from=now.date().isoformat(),
        limit=limit,
        ascending=True,
    )


def month_name(month):
    return BULAN[month - 1]


def month_matrix(year, month):
    import calendar

    cal = calendar.Calendar(firstweekday=0)
    return cal.monthdatescalendar(year, month)


def room_usage_stats(db):
    now = now_local()
    active = db.execute("SELECT COUNT(*) FROM rooms WHERE active = 1").fetchone()[0]
    pending = db.execute("SELECT COUNT(*) FROM reservations WHERE status = 'pending'").fetchone()[0]
    approved_today = db.execute(
        "SELECT COUNT(*) FROM reservations WHERE date = ? AND status = 'approved'",
        (now.date().isoformat(),),
    ).fetchone()[0]
    week_end = (now.date() + timedelta(days=7)).isoformat()
    upcoming = db.execute(
        """SELECT COUNT(*) FROM reservations
           WHERE date >= ? AND date <= ? AND status = 'approved'""",
        (now.date().isoformat(), week_end),
    ).fetchone()[0]
    return {
        "active_rooms": active,
        "pending": pending,
        "approved_today": approved_today,
        "upcoming_week": upcoming,
    }


def org_stats(db, organization_id):
    now = now_local()
    counts = status_counts(db, organization_id=organization_id)
    active_rooms = db.execute("SELECT COUNT(*) FROM rooms WHERE active = 1").fetchone()[0]
    month_prefix = now.strftime("%Y-%m")
    month_total = db.execute(
        "SELECT COUNT(*) FROM reservations WHERE organization_id = ? AND date LIKE ?",
        (organization_id, f"{month_prefix}%"),
    ).fetchone()[0]
    return {
        "pending": counts["pending"],
        "approved": counts["approved"],
        "completed": counts["completed"],
        "month_total": month_total,
        "active_rooms": active_rooms,
    }


def display_room(row):
    if row["room_id"]:
        return f'{row["room_code"]} · {row["room_name"]}'
    return row["custom_room"] or "Ruangan lain"


def initials(name):
    parts = [part for part in name.replace("—", " ").split() if part[:1].isalnum()]
    if not parts:
        return "ID"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def building_key(name):
    if not name:
        return "other"
    lowered = name.lower()
    if "serba guna" in lowered:
        return "gsg"
    if "luar" in lowered:
        return "outdoor"
    if lowered.startswith("gedung a"):
        return "a"
    if lowered.startswith("gedung b"):
        return "b"
    if lowered.startswith("gedung c"):
        return "c"
    return "other"


def slug_id(prefix="x"):
    return f"{prefix}{secrets.token_hex(4)}"
