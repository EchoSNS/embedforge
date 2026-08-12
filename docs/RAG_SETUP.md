# RAG Setup (Optional)

EmbedForge can optionally use Retrieval-Augmented Generation (RAG) to enhance LLM context with your vendor documentation (datasheets, reference manuals, application notes).

**RAG is NOT required for core functionality.** The plugin system provides sufficient context for most code generation tasks.

## When to Use RAG

- Complex peripheral configurations not fully covered by the plugin catalog
- Migration between MCU families (need reference manual context)
- Application-note-specific patterns (e.g. motor control algorithms)
- Understanding vendor-specific errata or workarounds

## Simple Setup: ChromaDB

### Install RAG dependencies

```bash
pip install -e ".[rag]"
```

### Configure

In `.env`:
```env
EMBEDFORGE_ENABLE_RAG=true
```

### Ingest Documents

```python
from rag import RAGPipeline

pipeline = RAGPipeline(persist_dir="./rag_data")
pipeline.initialize()

# Ingest your vendor documentation
pipeline.ingest_directory("./docs/vendor_pdfs")  # PDFs, markdown, text
```

### Query

```python
results = pipeline.query("How to configure DMA for ADC continuous conversion?")
for chunk in results:
    print(chunk[:200])
```

## File Types Supported

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Datasheets, reference manuals |
| Markdown | `.md` | Application notes, guides |
| Plain text | `.txt` | Any text documentation |

## Directory Structure

```
rag_data/           # Vector store (auto-created)
docs/
  vendor_pdfs/      # Place your documentation here
```
