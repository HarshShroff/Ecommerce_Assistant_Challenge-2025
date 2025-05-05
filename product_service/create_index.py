import os
import pandas as pd
import json
import logging
import numpy as np
import faiss
from langchain_community.embeddings import HuggingFaceEmbeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_list(text):
    if pd.isna(text):
        return []
    try:
        return json.loads(text.replace("'", '"'))
    except:
        return []

def create_faiss_index():
    data_path = os.environ.get('DATA_PATH', '../data/Product_Information_Dataset.csv')
    index_path = os.environ.get('FAISS_INDEX_PATH', '../data/faiss_index')
    
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
    embeddings = encoder.embed_documents(documents)
    embeddings_array = np.array(embeddings).astype('float32')
    dimension = embeddings_array.shape[1]  # Fix: Use the second dimension
    
    logger.info(f"Creating memory-efficient FAISS index with dimension {dimension}")
    index = faiss.IndexFlatL2(dimension)  # Start with a simple index
    
    logger.info("Adding vectors to index")
    index.add(embeddings_array)
    
    os.makedirs(index_path, exist_ok=True)
    index_file_path = os.path.join(index_path, "index.faiss")
    logger.info(f"Saving index to {index_file_path}")
    faiss.write_index(index, index_file_path)
    
    metadata_file_path = os.path.join(index_path, "metadata.json")
    with open(metadata_file_path, 'w') as f:
        json.dump(metadatas, f)
    
    logger.info("FAISS index creation complete")

if __name__ == "__main__":
    create_faiss_index()
