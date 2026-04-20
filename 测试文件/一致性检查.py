import sqlite3
import faiss

conn = sqlite3.connect('../local_knowledge.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM document_chunks")
chunk_count = cursor.fetchone()[0]
conn.close()

index = faiss.read_index("faiss_index.index")
print(f"片段数量: {chunk_count}")
print(f"FAISS向量数量: {index.ntotal}")