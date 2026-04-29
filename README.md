# 🌸 Mumzworld AI Product Discovery Assistant - TRACK A

A smart, semantic search-powered shopping assistant for Mumzworld. Users type natural language queries and receive intelligent, AI-generated product recommendations from a curated catalog.

---

## 🎯 Problem & Solution

Many users know what they want, but not the exact product name. Normal keyword search fails to understand their intent — searching "safe toy for 2-year-old" returns nothing useful if no product is named exactly that.

So, I built a system that understands the user query in natural language, searches the product catalog intelligently using vector embeddings, applies smart filters like budget and age group, and returns the most relevant recommendations with clear reasons why each product fits.

The result is a shopping assistant that thinks like a helpful store associate — not just a search bar.

---

## 🤖 AI Tooling

This project was designed and developed with the assistance of **Claude AI** (Anthropic), which was used throughout the development process — from architecture planning, pipeline design, and code generation to debugging and iterative improvements.

---

## 🏗️ Project Structure

```
mumzworld_ai_product_discovery_assistant/
│
├── app.py                  # Streamlit UI — main entry point
├── ingest.py               # CSV → embeddings → ChromaDB (runs once)
├── search.py               # Semantic search + Groq recommendation engine
│
├── data/
│   └── products.csv        # 50-product catalog
│
├── chroma_db/              # Auto-created: persisted vector store
│
├── .env                    # API keys (never commit to git)
├── requirements.txt        # Python dependencies
└── README.md
```

---

## ⚙️ Setup Instructions (Windows 11 + VS Code)

### 1. Prerequisites
- Python 3.10 or 3.11 (recommended)
- Visual Studio Code
- Git (optional)

### 2. Create & Activate Virtual Environment
Open a terminal in VS Code (`Ctrl + ~`) and run:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

> ⚠️ First install may take a few minutes — it downloads the `all-MiniLM-L6-v2` model (~90MB).

### 4. Verify `.env` File
The `.env` file should already contain your Groq API key:
```
GROQ_API_KEY=your_key_here
```

### 5. Run the Application
```bash
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`

---

## 🚀 How It Works

### On Startup (One-time)
1. `ingest.py` reads `data/products.csv`
2. Each product row is converted to a rich text document
3. `all-MiniLM-L6-v2` generates embeddings for all 50 products
4. Embeddings are stored in `chroma_db/` (skipped on subsequent runs)

### On Each Search Query
1. User types a natural language query (e.g. *"best stroller under 300 AED"*)
2. Budget is auto-extracted from the query text if present
3. The query is embedded using the same sentence-transformer model
4. ChromaDB performs cosine similarity search to find top matching products
5. Optional sidebar price filter is applied as additional refinement
6. Retrieved products + query are sent to **Groq Llama 3.3-70B**
7. Groq generates a personalized intro line + "Why Recommended" for each product
8. Results are displayed as styled product cards in the Streamlit UI

---

## 🔧 Configuration

| Setting | Default | Where to Change |
|---|---|---|
| Number of results | Top 3 | Sidebar radio button |
| Max price filter | Off | Sidebar toggle + slider |
| Embed model | all-MiniLM-L6-v2 | `ingest.py` / `search.py` |
| LLM model | llama-3.3-70b-versatile | `search.py` |
| Chroma DB path | `./chroma_db/` | `ingest.py` |

---

## 💡 Example Queries

| # | Query | Purpose | Expected Result |
|---|---|---|---|
| 1 | `best stroller under 300 AED` | Check budget + category filtering | Only stroller products within 300 AED, stroller ranked first |
| 2 | `safe toy for 2-year-old` | Check correct age-based toy filtering | Only age-appropriate toys for a 2-year-old, no infant/newborn toys |
| 3 | `feeding chair under 50 AED` | Check budget miss handling | "No exact match found in this budget — try increasing your budget" |
| 4 | `laptop under 500 AED` | Check unrelated / out-of-scope query | "No matching products found. Please try a valid product query." |
| 5 | `gift for new mom` | Check open intent mom-care matching | Relevant mom-care products recommended with personalized intro |

---

## 🛠️ Troubleshooting

**ChromaDB re-index**: Delete the `chroma_db/` folder and restart the app to force re-indexing.

**Groq API errors**: Verify your `GROQ_API_KEY` in `.env` is valid and has quota remaining.

**Slow first startup**: Normal — sentence-transformer model is downloading/loading into memory.

---

## 🧰 Tech Stack

| Layer | Component | Technology |
|---|---|---|
| User Interface | Web App | Streamlit |
| Data Ingestion | CSV Parser | Pandas |
| Embedding Model | Sentence Transformer | all-MiniLM-L6-v2 (HuggingFace) |
| Vector Database | Local Persistent Store | ChromaDB |
| Semantic Search | Cosine Similarity | ChromaDB Query Engine |
| LLM | Recommendation Generator | Groq API — Llama 3.3-70B Versatile |
| Environment Config | API Key Management | python-dotenv |
| Language | Backend | Python 3.10 / 3.11 |
| Platform | Development & Runtime | Windows 11 + VS Code |
