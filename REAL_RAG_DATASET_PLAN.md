# Real RAG Dataset Plan for AutoMentor

## Goal

Turn AutoMentor's current mock RAG into a real course-grounded retrieval system using your own academic material.

The best first version is a small, clean, subject-wise dataset built from real study resources.

## Best Dataset Choice

Use a custom academic dataset made from:

- syllabus
- class notes
- lab manuals
- previous-year question papers
- viva questions
- assignment questions
- short answer keys or teacher-approved explanations

Do not start with a huge generic internet dataset.

## Recommended Folder Structure

Create your dataset like this:

```text
rag_dataset/
  README.md
  raw/
    calculus/
      syllabus.pdf
      unit1_notes.pdf
      unit2_notes.pdf
      pyq_2024.pdf
      viva_questions.docx
    php/
      syllabus.pdf
      lab_manual.pdf
      assignment_set.pdf
      pyq_2024.pdf
    dsa/
      syllabus.pdf
      recursion_notes.pdf
      complexity_notes.pdf
      pyq_2024.pdf
    japanese/
      syllabus.pdf
      vocab_notes.pdf
      grammar_notes.pdf
      viva_questions.pdf
  processed/
    manifest.csv
    chunks.jsonl
```

## Meaning of Each Part

- `raw/`: your original files
- `processed/manifest.csv`: one row per source file with metadata
- `processed/chunks.jsonl`: final chunked dataset for retrieval

## Best Subjects to Start With

Start with only 3 or 4 subjects.

Recommended:

- Calculus
- PHP / Web Programming
- DSA / Algorithms
- Japanese or your elective/demo-friendly subject

This is enough for a strong demo.

## Best Source Priority

Use this order:

1. Official syllabus
2. Teacher notes / your class notes
3. Lab manuals
4. Previous-year questions
5. Viva questions
6. Short prepared answers

## Best Chunking Strategy

Do not store whole PDFs as one block.

Split the content into chunks that are:

- 150 to 300 words each
- focused on one concept only
- not mixed across many topics
- rich in keywords students would actually ask

Good chunk examples:

- "Chain Rule explanation with formula and one example"
- "PHP associative arrays with syntax and common mistakes"
- "Recursion base case and why stack overflow happens"
- "JLPT N4 vocabulary active recall strategy"

Bad chunk examples:

- a whole unit chapter in one chunk
- half a page of unrelated bullet points
- only formulas without explanation

## Metadata You Should Store

Each chunk should have:

- `chunk_id`
- `subject`
- `unit`
- `topic`
- `source_type`
- `source_name`
- `difficulty`
- `question_type`
- `text`

Optional but useful:

- `semester`
- `course_code`
- `tags`
- `page_number`

## Recommended `source_type` values

- `syllabus`
- `lecture_notes`
- `lab_manual`
- `assignment`
- `pyq`
- `viva`
- `reference_answer`

## Recommended `question_type` values

- `concept`
- `problem_solving`
- `lab_help`
- `exam_prep`
- `viva_prep`

## Example Chunk Format

Use JSONL for chunk storage.

Example:

```json
{"chunk_id":"dsa_001","subject":"DSA","unit":"Recursion","topic":"Base Case","source_type":"lecture_notes","source_name":"recursion_notes.pdf","difficulty":"medium","question_type":"concept","text":"In recursion, the base case is the stopping condition that prevents infinite function calls. Without a base case, the program keeps calling itself until stack overflow occurs. A correct recursive function should define the simplest solvable case first and then reduce the larger problem into a smaller version of the same problem."}
{"chunk_id":"php_001","subject":"PHP","unit":"Arrays","topic":"Associative Arrays","source_type":"lab_manual","source_name":"lab_manual.pdf","difficulty":"easy","question_type":"lab_help","text":"An associative array in PHP stores data as key-value pairs. Instead of numeric indexes, it uses named keys. For example, a student record may use keys like name, roll, and marks. Associative arrays are useful in forms, database results, and structured records."}
```

## Best First Dataset Size

Do not aim too big at first.

Strong first version:

- 20 to 30 source documents
- 150 to 300 chunks
- 3 to 4 subjects

That is enough to make the responses feel real.

## How This Improves Responses

Without real RAG:

- the model answers from general knowledge
- responses sound smart but generic

With real RAG:

- the answer reflects your real course topics
- the bot can mention syllabus concepts and lab-specific language
- exam-prep answers become more relevant
- viva-style questions become more accurate to your subject

## Best Demo Use Cases

Your teacher will notice the improvement most in:

- "Explain chain rule according to our syllabus"
- "Help me with PHP lab arrays"
- "What is recursion and what mistakes do students make?"
- "Give me viva questions from this unit"

## Practical Advice

Start with manually prepared clean text if needed.

Even if you do not yet automate PDF extraction, you can still create a strong dataset by:

- reading your notes
- rewriting them into clean chunked text
- saving them into JSONL

That is completely valid for a student project.

## Best Next Technical Step

When you are ready to implement:

1. build `chunks.jsonl`
2. load it into ChromaDB or FAISS
3. replace the mock retrieval functions in `backend_v2/rag/rag_engine.py`
4. keep the current `build_enriched_prompt()` structure

## One-Line Teacher Explanation

"We are upgrading the RAG layer from mock seed memories to a real course-specific dataset built from syllabus, notes, lab manuals, and previous-year questions, so the tutor can answer based on actual academic material instead of only general model knowledge."
