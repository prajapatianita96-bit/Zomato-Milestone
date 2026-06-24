import streamlit as st
import json
import base64
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.main import load_config, get_recommendations, setup_logging
from src.input_handler import InputValidationError

# --- Configuration ---
st.set_page_config(
    page_title="Zomato AI Recommendations",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Nocturnal Epicure Theme ---
st.markdown("""
<style>
    /* Base Theme */
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide top header and footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #e23744 0%, #b91c28 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        width: 100%;
        padding: 0.75rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(226, 55, 68, 0.4);
        color: white;
        border: none;
    }
    
    /* Inputs */
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input {
        background-color: #1e293b !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }
    
    /* Restaurant Card Glassmorphism */
    .restaurant-card {
        background: #111827;
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 24px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .restaurant-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 48px rgba(0,0,0,0.6), 0 0 24px rgba(226, 55, 68, 0.1);
        border-color: rgba(255,255,255,0.1);
    }
    .card-image-container {
        position: relative;
        width: 100%;
        height: 240px;
    }
    .card-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .rating-overlay {
        position: absolute;
        top: 16px;
        right: 16px;
        background: rgba(15, 23, 42, 0.7);
        backdrop-filter: blur(12px);
        color: white;
        padding: 6px 14px;
        border-radius: 99px;
        font-weight: 700;
        font-size: 14px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .card-body {
        padding: 24px 32px 32px;
    }
    .card-title {
        font-size: 26px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 8px;
        margin-top: 0;
    }
    .card-subtitle {
        color: #94a3b8;
        font-size: 15px;
        font-weight: 500;
        margin-bottom: 24px;
    }
    .ai-explanation {
        background: rgba(255, 255, 255, 0.02);
        padding: 20px;
        border-radius: 16px;
        font-size: 15px;
        line-height: 1.6;
        color: #cbd5e1;
        border: 1px solid rgba(255, 255, 255, 0.06);
        font-style: italic;
        margin-bottom: 24px;
    }
    .ai-header {
        color: #e23744;
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 8px;
        font-style: normal;
    }
</style>
""", unsafe_allow_html=True)

# --- HD Image Gallery Logic ---
HD_IMAGES = {
    'north indian': [
        'https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1631515243349-e0cb75fb8d3a?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1610067056496-6e54252e69de?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=800&q=80&auto=format&fit=crop'
    ],
    'south indian': [
        'https://images.unsplash.com/photo-1610190203036-70138e6ff56f?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1589301760014-d929f39ce9b1?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=800&q=80&auto=format&fit=crop'
    ],
    'chinese': [
        'https://images.unsplash.com/photo-1585032226651-759b368d7246?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1541696432-82c6da8ce7bf?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1525755662778-989d0524087e?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1563245372-f21724e3856d?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1552611052-33e04de081de?w=800&q=80&auto=format&fit=crop'
    ],
    'italian': [
        'https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1473093295043-cdd812d0e601?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1598866594230-a701cdd6eb6a?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1608219992759-8d74ed8d76eb?w=800&q=80&auto=format&fit=crop'
    ],
    'pizza': [
        'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1590947132387-155cc02f3212?w=800&q=80&auto=format&fit=crop'
    ],
    'burger': [
        'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1550547660-d9450f859349?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=800&q=80&auto=format&fit=crop'
    ],
    'japanese': [
        'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1611143669185-af224c5e3252?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1553621042-f6e147245754?w=800&q=80&auto=format&fit=crop',
        'https://images.unsplash.com/photo-1617196034796-73dfa7b1fd56?w=800&q=80&auto=format&fit=crop'
    ]
}

DEFAULT_IMAGES = [
    'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&q=80&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1414235077428-338988a2e8c0?w=800&q=80&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800&q=80&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1493770348161-369560ae357d?w=800&q=80&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=800&q=80&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1504753793650-d4a2b783c15e?w=800&q=80&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1544025162-8111f42d2a45?w=800&q=80&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&q=80&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800&q=80&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800&q=80&auto=format&fit=crop'
]

def get_image_url(cuisine_str, index):
    primary_cuisine = cuisine_str.split(',')[0].strip().lower()
    cuisine_group = HD_IMAGES.get(primary_cuisine)
    
    if cuisine_group:
        return cuisine_group[index % len(cuisine_group)]
    return DEFAULT_IMAGES[index % len(DEFAULT_IMAGES)]

def render_restaurant_card(restaurant, index):
    name = restaurant.get('name', 'Unknown Restaurant')
    rating = restaurant.get('rating') or restaurant.get('aggregate_rating', 'N/A')
    cuisine = restaurant.get('cuisine') or restaurant.get('cuisines', 'Various')
    cost = restaurant.get('cost') or restaurant.get('cost_for_two')
    if cost and "for two" not in str(cost):
        cost = f"₹{cost} for two"
    explanation = restaurant.get('explanation', 'No explanation provided by AI.')
    
    image_url = get_image_url(cuisine, index)
    fallback_url = 'https://images.unsplash.com/photo-1493770348161-369560ae357d?w=800&q=80&auto=format&fit=crop'
    
    card_html = f"""
    <div class="restaurant-card">
        <div class="card-image-container">
            <img src="{image_url}" class="card-image" onerror="this.onerror=null; this.src='{fallback_url}';">
            <div class="rating-overlay">{rating} ⭐</div>
        </div>
        <div class="card-body">
            <h3 class="card-title">{name}</h3>
            <div class="card-subtitle">{cuisine} &bull; {cost}</div>
            
            <div class="ai-explanation">
                <div class="ai-header">● AI INSIGHT</div>
                "{explanation}"
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

# --- App Logic ---
@st.cache_resource
def init_system():
    config = load_config()
    setup_logging(config)
    from src.data_loader import DataLoader
    loader = DataLoader(config)
    df = loader.load()
    locations = sorted(df["location"].unique().tolist())
    cuisines = sorted(df["cuisines"].dropna().unique().tolist())
    
    # Flatten multiple cuisines if necessary for selectbox
    flat_cuisines = set()
    for c_str in cuisines:
        for c in c_str.split(','):
            flat_cuisines.add(c.strip())
            
    return config, locations, sorted(list(flat_cuisines))

config, locations_list, cuisines_list = init_system()

# Sidebar Setup
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/b/bd/Zomato_Logo.svg", width=150)
    st.markdown("### Find Your Next Meal")
    st.markdown("Let AI curate the perfect dining experience for you.")
    
    with st.form("preferences_form"):
        location = st.selectbox("Where are you?", options=locations_list, index=0)
        budget = st.selectbox("Budget", options=["low", "medium", "high"], index=1)
        cuisine = st.selectbox("Cuisine Preference", options=cuisines_list, index=0)
        min_rating = st.slider("Minimum Rating", min_value=0.0, max_value=5.0, value=3.0, step=0.1)
        extra_preferences = st.text_area("Extra Preferences", placeholder="e.g. romantic, live music, rooftop...")
        
        submitted = st.form_submit_button("Find Restaurants")

# Main Content
st.title("Zomato AI Recommendations")

if submitted:
    if not os.getenv("GROQ_API_KEY"):
        st.error("Error: GROQ_API_KEY is missing from environment variables.")
    else:
        preferences = {
            "location": location,
            "budget": budget,
            "cuisine": cuisine,
            "min_rating": min_rating,
            "extra_preferences": extra_preferences
        }
        
        with st.spinner("AI is analyzing thousands of reviews and ratings..."):
            try:
                results = get_recommendations(preferences, config)
                
                if not results:
                    st.warning("No restaurants found matching your precise criteria. Try lowering the rating or changing the budget.")
                else:
                    st.success(f"Found {len(results)} perfect matches for you!")
                    
                    # Display results in columns (e.g. 2 per row)
                    for i in range(0, len(results), 2):
                        cols = st.columns(2)
                        with cols[0]:
                            render_restaurant_card(results[i], i)
                        if i + 1 < len(results):
                            with cols[1]:
                                render_restaurant_card(results[i+1], i+1)
                                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
else:
    st.markdown("""
        <div style='text-align: center; color: #94a3b8; margin-top: 100px;'>
            <h1 style='font-size: 64px; margin-bottom: 0;'>🍽️</h1>
            <h3>Ready for recommendations</h3>
            <p>Enter your preferences in the sidebar to get AI-ranked restaurant suggestions.</p>
        </div>
    """, unsafe_allow_html=True)
