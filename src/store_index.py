from src.helper import load_pdf_file, text_split, download_hugging_face_embeddings
from pinecone.grcp import PineconeGRCP as Pinecone
from pinecone import ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv
import os