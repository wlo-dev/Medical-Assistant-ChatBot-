from langchain.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings


#Extract Data from the PDF file
def load_pdf_file(data):
    loader = DirectoryLoader(data
                             glob="*.pdf",
                             loader_cls=PyPDFLoader)
    
    documents =loader.load()