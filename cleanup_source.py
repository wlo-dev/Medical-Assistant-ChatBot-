"""
Deletes all vectors in the 'medicalbot' index that came from a specific
source PDF. Use this to clean up a partial/stuck upload before retrying
with add_pdf.py.

Usage:
    python cleanup_source.py "Data/current-medical-diagnosis-and-treatment-2025-1.pdf"
"""

import sys
import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

INDEX_NAME = "medicalbot"


def cleanup_source(source_path: str):
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    index = pc.Index(INDEX_NAME)

    print(f"Deleting all vectors with source = '{source_path}' ...")
    index.delete(filter={"source": {"$eq": source_path}})
    print("Done. Partial vectors for that source have been removed.")
    print("You can now re-run add_pdf.py for this file.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cleanup_source.py <path_to_pdf_used_before>")
        sys.exit(1)

    cleanup_source(sys.argv[1])