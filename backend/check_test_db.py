import os
os.environ['TEST_DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5433/curio_test_db'

from sqlalchemy import create_engine, inspect

engine = create_engine(os.environ['TEST_DATABASE_URL'])
inspector = inspect(engine)

cols = inspector.get_columns('session_states')
print('=== TEST DB session_states ===')
for c in cols:
    if c['name'] in ['concept_mastery', 'misconception_counts', 'recent_strategy_history', 'mode_switch_history']:
        print(f"  {c['name']}: {c['type']} nullable={c['nullable']} default={c.get('default')}")

cols = inspector.get_columns('user_concept_progress')
print('=== TEST DB user_concept_progress ===')
for c in cols:
    print(f"  {c['name']}: {c['type']} nullable={c['nullable']} default={c.get('default')}")

cols = inspector.get_columns('teacher_intervention_logs')
print('=== TEST DB teacher_intervention_logs ===')
for c in cols:
    print(f"  {c['name']}: {c['type']} nullable={c['nullable']} default={c.get('default')}")

engine.dispose()