from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Asia/Makassar")
except Exception:  # pragma: no cover - fallback for old tz databases
    from datetime import timezone

    TZ = timezone(timedelta(hours=8))

DEFAULT_ORG_PASSWORD = "idb2026"
DEFAULT_ADMIN_PASSWORD = "admin2026"

ORGANIZATIONS = [
    ("BEM IDB Bali", "BEM"),
    ("Gravity", "Gravity"),
    ("Wicwakarma", "Wicwakarma"),
    ("Damoda", "Damoda"),
    ("Executive", "Executive"),
    ("Parkamen", "Parkamen"),
    ("Teater Biru Jingga", "Teater Biru Jingga"),
    ("Lontar", "Lontar"),
    ("Putra Putri Kampus", "Putra Putri"),
    ("Theorema Goldmonk Yoga", "Theorema"),
    ("Gravity Football Club", "Gravity FC"),
    ("Obscura", "Obscura"),
    ("Mapala Widya Bhuana", "Mapala"),
    ("Thunder", "Thunder"),
    ("Gravity Music Squad", "Gravity Music"),
    ("Bluerange", "Bluerange"),
    ("Phetra", "Phetra"),
    ("Creativepreneur", "Creativepreneur"),
    ("DTA", "DTA"),
    ("KAMALA RAJNI", "Kamala Rajni"),
    ("CITRAKARA", "Citrakara"),
    ("Creanova", "Creanova"),
    ("Goldmonk Yoga", "Goldmonk Yoga"),
]

USERNAMES = [
    "bem",
    "gravity",
    "wicwakarma",
    "damoda",
    "executive",
    "parkamen",
    "teater",
    "lontar",
    "putraputri",
    "theorema",
    "gravityfc",
    "obscura",
    "mapala",
    "thunder",
    "gravitymusic",
    "bluerange",
    "phetra",
    "creativepreneur",
    "dta",
    "kamala",
    "citrakara",
    "creanova",
    "goldmonk",
]

ROOMS = [
    ("A.1.1", "Studio Pola", "Gedung A", "Lantai 1", "Studio"),
    ("A.1.2", "Lect 1A", "Gedung A", "Lantai 1", "Ruang kuliah"),
    ("A.1.3", "Lab 1C", "Gedung A", "Lantai 1", "Laboratorium"),
    ("A.2.1", "Lab 2B", "Gedung A", "Lantai 2", "Laboratorium"),
    ("A.2.2", "Lab 2C", "Gedung A", "Lantai 2", "Laboratorium"),
    ("A.2.3", "Lect 2D", "Gedung A", "Lantai 2", "Ruang kuliah"),
    ("B.2.1", "International", "Gedung B", "Lantai 2", "Ruang kuliah"),
    ("B.1.3", "Studio 3", "Gedung B", "Lantai 1", "Studio"),
    ("B.1.4", "Lab Fashion", "Gedung B", "Lantai 1", "Laboratorium"),
    ("C.1.1", "Lab 1A", "Gedung C", "Lantai 1", "Laboratorium"),
    ("C.1.2", "Lab STI", "Gedung C", "Lantai 1", "Laboratorium"),
    ("C.1.3", "Lect 1", "Gedung C", "Lantai 1", "Ruang kuliah"),
    ("C.2.1", "Lect 2A", "Gedung C", "Lantai 2", "Ruang kuliah"),
    ("C.2.2", "Lect 2B", "Gedung C", "Lantai 2", "Ruang kuliah"),
    ("C.2.3", "Studio 2C", "Gedung C", "Lantai 2", "Studio"),
    ("C.3.1", "Studio 3A", "Gedung C", "Lantai 3", "Studio"),
    ("C.3.2", "Studio 3B", "Gedung C", "Lantai 3", "Studio"),
    ("C.3.3", "Studio 3C", "Gedung C", "Lantai 3", "Studio"),
    ("AULA", "Aula IDB Bali", "Gedung Serba Guna", "Lantai 1", "Aula"),
    ("FOTO", "Studio Foto IDB Bali", "Gedung Serba Guna", "Lantai 1", "Studio"),
    ("ROOFTOP", "Rooftop IDB Bali", "Gedung Serba Guna", "Atap", "Area terbuka"),
    ("INBIS", "Inbis IDB Bali", "Gedung Serba Guna", "Lantai 1", "Ruang serbaguna"),
    ("HAL-A", "Halaman IDB Bali Gedung A", "Area Luar", "Outdoor", "Area terbuka"),
    ("HAL-B", "Halaman IDB Bali Gedung B", "Area Luar", "Outdoor", "Area terbuka"),
    ("HAL-C", "Halaman IDB Bali Gedung C", "Area Luar", "Outdoor", "Area terbuka"),
    ("GSG-1", "Gedung Serba Guna IDB Bali — Lt. 1", "Gedung Serba Guna", "Lantai 1", "Ruang serbaguna"),
    ("GSG-2", "Gedung Serba Guna IDB Bali — Lt. 2", "Gedung Serba Guna", "Lantai 2", "Ruang serbaguna"),
    ("GSG-3", "Gedung Serba Guna IDB Bali — Lt. 3", "Gedung Serba Guna", "Lantai 3", "Ruang serbaguna"),
    ("GEAR-B", "Gedung B (Gear Inc)", "Gedung B", "Lantai 1", "Ruang serbaguna"),
]

