from backend.app.db.session import SessionLocal
from sqlalchemy import inspect

# Check dev database
db = SessionLocal()
inspector = inspect(db.bind)
cols = inspector.get_columns('session_states')
print('=== DEV DB session_states ===')
for c in cols:
    if c['name'] in ['concept_mastery', 'misconception_counts', 'recent_strategy_history', 'mode_switch_history']:
        print(f"  {c['name']}: {c['type']} nullable={c['nullable']} default={c.get('default')}")

cols = inspector.get_columns('user_concept_progress')
print('=== DEV DB user_concept_progress ===')
for c in cols:
    print(f"  {c['name']}: {c['type']} nullable={c['nullable']} default={c.get('default')}")

cols = inspector.get_columns('teacher_intervention_logs')
print('=== DEV DB teacher_intervention_logs ===')
for c in cols:
    print(f"  {c['name']}: {c['type']} nullable={c['nullable']} default={c.get('default')}")

db.close()