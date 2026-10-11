import psycopg2
from backend.app.core.config import settings

test_url = settings.get_test_database_url()
conn = psycopg2.connect(test_url)
conn.autocommit = True
cur = conn.cursor()
cur.execute('SELECT current_database(), inet_server_addr(), inet_server_port()')
result = cur.fetchone()
print(f'Test DB: database={result[0]}, host={result[1]}, port={result[2]}')

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name")
tables = [row[0] for row in cur.fetchall()]
print(f'Tables in test DB ({len(tables)}): {tables}')

cur.close()
conn.close()