BORROWER_PROFILES = {
    "bem": ("organisasi", "Ni Kadek Ayu Lestari", "2023010101"),
    "gravity": ("mahasiswa", "I Made Yoga Pratama", "2023020145"),
    "wicwakarma": ("mahasiswa", "Putu Ayu Widyasari", "2023010233"),
    "damoda": ("mahasiswa", "I Wayan Aditya Putra", "2023030117"),
    "executive": ("mahasiswa", "Komang Gita Permata", "2023040122"),
    "teater": ("mahasiswa", "Ida Bagus Arya Wiguna", "2023050134"),
    "lontar": ("mahasiswa", "Ni Luh Putu Maharani", "2023060148"),
    "mapala": ("mahasiswa", "I Putu Gede Surya", "2023070156"),
    "obscura": ("mahasiswa", "Ayu Made Krisna", "2023080163"),
    "citrakara": ("mahasiswa", "Komang Tri Wahyuni", "2023090171"),
    "bluerange": ("mahasiswa", "I Gede Bagus Pramana", "2023100187"),
}

DEFAULT_SETTINGS = {
    "buffer_minutes": "0",
    "max_advance_days": "180",
    "open_time": "07:00",
    "close_time": "22:00",
    "cancel_deadline_hours": "0",
    "min_duration_minutes": "30",
    "max_duration_hours": "8",
}


def _iso(moment):
    return moment.isoformat(timespec="seconds")


