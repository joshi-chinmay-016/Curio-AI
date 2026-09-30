import psycopg2

# Try different users that might exist
users = ['postgres', 'curio', 'admin', 'test', 'vishal']
for user in users:
    try:
        conn = psycopg2.connect(host='localhost', port=5432, user=user, password='postgres', database='postgres', connect_timeout=3)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'curio_test_db'")
        exists = cur.fetchone()
        if not exists:
            cur.execute('CREATE DATABASE curio_test_db')
            print(f'Created curio_test_db with user: {user}')
        else:
            print(f'curio_test_db already exists with user: {user}')
        cur.close()
        conn.close()
        break
    except Exception as e:
        print(f'User {user} failed: {e}')
        continue
else:
    print('No valid user found')