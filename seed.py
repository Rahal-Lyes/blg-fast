"""
seed.py — Populates the database with sample data (same as the PHP demo data).
Run: python seed.py
"""
from app.db.database import SessionLocal
from app.models.user import User
from app.models.report import Report, StatusHistory
from app.core.security import hash_password


def seed():
    db = SessionLocal()
    try:
        if db.query(User).first():
            print("Database already seeded — skipping.")
            return

        # ── Users ──────────────────────────────────────────────
        u1 = User(name="أحمد بن علي", email="ahmed@example.com",
                  hashed_password=hash_password("citizen1"), role="citizen")
        u2 = User(name="فاطمة زهراء", email="fatima@example.com",
                  hashed_password=hash_password("citizen2"), role="citizen")
        db.add_all([u1, u2])
        db.flush()

        # ── Reports ────────────────────────────────────────────
        reports_data = [
            dict(user_id=u1.id, ref_num="2026/16/0001", title="حفرة كبيرة في الطريق",
                 category="road", wilaya="الجزائر", commune="باب الوادي",
                 status="processing", priority="urgent",
                 description="حفرة خطيرة تسبب حوادث للسيارات في الطريق الرئيسي",
                 lat=36.7752, lng=3.0584, votes_count=12),
            dict(user_id=u2.id, ref_num="2026/31/0001", title="عمود إنارة معطل",
                 category="lighting", wilaya="وهران", commune="السانيا",
                 status="pending", priority="normal",
                 description="الشارع مظلم ليلاً مما يشكل خطراً على المشاة",
                 lat=35.6987, lng=-0.6349, votes_count=5),
            dict(user_id=u1.id, ref_num="2026/16/0002", title="تراكم النفايات",
                 category="waste", wilaya="الجزائر", commune="الحراش",
                 status="resolved", priority="normal",
                 description="تم حل المشكلة بعد تدخل البلدية",
                 lat=36.7200, lng=3.1500, votes_count=23),
            dict(user_id=u2.id, ref_num="2026/25/0001", title="تسرب مياه في الشارع",
                 category="water", wilaya="قسنطينة", commune="المنصورة",
                 status="pending", priority="urgent",
                 description="تسرب مستمر منذ أسبوع يتسبب في أضرار",
                 lat=36.3650, lng=6.6147, votes_count=8),
            dict(user_id=u1.id, ref_num="2026/06/0001", title="شجرة مقطوعة تعيق المرور",
                 category="other", wilaya="بجاية", commune="أميزور",
                 status="processing", priority="low",
                 description="شجرة سقطت بسبب الرياح وتعيق الطريق",
                 lat=36.6400, lng=4.9000, votes_count=3),
        ]
        for rd in reports_data:
            r = Report(**rd)
            db.add(r)
            db.flush()
            db.add(StatusHistory(report_id=r.id, from_status=None, to_status=r.status, changed_by="seed"))

        db.commit()
        print("✅ Database seeded successfully!")
        print("   Citizens: ahmed@example.com / citizen1 | fatima@example.com / citizen2")
        print("   Admin:    password = admin123")
    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
