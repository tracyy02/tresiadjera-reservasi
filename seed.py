from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Asia/Makassar")
except Exception:  # pragma: no cover - fallback for old tz databases
    from datetime import timezone

    TZ = timezone(timedelta(hours=8))

DEFAULT_STUDENT_PASSWORD = "idb2026"
DEFAULT_ADMIN_PASSWORD = "idbbali123"

# Setiap peminjam adalah individu (mahasiswa/dosen). Baris pada tabel
# organizations bersifat internal sebagai pemisah data antar-pengguna.
PEOPLE = [
    ("kean", "Kean Azkara", "kean.azkara@idbbali.ac.id", "mahasiswa", "2023010101", "123456"),
    ("tania", "Tania Moona", "tania.moona@idbbali.ac.id", "dosen", "0012345678", "tania124"),
    ("ayu", "Ni Kadek Ayu Lestari", "ayu.lestari@idbbali.ac.id", "mahasiswa", "2023010233", DEFAULT_STUDENT_PASSWORD),
    ("yoga", "I Made Yoga Pratama", "yoga.pratama@idbbali.ac.id", "mahasiswa", "2023020145", DEFAULT_STUDENT_PASSWORD),
    ("widyasari", "Putu Ayu Widyasari", "widyasari@idbbali.ac.id", "mahasiswa", "2023010288", DEFAULT_STUDENT_PASSWORD),
    ("aditya", "I Wayan Aditya Putra", "aditya.putra@idbbali.ac.id", "mahasiswa", "2023030117", DEFAULT_STUDENT_PASSWORD),
    ("arya", "Ida Bagus Arya Wiguna", "arya.wiguna@idbbali.ac.id", "mahasiswa", "2023050134", DEFAULT_STUDENT_PASSWORD),
    ("maharani", "Ni Luh Putu Maharani", "maharani@idbbali.ac.id", "mahasiswa", "2023060148", DEFAULT_STUDENT_PASSWORD),
    ("surya", "I Putu Gede Surya", "surya@idbbali.ac.id", "mahasiswa", "2023070156", DEFAULT_STUDENT_PASSWORD),
    ("krisna", "Ayu Made Krisna", "krisna@idbbali.ac.id", "mahasiswa", "2023080163", DEFAULT_STUDENT_PASSWORD),
    ("tri", "Komang Tri Wahyuni", "tri.wahyuni@idbbali.ac.id", "mahasiswa", "2023090171", DEFAULT_STUDENT_PASSWORD),
    ("pramana", "I Gede Bagus Pramana", "pramana@idbbali.ac.id", "mahasiswa", "2023100187", DEFAULT_STUDENT_PASSWORD),
    ("gita", "Komang Gita Permata", "gita@idbbali.ac.id", "mahasiswa", "2023040122", DEFAULT_STUDENT_PASSWORD),
]

PROFILE_BY_USER = {person[0]: (person[3], person[4]) for person in PEOPLE}

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
    ("AULA", "Aula IDB Bali", "Gedung A", "Lantai 3", "Aula"),
    ("FOTO", "Studio Foto IDB Bali", "Gedung A", "Lantai 1", "Studio"),
    ("ROOFTOP", "Rooftop IDB Bali", "Gedung B", "Lantai 3", "Area terbuka"),
    ("INBIS", "Inbis IDB Bali", "Gedung B", "Lantai 1", "Ruang serbaguna"),
    ("HAL-A", "Halaman IDB Bali Gedung A", "Area Luar", "Outdoor", "Area terbuka"),
    ("HAL-B", "Halaman IDB Bali Gedung B", "Area Luar", "Outdoor", "Area terbuka"),
    ("HAL-C", "Halaman IDB Bali Gedung C", "Area Luar", "Outdoor", "Area terbuka"),
    ("GSG-1", "Gedung Serba Guna IDB Bali — Lt. 1", "Gedung Serba Guna", "Lantai 1", "Ruang serbaguna"),
    ("GSG-2", "Gedung Serba Guna IDB Bali — Lt. 2", "Gedung Serba Guna", "Lantai 2", "Ruang serbaguna"),
    ("GSG-3", "Gedung Serba Guna IDB Bali — Lt. 3", "Gedung Serba Guna", "Lantai 3", "Ruang serbaguna"),
    ("GEAR-B", "Gedung B (Gear Inc)", "Gedung B", "Lantai 1", "Ruang serbaguna"),
]

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
    admin_password = generate_password_hash(DEFAULT_ADMIN_PASSWORD, method="pbkdf2:sha256:600000")
    password_hashes = {}
    created = _iso(now - timedelta(days=120))

    for key, value in DEFAULT_SETTINGS.items():
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

    for username, name, email, borrower_type, identity, password in PEOPLE:
        if password not in password_hashes:
            password_hashes[password] = generate_password_hash(
                password, method="pbkdf2:sha256:600000"
            )
        cursor = db.execute(
            "INSERT INTO organizations (name, short_name, active, created_at) VALUES (?, ?, 1, ?)",
            (name, name.split()[0], created),
        )
        db.execute(
            """INSERT INTO users
               (username, email, password_hash, role, name, borrower_type, organization_id, active, created_at)
               VALUES (?, ?, ?, 'org', ?, ?, ?, 1, ?)""",
            (
                username,
                email,
                password_hashes[password],
                name,
                borrower_type,
                cursor.lastrowid,
                created,
            ),
        )

    db.execute(
        """INSERT INTO users
           (username, email, password_hash, role, name, borrower_type, organization_id, active, created_at)
           VALUES (?, ?, ?, 'admin', ?, 'mahasiswa', NULL, 1, ?)""",
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
        borrower_type, identity_number = PROFILE_BY_USER.get(
            username, ("mahasiswa", "2024000000")
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
                user["name"],
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
        "yoga",
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
            "widyasari",
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
            "aditya",
            "AULA",
            today,
            pending_start,
            pending_end,
            "Diskusi terbuka mahasiswa.",
            "pending",
            created_days_ago=1,
            decided=False,
        )

    add_booking(
        "arya",
        "GSG-1",
        today + timedelta(days=1),
        "10:00",
        "12:00",
        "Latihan pementasan Teater Biru Jingga.",
        "approved",
    )
    add_booking(
        "maharani",
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
        "kean",
        "B.2.1",
        today + timedelta(days=2),
        "09:00",
        "11:00",
        "Rapat kerja kepengurusan mahasiswa.",
        "approved",
    )
    add_booking(
        "surya",
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
        "arya",
        "A.1.2",
        today - timedelta(days=3),
        "10:00",
        "12:00",
        "Reading session naskah baru.",
        "approved",
        created_days_ago=12,
    )
    add_booking(
        "krisna",
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
        "tri",
        "FOTO",
        today + timedelta(days=6),
        "09:00",
        "12:00",
        "Pemotretan katalog karya.",
        "cancelled",
        note="Kegiatan dibatalkan oleh pemohon.",
        created_days_ago=4,
    )
    add_booking(
        "pramana",
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
        "kean",
        "AULA",
        example_day,
        "09:00",
        "11:00",
        "Seminar kepemimpinan mahasiswa.",
        "approved",
        created_days_ago=8,
    )
    add_booking(
        "gita",
        "AULA",
        example_day,
        "10:00",
        "12:00",
        "Pelatihan public speaking.",
        "pending",
        created_days_ago=2,
        decided=False,
    )

    add_booking(
        "tania",
        "C.2.2",
        today + timedelta(days=9),
        "09:00",
        "11:00",
        "Rapat koordinasi dosen pembimbing.",
        "approved",
        created_days_ago=2,
    )
