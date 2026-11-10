import os
import re
import tempfile
import unittest
from datetime import date, timedelta

os.environ["IDB_DATABASE"] = tempfile.mktemp(prefix="idb-room-test-", suffix=".sqlite")
os.environ["IDB_SECRET_KEY"] = "test-secret-key-not-for-production"

from app import app  # noqa: E402
from database import get_db  # noqa: E402
import services  # noqa: E402


def csrf_from(html):
    match = re.search(r'name="_csrf" value="([^"]+)"', html)
    if not match:
        raise AssertionError("CSRF token not found")
    return match.group(1)


class IDBRoomTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def login(self, username, password):
        page = self.client.get("/login")
        token = csrf_from(page.get_data(as_text=True))
        response = self.client.post(
            "/login",
            data={"username": username, "password": password, "_csrf": token},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        return response

    def logout(self):
        page = self.client.get("/")
        token = csrf_from(page.get_data(as_text=True))
        self.client.post("/logout", data={"_csrf": token})

    def test_01_login_page_and_redirect(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Masuk ke akun", response.get_data(as_text=True))
        protected = self.client.get("/", follow_redirects=False)
        self.assertEqual(protected.status_code, 302)
        self.assertIn("/login", protected.headers["Location"])

    def test_02_login_works(self):
        response = self.login("kean.azkara@idbbali.ac.id", "123456")
        self.assertIn("Selamat datang", response.get_data(as_text=True))

    def test_03_wrong_password_is_rejected(self):
        response = self.login("kean.azkara@idbbali.ac.id", "salah")
        self.assertIn("Email atau kata sandi tidak cocok", response.get_data(as_text=True))

    def test_03b_email_login_is_supported(self):
        response = self.login("kean.azkara@idbbali.ac.id", "123456")
        self.assertIn("Selamat datang", response.get_data(as_text=True))

    def test_03c_dosen_login_uses_dosen_defaults(self):
        response = self.login("tania.moona@idbbali.ac.id", "tania124")
        self.assertIn("Selamat datang", response.get_data(as_text=True))
        form = self.client.get("/reservasi/baru").get_data(as_text=True)
        self.assertIn("Nama dosen", form)
        self.assertIn("NIDN/NIP", form)
        self.assertIn("Tania Moona", form)

    def test_04_detects_prd_conflict_example(self):
        with app.app_context():
            db = get_db()
            pending = db.execute(
                """SELECT r.*, rm.id AS rid FROM reservations r
                   JOIN rooms rm ON rm.id = r.room_id
                   WHERE r.status = 'pending' AND rm.code = 'AULA'
                   ORDER BY r.date DESC LIMIT 1"""
            ).fetchone()
            self.assertIsNotNone(pending)
            conflicts = services.room_conflicts(
                db, pending["room_id"], pending["date"], pending["start_time"], pending["end_time"],
                exclude_id=pending["id"], include_pending=False,
            )
            self.assertTrue(conflicts, "Contoh PRD seharusnya mendeteksi bentrok dengan reservasi disetujui")

    def test_05_create_rejects_overlap_and_accepts_free_slot(self):
        self.login("kean.azkara@idbbali.ac.id", "123456")
        with app.app_context():
            db = get_db()
            room = db.execute("SELECT * FROM rooms WHERE code = 'AULA'").fetchone()
            example = db.execute(
                """SELECT * FROM reservations
                   WHERE room_id = ? AND status = 'pending' ORDER BY date DESC LIMIT 1""",
                (room["id"],),
            ).fetchone()
            room_id = room["id"]
            example_day = example["date"]
        form_page = self.client.get("/reservasi/baru")
        token = csrf_from(form_page.get_data(as_text=True))
        base = {
            "_csrf": token,
            "room_id": str(room_id),
            "date": example_day,
            "start_time": "10:00",
            "end_time": "11:00",
            "purpose": "Uji bentrok otomatis dari test suite.",
            "borrower_type": "mahasiswa",
            "identity_number": "2023010101",
            "pic_name": "Pengurus BEM",
            "pic_phone": "081234567890",
        }
        rejected = self.client.post("/reservasi/baru", data=base)
        self.assertEqual(rejected.status_code, 200)
        self.assertIn("bertabrakan", rejected.get_data(as_text=True))

        later = (date.today() + timedelta(days=40)).isoformat()
        base.update({"date": later, "start_time": "13:00", "end_time": "15:00"})
        created = self.client.post("/reservasi/baru", data=base, follow_redirects=False)
        self.assertEqual(created.status_code, 302)
        with app.app_context():
            db = get_db()
            row = db.execute(
                "SELECT * FROM reservations WHERE date = ? ORDER BY id DESC LIMIT 1", (later,)
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["status"], "pending")
            self.assertEqual(row["start_time"], "13:00")

    def test_06_admin_cannot_approve_conflicting_request(self):
        with app.app_context():
            db = get_db()
            row = db.execute(
                """SELECT p.* FROM reservations p JOIN rooms rm ON rm.id = p.room_id
                   WHERE p.status = 'pending' AND rm.code = 'AULA'
                     AND EXISTS (
                       SELECT 1 FROM reservations a
                       WHERE a.room_id = p.room_id AND a.date = p.date AND a.status = 'approved'
                         AND a.id != p.id
                         AND a.start_time < p.end_time AND p.start_time < a.end_time
                     )
                   ORDER BY p.date LIMIT 1"""
            ).fetchone()
            reservation_id = row["id"]
        self.login("admin", "idbbali123")
        page = self.client.get(f"/reservasi/{reservation_id}")
        token = csrf_from(page.get_data(as_text=True))
        response = self.client.post(
            f"/admin/reservasi/{reservation_id}/keputusan",
            data={"_csrf": token, "action": "approve", "note": ""},
            follow_redirects=True,
        )
        self.assertIn("Belum bisa disetujui", response.get_data(as_text=True))
        with app.app_context():
            db = get_db()
            status = db.execute(
                "SELECT status FROM reservations WHERE id = ?", (reservation_id,)
            ).fetchone()["status"]
            self.assertEqual(status, "pending")

    def test_07_admin_approves_clean_request_and_notifies(self):
        self.login("admin", "idbbali123")
        with app.app_context():
            db = get_db()
            row = db.execute(
                """SELECT r.* FROM reservations r JOIN rooms rm ON rm.id = r.room_id
                   WHERE r.status = 'pending' AND rm.code = 'GSG-1'
                   ORDER BY r.date LIMIT 1"""
            ).fetchone()
            reservation_id = row["id"]
            user_id = row["user_id"]
        page = self.client.get(f"/reservasi/{reservation_id}")
        token = csrf_from(page.get_data(as_text=True))
        response = self.client.post(
            f"/admin/reservasi/{reservation_id}/keputusan",
            data={"_csrf": token, "action": "approve", "note": "Disetujui untuk uji."},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("disetujui", response.get_data(as_text=True).lower())
        with app.app_context():
            db = get_db()
            booking = db.execute(
                "SELECT * FROM reservations WHERE id = ?", (reservation_id,)
            ).fetchone()
            self.assertEqual(booking["status"], "approved")
            notification = db.execute(
                "SELECT * FROM notifications WHERE user_id = ? AND reservation_id = ?",
                (user_id, reservation_id),
            ).fetchone()
            self.assertIsNotNone(notification)

    def test_07b_nim_is_required_and_shown_on_detail(self):
        self.login("kean.azkara@idbbali.ac.id", "123456")
        token = csrf_from(self.client.get("/reservasi/baru").get_data(as_text=True))
        data = {
            "_csrf": token,
            "room_id": "29",
            "date": (date.today() + timedelta(days=41)).isoformat(),
            "start_time": "09:00",
            "end_time": "10:00",
            "purpose": "Uji validasi identitas peminjam.",
            "borrower_type": "dosen",
            "identity_number": "123",
            "pic_name": "Dr. Uji Coba",
            "pic_phone": "081234567890",
        }
        rejected = self.client.post("/reservasi/baru", data=data)
        self.assertIn("NIDN/NIP minimal 6 angka", rejected.get_data(as_text=True))
        data["identity_number"] = "0012345678"
        created = self.client.post("/reservasi/baru", data=data, follow_redirects=False)
        self.assertEqual(created.status_code, 302)
        detail = self.client.get(created.headers["Location"])
        body = detail.get_data(as_text=True)
        self.assertIn("Nama dosen", body)
        self.assertIn("NIDN/NIP", body)
        self.assertIn("0012345678", body)

    def test_08_buffer_rule(self):
        self.assertTrue(services.overlaps("09:00", "11:00", "11:10", "12:00", 15))
        self.assertFalse(services.overlaps("09:00", "11:00", "11:15", "12:00", 15))
        self.assertFalse(services.overlaps("09:00", "11:00", "11:15", "12:00", 0))

    def test_09_healthcheck_headers(self):
        response = self.client.get("/login")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src", response.headers["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
