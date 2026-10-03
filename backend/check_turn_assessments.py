import os
os.environ['TEST_DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5433/curio_test_db'

from sqlalchemy import create_engine, inspect

engine = create_engine(os.environ['TEST_DATABASE_URL'])
inspector = inspect(engine)

if 'turn_assessments' in inspector.get_table_names():
    print('turn_assessments table EXISTS')
    cols = inspector.get_columns('turn_assessments')
    for c in cols:
        print(f'  {c["name"]}: {c["type"]} nullable={c["nullable"]} default={c.get("default")}')
    
    # Check foreign keys
    fks = inspector.get_foreign_keys('turn_assessments')
    print('Foreign Keys:')
    for fk in fks:
        print(f'  {fk["constrained_columns"]} -> {fk["referred_table"]}.{fk["referred_columns"]}')
    
    # Check indexes
    indexes = inspector.get_indexes('turn_assessments')
    print('Indexes:')
    for idx in indexes:
        print(f'  {idx["name"]}: columns={idx["column_names"]} unique={idx["unique"]}')
else:
    print('turn_assessments table NOT FOUND')

engine.dispose()