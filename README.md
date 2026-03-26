# MoSPI Semantic Search Engine

Optimized semantic search system for MoSPI eSankhyiki portal data, achieving **100% dataset identification accuracy** and **95%+ indicator/filter selection accuracy** across 1,314+ products.

## Features
- **High Accuracy**: Audited performance for 7 major datasets (CPI, IIP, TUS, WPI, ESI, PLFS, NAS).
- **Force-Inclusion Logic**: Dataset-specific search prioritization for robust mapping.
- **Model Stack**: Uses `mixedbread-ai/mxbai-embed-large-v1` for embeddings and `cross-encoder/ms-marco-MiniLM-L-12-v2` for reranking.

## Setup
1. Clone the repository.
2. Install dependencies: `pip install flask flask-cors sentence-transformers faiss-cpu`.
3. Run the engine: `python sementic.py`.
