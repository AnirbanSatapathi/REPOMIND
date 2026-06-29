import tempfile
import unittest
from pathlib import Path

from repomind.vector_store import VectorStore


class TestVectorStore(unittest.TestCase):
    def setUp(self):
        self.dimension = 384  # all-MiniLM-L6-v2 dimension
        self.store = VectorStore(dimension=self.dimension)

    def test_add_and_search_chunks(self):
        embeddings = [[0.1] * self.dimension, [0.2] * self.dimension, [0.9] * self.dimension]
        chunks = [
            {"text": "chunk A", "file_path": "/a.py", "chunk_type": "function", "name": "a"},
            {"text": "chunk B", "file_path": "/b.py", "chunk_type": "function", "name": "b"},
            {"text": "chunk C", "file_path": "/c.py", "chunk_type": "function", "name": "c"},
        ]

        self.store.add_chunks(embeddings, chunks)
        self.assertEqual(self.store.count, 3)

        # Search with embedding similar to last chunk
        query = [0.85] * self.dimension
        results = self.store.search(query, top_k=2)

        self.assertEqual(len(results), 2)
        # Most similar should be chunk C (index 2)
        self.assertEqual(results[0][1]["name"], "c")

    def test_search_empty_store(self):
        query = [0.1] * self.dimension
        results = self.store.search(query, top_k=5)
        self.assertEqual(len(results), 0)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            save_path = Path(td) / "index"

            embeddings = [[0.5] * self.dimension]
            chunks = [{"text": "test", "file_path": "/t.py", "chunk_type": "module", "name": "t"}]
            self.store.add_chunks(embeddings, chunks)

            self.store.save(save_path)

            # Create new store and load
            new_store = VectorStore(dimension=self.dimension)
            new_store.load(save_path)

            self.assertEqual(new_store.count, 1)

            # Verify search works
            results = new_store.search([0.5] * self.dimension, top_k=1)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0][1]["name"], "t")

    def test_clear(self):
        embeddings = [[0.1] * self.dimension]
        chunks = [{"text": "test", "file_path": "/t.py", "chunk_type": "module", "name": "t"}]
        self.store.add_chunks(embeddings, chunks)
        self.assertEqual(self.store.count, 1)

        self.store.clear()
        self.assertEqual(self.store.count, 0)

    def test_add_empty_embeddings(self):
        self.store.add_chunks([], [])
        self.assertEqual(self.store.count, 0)

    def test_load_nonexistent_index_raises(self):
        """Loading from a non-existent path should raise FileNotFoundError."""
        with tempfile.TemporaryDirectory() as td:
            fake_path = Path(td) / "nonexistent"
            store = VectorStore(dimension=self.dimension)
            with self.assertRaises(FileNotFoundError):
                store.load(fake_path)

    def test_save_without_path_raises(self):
        """Saving without providing a path should raise ValueError."""
        store = VectorStore(dimension=self.dimension)
        embeddings = [[0.1] * self.dimension]
        chunks = [{"text": "t", "file_path": "/t.py", "chunk_type": "module", "name": "t"}]
        store.add_chunks(embeddings, chunks)

        with self.assertRaises(ValueError):
            store.save(None)

    def test_count_on_fresh_store(self):
        """A fresh store should have count 0 before initialization."""
        store = VectorStore(dimension=self.dimension)
        self.assertEqual(store.count, 0)

    def test_search_returns_scores(self):
        """Search results should include non-negative similarity scores."""
        embeddings = [[1.0] * self.dimension]
        chunks = [{"text": "test", "file_path": "/t.py", "chunk_type": "module", "name": "t"}]
        self.store.add_chunks(embeddings, chunks)

        results = self.store.search([1.0] * self.dimension, top_k=1)
        self.assertEqual(len(results), 1)
        score, meta = results[0]
        self.assertGreater(score, 0)
        self.assertEqual(meta["name"], "t")

    def test_top_k_exceeds_store_size(self):
        """Requesting more results than stored should return all available."""
        embeddings = [[0.1] * self.dimension, [0.5] * self.dimension]
        chunks = [
            {"text": "a", "file_path": "/a.py", "chunk_type": "module", "name": "a"},
            {"text": "b", "file_path": "/b.py", "chunk_type": "module", "name": "b"},
        ]
        self.store.add_chunks(embeddings, chunks)

        results = self.store.search([0.3] * self.dimension, top_k=100)
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()