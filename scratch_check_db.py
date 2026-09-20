from backend.app.db.session import SessionLocal
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.message import Message
from backend.app.models.evaluation import TurnEvaluation
from backend.app.models.session import Session, SessionState
from backend.app.models.report import SessionReport

db = SessionLocal()
try:
    sessions = db.query(Session).all()
    reports = db.query(SessionReport).all()
    print(f"Total sessions in DB: {len(sessions)}")
    for s in sessions:
        print(f"Session: id={s.id}, topic={s.topic}, status={s.status}")
    print(f"Total reports in DB: {len(reports)}")
    for r in reports:
        print(f"Report: session_id={r.session_id}, score={r.understanding_score}, mastery={r.mastery_level}")
except Exception as e:
    print(f"DB error: {e}")
finally:
    db.close()
