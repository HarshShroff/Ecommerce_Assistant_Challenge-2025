import pandas as pd
import os
import json
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.retrievers import FAISS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_list(text):
    if pd.isna(text):
        return []
    try:
        return json.loads(text.replace("'", "\""))
    except:
        return []

def create_index():
    data_path = os.environ.get('DATA_PATH', '/data/Product_Information_Dataset.csv')
    index_path = os.environ.get('FAISS_INDEX_PATH', '/data/faiss_index')
    
    logger.info(f"Loading product data from {data_path}")
    df = pd.read_csv(data_path)
    
    logger.info("Initializing embeddings")
    encoder = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
    
    logger.info("Creating documents for indexing")
    documents = []
    metadatas = []
    
    for _, row in df.iterrows():
        title = row['title'] if not pd.isna(row['title']) else ""
        desc = str(row['description']) if not pd.isna(row['description']) else ""
        features = " ".join(parse_list(row['features']))
        
        doc_text = f"{title} {desc} {features}"
        documents.append(doc_text)
        
        metadatas.append({"asin": row['parent_asin']})
    
    logger.info(f"Creating FAISS index with {len(documents)} documents")
    index = FAISS.from_texts(documents, encoder, metadatas=metadatas)
    
    logger.info(f"Saving index to {index_path}")
    os.makedirs(index_path, exist_ok=True)
    index.save_local(index_path)
    logger.info("Index creation complete")

if __name__ == "__main__":
    create_index()
