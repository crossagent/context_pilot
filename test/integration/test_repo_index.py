
import os
import unittest
import tempfile
from pathlib import Path
from bug_sleuth.repo_index_tool import CodeParser, DatabaseManager

class TestRepoIndexTool(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.test_dir.name, "index.db")
        self.src_file = os.path.join(self.test_dir.name, "TestClass.cs")
        
        # Write dummy C# code
        with open(self.src_file, "w", encoding="utf-8") as f:
            f.write("""
            using System;
            namespace MyNamespace {
                public class TestClass {
                    public void MyMethod() {
                        Console.WriteLine("Hello");
                    }
                }
            }
            """)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_parse_and_store(self):
        # 1. Initialize Parser & DB
        parser = CodeParser()
        db_manager = DatabaseManager(self.db_path)
        db_manager.connect()

        # 2. Parse File
        symbols = list(parser.parse_file(self.src_file))
        
        # Verify Parser Output
        # Expecting: class TestClass, method MyMethod
        names = [s['name'] for s in symbols]
        self.assertIn("TestClass", names)
        self.assertIn("MyMethod", names)

        # 3. Store in DB
        db_manager.clear_file_symbols(self.src_file)
        for s in symbols:
            db_manager.insert_symbol(
                name=s['name'],
                symbol_type=s['type'],
                file_path=self.src_file,
                start_line=s['start_line'],
                end_line=s['end_line']
            )
        
        db_manager.commit()

        # 4. Verify DB Content
        cursor = db_manager.conn.cursor()
        cursor.execute("SELECT name, type FROM symbols WHERE file_path = ?", (self.src_file,))
        rows = cursor.fetchall()
        
        stored_names = [r[0] for r in rows]
        self.assertIn("TestClass", stored_names)
        self.assertIn("MyMethod", stored_names)
        
        db_manager.close()

if __name__ == "__main__":
    unittest.main()
