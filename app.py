"""
app.py
------
Mumzworld AI Product Discovery Assistant — Streamlit UI
"""

import os
import sys
import streamlit as st
from dotenv import load_dotenv

# ── Environment ───────────────────────────────────────────────────────────────
load_dotenv()

# ── Page config (MUST be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Mumzworld AI Assistant",
    page_icon="🛍️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&family=Playfair+Display:wght@700&display=swap');

html, body, [class*="css"] {
    font-family: 'Nunito', sans-serif;
}

/* ── Page background ── */
.stApp {
    background: linear-gradient(135deg, #fff8f8 0%, #fff0f5 50%, #fff8f8 100%);
}

/* ── Header ── */
.mw-header {
    text-align: center;
    padding: 2rem 0 1rem 0;
}
.mw-header h1 {
    font-family: 'Playfair Display', serif;
    font-size: 2.6rem;
    color: #c0245a;
    margin-bottom: 0.2rem;
    letter-spacing: -0.5px;
}
.mw-header p {
    color: #a05070;
    font-size: 1.05rem;
    font-weight: 600;
    margin-top: 0;
}
.mw-tagline {
    font-size: 0.9rem !important;
    color: #c07090 !important;
    font-weight: 400 !important;
}

/* ── Search box ── */
.stTextInput > div > div > input {
    border: 2px solid #f0a0c0 !important;
    border-radius: 12px !important;
    padding: 0.75rem 1.1rem !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 1rem !important;
    background: #fff !important;
    color: #3a1a2a !important;
    caret-color: #c0245a !important;
    transition: border-color 0.2s, box-shadow 0.2s;
    line-height: 1.5 !important;
}
.stTextInput > div > div > input::placeholder {
    color: #c090a8 !important;
    font-style: italic !important;
    font-weight: 500 !important;
    opacity: 1 !important;
}
.stTextInput > div > div > input:focus {
    border-color: #c0245a !important;
    box-shadow: 0 0 0 3px rgba(192,36,90,0.15) !important;
    outline: none !important;
}
.stTextInput > div > div > input:focus::placeholder {
    color: #ddb0c8 !important;
}

/* ── Error / Warning boxes — force dark text on light bg ── */
.stException, .stAlert, [data-testid="stException"] {
    background: #fff0f3 !important;
    border: 1.5px solid #f0a0b8 !important;
    border-radius: 12px !important;
    color: #7a1030 !important;
}
.stException pre, .stException code,
[data-testid="stException"] pre,
[data-testid="stException"] code {
    background: #ffeef3 !important;
    color: #6a0020 !important;
    font-size: 0.82rem !important;
}
div[data-testid="stAlert"] {
    background: #fff5f0 !important;
    color: #7a2010 !important;
    border-color: #f5b0a0 !important;
}

/* ── Primary button ── */
.stButton > button[kind="primary"],
.stButton > button {
    background: linear-gradient(135deg, #c0245a 0%, #e0507a 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.65rem 2rem !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px;
    cursor: pointer;
    transition: transform 0.15s, box-shadow 0.15s;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(192,36,90,0.35) !important;
}

/* ── Product card ── */
.product-card {
    background: #ffffff;
    border: 1.5px solid #f5d0e0;
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.1rem;
    box-shadow: 0 4px 18px rgba(192,36,90,0.07);
    transition: transform 0.18s, box-shadow 0.18s;
    position: relative;
}
.product-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 28px rgba(192,36,90,0.14);
}
.product-card-rank {
    position: absolute;
    top: -12px;
    left: 20px;
    background: linear-gradient(135deg, #c0245a, #e0507a);
    color: white;
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    font-size: 0.78rem;
    padding: 3px 12px;
    border-radius: 20px;
    letter-spacing: 0.5px;
}
.product-name {
    font-family: 'Playfair Display', serif;
    font-size: 1.15rem;
    color: #2a0a1a;
    font-weight: 700;
    margin: 0.3rem 0 0.15rem 0;
}
.product-brand {
    font-size: 0.85rem;
    color: #c0245a;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
.product-meta {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin: 0.55rem 0;
}
.meta-badge {
    background: #fff0f5;
    border: 1px solid #f5d0e0;
    color: #a03060;
    font-size: 0.78rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 20px;
}
.meta-badge.price {
    background: #fff3e0;
    border-color: #ffd0a0;
    color: #c05010;
}
.why-box {
    background: #fff8fb;
    border-left: 3px solid #c0245a;
    border-radius: 0 8px 8px 0;
    padding: 0.55rem 0.9rem;
    margin-top: 0.6rem;
    font-size: 0.9rem;
    color: #5a2a3a;
    line-height: 1.5;
}
.why-label {
    font-size: 0.75rem;
    font-weight: 800;
    color: #c0245a;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 2px;
}

/* ── Intro line ── */
.intro-line {
    text-align: center;
    font-size: 1.05rem;
    color: #7a3050;
    font-weight: 600;
    margin: 0.8rem 0 1.4rem 0;
    padding: 0.7rem 1.2rem;
    background: #fff0f5;
    border-radius: 12px;
    border: 1px solid #f5d0e0;
}

/* ── No results ── */
.no-results {
    text-align: center;
    padding: 2.5rem 1rem;
    background: #fff8fb;
    border: 1.5px dashed #f0a0c0;
    border-radius: 16px;
    color: #8a3050;
}
.no-results h3 {
    font-family: 'Playfair Display', serif;
    color: #c0245a;
    margin-bottom: 0.4rem;
}

/* ── Budget info ── */
.budget-pill {
    display: inline-block;
    background: #fff0e8;
    border: 1.5px solid #f5c0a0;
    color: #b04010;
    font-size: 0.82rem;
    font-weight: 700;
    padding: 4px 14px;
    border-radius: 20px;
    margin-bottom: 1rem;
}

/* ── Sidebar ── */
.sidebar-title {
    font-family: 'Playfair Display', serif;
    color: #c0245a;
    font-size: 1.1rem;
}

/* ── Spinner ── */
.stSpinner > div > div {
    border-top-color: #c0245a !important;
}

/* ── Divider ── */
hr {
    border-color: #f5d0e0 !important;
    margin: 1.5rem 0 !important;
}

/* ── Examples ── */
.example-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    justify-content: center;
    margin: 0.8rem 0 1.5rem 0;
}
.example-chip {
    background: #fff;
    border: 1.5px solid #f0a0c0;
    color: #c0245a;
    font-size: 0.82rem;
    font-weight: 700;
    padding: 5px 14px;
    border-radius: 20px;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

# ── Ingest on startup (once) ──────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading product catalog…")
def load_system():
    from ingest import ingest
    from search import _get_embed_model
    collection = ingest()          # skips if already indexed
    _get_embed_model()             # warm up embedder
    return collection

load_system()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="mw-header">
    <h1>🌸 Mumzworld</h1>
    <p>AI Product Discovery Assistant</p>
    <span class="mw-tagline">Smart shopping for moms, babies & little ones</span>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="sidebar-title">🎛️ Search Filters</p>', unsafe_allow_html=True)
    st.caption("Refine your product discovery")

    st.markdown("**💰 Max Price (AED)**")
    enable_price_filter = st.toggle("Enable price filter", value=False)
    manual_price = None
    if enable_price_filter:
        manual_price = st.slider(
            "Set max price",
            min_value=10,
            max_value=1500,
            value=500,
            step=10,
            format="%d AED",
        )
        st.caption(f"Showing products up to **{manual_price} AED**")

    st.markdown("---")

    st.markdown("**📊 Number of Results**")
    n_results = st.radio(
        "Show top",
        options=[3, 5],
        index=0,
        horizontal=True,
        format_func=lambda x: f"Top {x}",
    )

    st.markdown("---")

    st.markdown("**💡 Example Queries**")
    examples = [
        "best stroller under 300 AED",
        "safe toy for 2-year-old",
        "gift for new mom",
        "feeding essentials for newborn",
        "travel gear under 500 AED",
        "educational toy for toddler",
    ]
    for ex in examples:
        st.markdown(f"• _{ex}_")

    st.markdown("---")
    st.caption("Powered by ChromaDB · all-MiniLM-L6-v2 · Groq Llama 3.3-70B")

# ── Search Input ──────────────────────────────────────────────────────────────
col1, col2 = st.columns([5, 1])
with col1:
    query = st.text_input(
        label="Search",
        placeholder="Ask anything — e.g. best stroller under 300 AED",
        label_visibility="collapsed",
    )
with col2:
    search_clicked = st.button("Search 🔍", use_container_width=True)

# ── Run Search ────────────────────────────────────────────────────────────────
if search_clicked or (query and query.strip()):
    if not query.strip():
        st.warning("Please enter a search query.")
    else:
        from search import run_query

        with st.spinner("Finding the best products for you…"):
            try:
                result = run_query(
                    query=query.strip(),
                    manual_max_price=manual_price if enable_price_filter else None,
                    n_results=n_results,
                )
            except Exception as e:
                st.markdown(f"""
                <div class="no-results">
                    <h3>⚠️ Something went wrong</h3>
                    <p>Could not complete your search. Please check your API key or internet connection and try again.</p>
                    <p style="font-size:0.78rem; color:#b06070; margin-top:0.5rem;">Details: {str(e)}</p>
                </div>
                """, unsafe_allow_html=True)
                st.stop()

        recommendations = result.get("recommendations", [])
        intro           = result.get("intro", "")
        budget_used     = result.get("budget_used")
        invalid_query   = result.get("invalid_query", False)
        budget_miss     = result.get("budget_miss", False)
        age_miss        = result.get("age_miss", False)
        no_match        = result.get("no_match", False)
        age_range       = result.get("age_range")

        # ── Budget pill ────────────────────────────────────────────────────────
        if budget_used:
            st.markdown(
                f'<div style="text-align:center"><span class="budget-pill">'
                f'💰 Budget filter: up to {int(budget_used)} AED</span></div>',
                unsafe_allow_html=True,
            )

        # ── Age pill ───────────────────────────────────────────────────────────
        if age_range:
            lo, hi = age_range
            if hi >= 999:
                age_label = f"{lo // 12} years and above" if lo >= 12 else f"{lo} months and above"
            elif lo == 0:
                age_label = f"under {hi // 12} years" if hi >= 12 else f"under {hi} months"
            elif lo == hi:
                age_label = f"{lo // 12} years" if lo % 12 == 0 and lo >= 12 else f"{lo} months"
            else:
                lo_str = f"{lo // 12}yr" if lo % 12 == 0 and lo >= 12 else f"{lo}mo"
                hi_str = f"{hi // 12}yr" if hi % 12 == 0 and hi >= 12 else f"{hi}mo"
                age_label = f"{lo_str} – {hi_str}"
            st.markdown(
                f'<div style="text-align:center"><span class="budget-pill" '
                f'style="background:#f0fff0;border-color:#a0d0a0;color:#1a6020;">'
                f'👶 Age filter: {age_label}</span></div>',
                unsafe_allow_html=True,
            )

        # ── Result states ──────────────────────────────────────────────────────
        if invalid_query:
            st.markdown("""
            <div class="no-results">
                <h3>🔍 No matching products found</h3>
                <p>Please try a valid product query.<br>
                Mumzworld carries baby, toddler, and mom products only.<br>
                Try: <em>"best stroller under 400 AED"</em>, <em>"toys for 2-year-old"</em>,
                or <em>"gift for new mom"</em>.</p>
            </div>
            """, unsafe_allow_html=True)

        elif age_miss:
            age_str = ""
            if age_range:
                lo, hi = age_range
                if lo == hi or abs(lo - hi) <= 6:
                    age_str = f"{lo // 12} years" if lo >= 12 and lo % 12 == 0 else f"{lo} months"
                else:
                    age_str = f"that age range"
            st.markdown(f"""
            <div class="no-results">
                <h3>👶 No products found for this age</h3>
                <p>We don't have products in our catalog suitable for <strong>{age_str}</strong>.<br>
                Our catalog covers products for newborns through children up to 12 years.<br>
                Try adjusting the age in your query.</p>
            </div>
            """, unsafe_allow_html=True)

        elif budget_miss:
            budget_str = f"{int(budget_used)} AED" if budget_used else "your budget"
            st.markdown(f"""
            <div class="no-results">
                <h3>💸 No exact match found in this budget</h3>
                <p>We found products matching your search, but none are within <strong>{budget_str}</strong>.<br>
                Try increasing your budget or removing the price filter to see all available options.</p>
            </div>
            """, unsafe_allow_html=True)

        elif no_match or not recommendations:
            st.markdown("""
            <div class="no-results">
                <h3>😕 No exact match found</h3>
                <p>We couldn't find a product that exactly matches your request.<br>
                Try rephrasing — for example: <em>"feeding chair"</em>, <em>"baby stroller"</em>,
                or <em>"newborn essentials"</em>.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Intro line
            if intro:
                st.markdown(f'<div class="intro-line">✨ {intro}</div>', unsafe_allow_html=True)

            # Product cards
            rank_labels = ["🥇 Best Pick", "🥈 Great Choice", "🥉 Also Consider", "4th Pick", "5th Pick"]
            for i, prod in enumerate(recommendations):
                rank_label = rank_labels[i] if i < len(rank_labels) else f"#{i+1}"
                st.markdown(f"""
                <div class="product-card">
                    <span class="product-card-rank">{rank_label}</span>
                    <div class="product-brand">{prod['brand']}</div>
                    <div class="product-name">{prod['product_name']}</div>
                    <div class="product-meta">
                        <span class="meta-badge price">💰 {int(prod['price_aed'])} AED</span>
                        <span class="meta-badge">📦 {prod['category']}</span>
                        <span class="meta-badge">👶 {prod['age_group']}</span>
                    </div>
                    <div class="why-box">
                        <div class="why-label">Why recommended</div>
                        {prod.get('why', prod['description'])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

else:
    # Landing state — example chips
    st.markdown("""
    <div style="text-align:center; padding: 1.5rem 0 0.5rem 0;">
        <p style="color:#a05070; font-weight:600; font-size:0.95rem;">
            Try one of these popular searches:
        </p>
        <div class="example-chips">
            <span class="example-chip">🛒 best stroller under 300 AED</span>
            <span class="example-chip">🧸 safe toy for 2-year-old</span>
            <span class="example-chip">🎁 gift for new mom</span>
            <span class="example-chip">🍼 newborn feeding essentials</span>
            <span class="example-chip">✈️ travel gear under 500 AED</span>
        </div>
    </p>
    """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#c0a0b0; font-size:0.78rem;">'
    '© 2025 Mumzworld AI Assistant · Built with Streamlit · '
    'Semantic search powered by ChromaDB & Sentence Transformers</p>',
    unsafe_allow_html=True,
)