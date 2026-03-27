# AutoMentor Real RAG Dataset

This folder contains the first real course-grounded dataset used by the RAG layer.

Use `processed/chunks.jsonl` as the main retrieval source.

Workflow:

1. Put your subject notes inside `raw/` as `.md` or `.txt` files.
2. Start each file with simple metadata lines like `subject: DSA`.
3. Run:

```powershell
.\.venv\Scripts\python.exe scripts\build_rag_dataset.py
```

4. The script rebuilds:
   - `processed/manifest.csv`
   - `processed/chunks.jsonl`

The backend RAG engine automatically reads `processed/chunks.jsonl`.

You can keep adding more chunks over time from:

- syllabus
- lecture notes
- lab manuals
- assignment sheets
- previous-year questions
- viva questions

The backend will prefer this dataset over the template dataset when both exist.
