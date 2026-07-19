"""
Add another PDF to the existing 'medicalbot' Pinecone index.

This does NOT recreate or clear the index — it loads, chunks, embeds,
and appends the new document's vectors alongside whatever is already
indexed. Safe to run multiple times with different PDFs.

Usage:
    python add_pdf.py "Data/another_reference.pdf"
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()

INDEX_NAME = "medicalbot"


def add_pdf(pdf_path: str):
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    print(f"Loading {pdf_path.name}...")
    loader = PyPDFLoader(str(pdf_path))
    documents = loader.load()
    print(f"Loaded {len(documents)} page(s).")

    print("Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunk(s).")

    for chunk in chunks:
        chunk.metadata["source"] = str(pdf_path)

    print("Loading embeddings model...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    print(f"Upserting into existing index '{INDEX_NAME}' in batches...")

    docsearch = PineconeVectorStore.from_existing_index(
        index_name=INDEX_NAME,
        embedding=embeddings,
    )

    batch_size = 100
    total = len(chunks)
    for start in range(0, total, batch_size):
        batch = chunks[start:start + batch_size]
        docsearch.add_documents(batch)
        done = min(start + batch_size, total)
        percent = (done / total) * 100
        print(f"  Uploaded {done}/{total} chunks ({percent:.1f}%)")

    print(f"Done. {total} chunks from {pdf_path.name} added to '{INDEX_NAME}'.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python add_pdf.py <path_to_pdf>")
        sys.exit(1)

    add_pdf(sys.argv[1])