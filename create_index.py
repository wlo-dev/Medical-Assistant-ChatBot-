"""
Creates the 'medicalbot' Pinecone index. Safe to run once — if the index
already exists, this will raise an error rather than silently doing
nothing, so you always know whether it actually created a fresh index.
"""

import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

INDEX_NAME = "medicalbot"

pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

existing = [i["name"] for i in pc.list_indexes()]

if INDEX_NAME in existing:
    print(f"Index '{INDEX_NAME}' already exists — nothing to do.")
else:
    print(f"Creating index '{INDEX_NAME}'...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    print(f"Index '{INDEX_NAME}' created.")