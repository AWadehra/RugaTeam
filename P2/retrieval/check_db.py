import chromadb
client = chromadb.PersistentClient(path='./P2/chroma_db')
collection = client.get_or_create_collection(name='documents')
print(collection.peek(limit=5)['metadatas'])