import pandas as pd
import os
import json
import numpy as np
import faiss
from langchain_community.embeddings import HuggingFaceEmbeddings
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
    index_path = os.environ.get('FAISS_INDEX_PATH', '../data/faiss_index')
    
    logger.info(f"Loading product data from {data_path}")
    df = pd.read_csv(data_path)
    
    logger.info("Initializing embeddings")
    encoder = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
    
    logger.info("Creating documents for indexing")
    documents = []
    metadatas = []
    
    # Process in batches to save memory
    batch_size = 500
    all_embeddings = []
    all_metadata = []
    
    for i in range(0, len(df), batch_size):
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(df) + batch_size - 1)//batch_size}")
        batch_df = df.iloc[i:i+batch_size]
        
        batch_texts = []
        batch_meta = []
        
        for _, row in batch_df.iterrows():
            title = row['title'] if not pd.isna(row['title']) else ""
            desc = str(row['description']) if not pd.isna(row['description']) else ""
            features = " ".join(parse_list(row['features']))
            
            doc_text = f"{title} {desc} {features}"
            batch_texts.append(doc_text)
            batch_meta.append({"asin": row['parent_asin']})
        
        # Get embeddings for this batch
        batch_embeddings = encoder.embed_documents(batch_texts)
        
        # Store embeddings and metadata
        all_embeddings.extend(batch_embeddings)
        all_metadata.extend(batch_meta)
        
        # Clear memory
        del batch_texts
        del batch_embeddings
        import gc
        gc.collect()
    
    # Convert to numpy array
    embeddings_array = np.array(all_embeddings).astype('float32')
    dimension = embeddings_array.shape[1]
    
    # Create a more memory-efficient index using index_factory
    logger.info(f"Creating memory-efficient FAISS index with dimension {dimension}")
    index = faiss.index_factory(dimension, "IVF100,PQ32")
    
    # Need to train the index
    logger.info("Training the index")
    index.train(embeddings_array)
    
    # Add vectors to the index
    logger.info("Adding vectors to index")
    index.add(embeddings_array)
    
    # Save the index and metadata
    logger.info(f"Saving index to {index_path}")
    os.makedirs(index_path, exist_ok=True)
    faiss.write_index(index, f"{index_path}/index.faiss")
    
    # Save metadata separately
    with open(f"{index_path}/metadata.json", 'w') as f:
        json.dump(all_metadata, f)
    
    logger.info("Index creation complete")

if __name__ == "__main__":
    create_index()
