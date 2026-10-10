from sqlalchemy import create_engine, text

# Check dev database
engine_dev = create_engine('postgresql://postgres:postgres@localhost:5433/curio_db')
with engine_dev.connect() as conn:
    # Check pgvector extension
    result = conn.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'")).fetchall()
    print('PGVector extension (dev):', result)
    
    # Check current chunks and embeddings
    result = conn.execute(text("SELECT COUNT(*) as total, COUNT(embedding) as with_embedding FROM document_chunks")).fetchall()
    print('Chunks (dev):', result)

# Check test database
engine_test = create_engine('postgresql://postgres:postgres@localhost:5433/curio_test_db')
with engine_test.connect() as conn:
    # Check pgvector extension
    result = conn.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'")).fetchall()
    print('PGVector extension (test):', result)
    
    # Check current chunks and embeddings
    result = conn.execute(text("SELECT COUNT(*) as total, COUNT(embedding) as with_embedding FROM document_chunks")).fetchall()
    print('Chunks (test):', result)