def _round_to_quarter(moment):
    minute = (moment.minute // 15) * 15
    return moment.replace(minute=minute, second=0, microsecond=0)


def _clamp_time(value, low="07:00", high="22:00"):
    if value < low:
        return low
    if value > high:
        return high
    return value


def _minutes(value):
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _hhmm(total):
    total = max(0, min(total, 23 * 60 + 59))
    return f"{total // 60:02d}:{total % 60:02d}"


def seed_database(db):
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        return

    now = datetime.now(TZ)
    today = now.date()
    org_password = generate_password_hash(DEFAULT_ORG_PASSWORD, method="pbkdf2:sha256:600000")
    admin_password = generate_password_hash(DEFAULT_ADMIN_PASSWORD, method="pbkdf2:sha256:600000")
    created = _iso(now - timedelta(days=120))

    for key, value in DEFAULT_SETTINGS.items():
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

    for name, short_name in ORGANIZATIONS:
        db.execute(
            "INSERT INTO organizations (name, short_name, active, created_at) VALUES (?, ?, 1, ?)",
            (name, short_name, created),
        )

    org_rows = db.execute("SELECT id, name FROM organizations ORDER BY id").fetchall()
    org_ids = {}
    for row, username in zip(org_rows, USERNAMES):
        org_ids[username] = row["id"]
        db.execute(
            """INSERT INTO users (username, email, password_hash, role, name, organization_id, active, created_at)
               VALUES (?, ?, ?, 'org', ?, ?, 1, ?)""",
            (
                username,
                f"{username}@idbbali.ac.id",
                org_password,
                row["name"],
                row["id"],
                created,
            ),
        )

    db.execute(
        """INSERT INTO users (username, email, password_hash, role, name, organization_id, active, created_at)
           VALUES (?, ?, ?, 'admin', ?, NULL, 1, ?)""",
        ("admin", "admin@idbbali.ac.id", admin_password, "Admin Kampus", created),
    )

    for order, (code, name, building, floor, kind) in enumerate(ROOMS, start=1):
        db.execute(
            """INSERT INTO rooms (code, name, building, floor, kind, description, active, sort_order, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            (
                code,
                name,
                building,
                floor,
                kind,
                f"{kind} di {building}, {floor.lower()}.",
                order,
                created,
            ),
        )

    room_ids = {
        row["code"]: row["id"] for row in db.execute("SELECT id, code FROM rooms").fetchall()
    }
    admin_id = db.execute("SELECT id FROM users WHERE role = 'admin'").fetchone()["id"]

    def add_booking(
        username,
        room_code,
        day,
        start,
        end,
        purpose,
        status,
        note=None,
        created_days_ago=4,
        decided=True,
    ):
        user = db.execute(
            "SELECT id, name, organization_id FROM users WHERE username = ?", (username,)
        ).fetchone()
        created_at = _iso(now - timedelta(days=created_days_ago))
        code = f"RSV-{day.strftime('%Y%m%d')}-{db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0] + 1:03d}"
        borrower_type, borrower_name, identity_number = BORROWER_PROFILES.get(
            username,
            (
                "mahasiswa",
                f"Perwakilan {user['name']}",
                f"2024{user['organization_id']:04d}",
            ),
        )
        decided_at = _iso(now - timedelta(days=max(created_days_ago - 1, 0))) if decided else None
        cancelled_at = decided_at if status == "cancelled" else None
        cursor = db.execute(
            """INSERT INTO reservations
               (code, organization_id, user_id, room_id, borrower_type, identity_number,
                date, start_time, end_time, purpose, pic_name, pic_phone, status, admin_id,
                note, created_at, decided_at, cancelled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                code,
                user["organization_id"],
                user["id"],
                room_ids[room_code],
                borrower_type,
                identity_number,
                day.isoformat(),
                start,
                end,
                purpose,
                borrower_name,
                "0812 3456 7890",
                status,
                admin_id if decided else None,
                note,
                created_at,
                decided_at,
                cancelled_at,
            ),
        )
        reservation_id = cursor.lastrowid
        db.execute(
            """INSERT INTO reservation_events (reservation_id, actor_id, actor_role, action, note, created_at)
               VALUES (?, ?, 'org', 'dibuat', 'Permohonan dikirim.', ?)""",
            (reservation_id, user["id"], created_at),
        )
        if decided:
            action = {
                "approved": "disetujui",
                "rejected": "ditolak",
                "cancelled": "dibatalkan",
            }.get(status)
            if action:
                actor_role = "org" if status == "cancelled" else "admin"
                actor_id = user["id"] if status == "cancelled" else admin_id
                db.execute(
                    """INSERT INTO reservation_events (reservation_id, actor_id, actor_role, action, note, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (reservation_id, actor_id, actor_role, action, note, decided_at),
                )
        if status in ("approved", "rejected"):
            title = "Reservasi disetujui" if status == "approved" else "Reservasi ditolak"
            message = (
                f"{code} · {room_code} pada {day.strftime('%d/%m/%Y')} {start}–{end} telah {action}."
                if status == "approved"
                else f"{code} untuk {room_code} pada {day.strftime('%d/%m/%Y')} ditolak. {note or ''}".strip()
            )
            db.execute(
                """INSERT INTO notifications (user_id, reservation_id, title, message, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (user["id"], reservation_id, title, message, _iso(now - timedelta(hours=3))),
            )
        return reservation_id

    # Papan jadwal hari ini: satu sesi yang sedang berjalan, satu sesi berikutnya.
    running_start = _clamp_time(_hhmm(_minutes(_round_to_quarter(now).strftime("%H:%M")) - 30))
    running_end = _clamp_time(_hhmm(_minutes(running_start) + 120))
    if running_end <= running_start:
        running_start, running_end = "18:00", "20:00"
    add_booking(
        "gravity",
        "C.2.1",
        today,
        running_start,
        running_end,
        "Rapat koordinasi panitia Dies Natalis.",
        "approved",
        created_days_ago=6,
    )

    next_start = _clamp_time(_hhmm(_minutes(_round_to_quarter(now).strftime("%H:%M")) + 150))
    next_end = _clamp_time(_hhmm(_minutes(next_start) + 120))
    if next_end > next_start:
        add_booking(
            "wicwakarma",
            "AULA",
            today,
            next_start,
            next_end,
            "Gladi bersih pameran karya mahasiswa.",
            "approved",
            created_days_ago=5,
        )

    pending_start = _clamp_time(_hhmm(_minutes(next_end) + 30))
    pending_end = _clamp_time(_hhmm(_minutes(pending_start) + 120))
    if pending_end > pending_start:
        add_booking(
            "damoda",
            "AULA",
            today,
            pending_start,
            pending_end,
            "Diskusi terbuka organisasi mahasiswa.",
            "pending",
            created_days_ago=1,
            decided=False,
        )

    add_booking(
        "teater",
        "GSG-1",
        today + timedelta(days=1),
        "10:00",
        "12:00",
        "Latihan pementasan Teater Biru Jingga.",
        "approved",
    )
    add_booking(
        "lontar",
        "GSG-1",
        today + timedelta(days=1),
        "13:00",
        "15:00",
        "Lokakarya penulisan naskah.",
        "pending",
        created_days_ago=2,
        decided=False,
    )
    add_booking(
        "bem",
        "B.2.1",
        today + timedelta(days=2),
        "09:00",
        "11:00",
        "Rapat kerja pengurus BEM.",
        "approved",
    )
    add_booking(
        "mapala",
        "ROOFTOP",
        today + timedelta(days=3),
        "15:00",
        "18:00",
        "Briefing ekspedisi dan pemeriksaan alat.",
        "pending",
        created_days_ago=1,
        decided=False,
    )
    add_booking(
        "teater",
        "A.1.2",
        today - timedelta(days=3),
        "10:00",
        "12:00",
        "Reading session naskah baru.",
        "approved",
        created_days_ago=12,
    )
    add_booking(
        "obscura",
        "C.1.1",
        today + timedelta(days=5),
        "13:00",
        "15:00",
        "Workshop fotografi dasar.",
        "rejected",
        note="Ruangan dipakai untuk ujian praktikum pada jam tersebut.",
        created_days_ago=3,
    )
    add_booking(
        "citrakara",
        "FOTO",
        today + timedelta(days=6),
        "09:00",
        "12:00",
        "Pemotretan katalog karya.",
        "cancelled",
        note="Kegiatan dibatalkan oleh organisasi.",
        created_days_ago=4,
    )
    add_booking(
        "bluerange",
        "HAL-B",
        today + timedelta(days=7),
        "16:00",
        "19:00",
        "Pasar kreatif mahasiswa.",
        "approved",
        created_days_ago=2,
    )

    # Contoh validasi jadwal dari PRD: A disetujui, B bertabrakan dan menunggu keputusan.
    example_day = max(date(2026, 11, 20), today + timedelta(days=20))
    add_booking(
        "bem",
        "AULA",
        example_day,
        "09:00",
        "11:00",
        "Seminar kepemimpinan organisasi.",
        "approved",
        created_days_ago=8,
    )
    add_booking(
        "executive",
        "AULA",
        example_day,
        "10:00",
        "12:00",
        "Pelatihan public speaking.",
        "pending",
        created_days_ago=2,
        decided=False,
    )
