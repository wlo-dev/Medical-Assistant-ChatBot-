from src.helper import load_pdf_file, text_split, download_hugging_face_embeddings
from pinecone.grcp import PineconeGRCP as Pinecone
from pinecone import ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv
import os


load_dotenv()

PINECONE_API_KEY=os.getenv('PINECONE_API_KEY')
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY