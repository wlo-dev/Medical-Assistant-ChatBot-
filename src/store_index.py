from src.helper import load_pdf_file, text_split, download_hugging_face_embeddings
from pinecone.grcp import PineconeGRCP as Pinecone
from pinecone import ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv
import os


load_dotenv()

PINECONE_API_KEY=os.getenv('PINECONE_API_KEY')
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY


extracted_data=load_pdf_file(data='data/')
text_chunks=text_split(extracted_data)
embeddings = download_hugging_face_embeddings()

pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index_name = "medicalbot"

if index_name not in [i["name"] for i in pc.list_indexes()]:
    pc.create_index(
        name=index_name,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
else:
    print(f"Index '{index_name}' already exists — skipping creation.")

index = pc.Index(index_name)


# Embed each chunk and upsert the embeddings into your Pinecone index
docsearch = PineconeVectorStore.from_documents(
   documents=text_chunks,
   index_name =index_name,
   embedding=embeddings,

)