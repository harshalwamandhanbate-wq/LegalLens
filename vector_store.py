import chromadb
from chromadb.utils import embedding_functions

class LocalContractStore:
    def __init__(self):
        # Creates a local, in-memory database that wipes clean on every run
        self.client = chromadb.Client()
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="contract_clauses", 
            embedding_function=self.ef
        )

    def add_document_chunks(self, text, chunk_size=800, overlap=100):
        """Splits PDF text into smaller pieces and stores them in the local database."""
        existing_ids = self.collection.get()["ids"]
        if existing_ids:
            self.collection.delete(ids=existing_ids)

        words = text.split()
        chunks = []
        ids = []
        
        i = 0
        chunk_idx = 0
        while i < len(words):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            ids.append(f"clause_{chunk_idx}")
            i += (chunk_size - overlap)
            chunk_idx += 1

        if chunks:
            self.collection.add(documents=chunks, ids=ids)
        return len(chunks)

    def query_relevant_clauses(self, query_text, n_results=2):
        """Searches the database for the paragraphs that match your topic."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=min(n_results, self.collection.count())
        )
        if results and results["documents"]:
            return results["documents"][0]
        return []