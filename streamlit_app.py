import os
import subprocess
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import requests
from io import BytesIO
import re
import asyncio
import threading
import time
import glob
from pathlib import Path
import math
from price_scrapers import get_live_price_sync

# Page configuration
st.set_page_config(
    page_title="Grocery Price Comparison",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #E50000, #FF6B35);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    .store-metric {
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem;
    }
    .coles-metric {
        background-color: #E50000;
        color: white;
    }
    .iga-metric {
        background-color: #00A651;
        color: white;
    }
    .woolworths-metric {
        background-color: #FF6B35;
        color: white;
    }
    .product-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def discover_csv_files():
    """Discover all CSV files in store folders"""
    csv_files = {}
    
    # Check IGA folder
    iga_files = {}
    iga_path = Path("IGA")
    if iga_path.exists():
        # Get files in root IGA folder
        for csv_file in iga_path.glob("*.csv"):
            category = csv_file.stem.replace("iga_", "").replace("_", " ").title()
            iga_files[category] = str(csv_file)
        
        # Get files in IGA subfolders
        for subfolder in iga_path.iterdir():
            if subfolder.is_dir():
                subfolder_name = subfolder.name.replace("_", " ").replace(",", " & ").title()
                for csv_file in subfolder.glob("*.csv"):
                    category = f"{subfolder_name} - {csv_file.stem.replace('iga_', '').replace('_', ' ').title()}"
                    iga_files[category] = str(csv_file)
    
    csv_files['IGA'] = iga_files
    
    # Check Woolworths folder
    woolworths_files = {}
    woolworths_path = Path("Woolworths")
    if woolworths_path.exists():
        for csv_file in woolworths_path.glob("*.csv"):
            category = csv_file.stem.replace("woolworths_", "").replace("_", " ").title()
            woolworths_files[category] = str(csv_file)
    
    csv_files['Woolworths'] = woolworths_files
    
    # Check Coles folder
    coles_files = {}
    coles_path = Path("Coles")
    if coles_path.exists():
        for csv_file in coles_path.glob("*.csv"):
            category = csv_file.stem.replace("coles_", "").replace("_", " ").title()
            coles_files[category] = str(csv_file)
    
    csv_files['Coles'] = coles_files
    
    return csv_files

@st.cache_data
def load_csv_data(file_path: str, store_name: str):
    """Load and process individual CSV file"""
    try:
        df = pd.read_csv(file_path)
        df['store'] = store_name
        
        # Standardize column names based on store
        if store_name == 'IGA':
            if 'title' in df.columns:
                df = df.rename(columns={'title': 'product_name'})
            if 'productUrl' in df.columns:
                df = df.rename(columns={'productUrl': 'product_url'})
            if 'imageUrl' in df.columns:
                df = df.rename(columns={'imageUrl': 'image_url'})
                
        elif store_name == 'Woolworths':
            if 'title' in df.columns:
                df = df.rename(columns={'title': 'product_name'})
            if 'producturl' in df.columns:
                df = df.rename(columns={'producturl': 'product_url'})
            if 'imageurl' in df.columns:
                df = df.rename(columns={'imageurl': 'image_url'})
                
        elif store_name == 'Coles':
            if 'name' in df.columns:
                df = df.rename(columns={'name': 'product_name'})
            if 'productURL' in df.columns:
                df = df.rename(columns={'productURL': 'product_url'})
            if 'imageURL' in df.columns:
                df = df.rename(columns={'imageURL': 'image_url'})
        
        # Ensure required columns exist
        required_columns = ['product_name', 'price', 'store']
        for col in required_columns:
            if col not in df.columns:
                if col == 'product_name':
                    df['product_name'] = df.get('title', df.get('name', 'Unknown Product'))
                elif col == 'price':
                    df['price'] = 'Price not available'
                elif col == 'store':
                    df['store'] = store_name
        
        # Add missing columns with default values
        if 'brand' not in df.columns:
            df['brand'] = 'Various'
        if 'image_url' not in df.columns:
            df['image_url'] = None
        if 'product_url' not in df.columns:
            df['product_url'] = None
        if 'category' not in df.columns:
            df['category'] = 'General'
        
        # Keep raw price data without any parsing or validation
        # Just create a copy of the price column for compatibility
        df['price_numeric'] = df['price']
        
        # Don't filter out any rows - show all data as-is
        
        return df
        
    except Exception as e:
        st.error(f"Error loading {file_path}: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def load_and_process_data():
    """Load and process all CSV files - kept for backward compatibility"""
    # This function is kept for any existing functionality that might depend on it
    # but it will return empty DataFrame since we're moving to category-based loading
    return pd.DataFrame()

@st.cache_data
def load_image_from_url(url):
    """Load image from URL with error handling"""
    if not url or pd.isna(url):
        return None
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        return img
    except Exception as e:
        return None

def update_live_price(product_url, store, product_name):
    """Update live price for a specific product"""
    if not product_url or pd.isna(product_url):
        return None, "No product URL available"
    
    try:
        with st.spinner(f'Fetching live price for {product_name}...'):
            result = get_live_price_sync(product_url, store)
            
            if result['status'] == 'success':
                return result['price'], f"✅ Live price updated successfully"
            else:
                return None, f"❌ {result['message']}"
                
    except Exception as e:
        return None, f"❌ Error: {str(e)}"
    except Exception as e:
        return None, f"❌ Error: {str(e)}"

def create_price_comparison_chart(df):
    """Create price comparison chart - disabled for raw price data"""
    # Since we're using raw price strings, charts are not applicable
    return None
    
    fig.update_layout(
        template='plotly_white',
        title_font_size=20,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14,
        height=500
    )
    
    return fig

def create_product_count_chart(df):
    """Create product count chart"""
    if df.empty:
        return None
        
    product_counts = df['store'].value_counts().reset_index()
    product_counts.columns = ['store', 'count']
    
    fig = px.pie(product_counts, values='count', names='store',
                 title='Number of Coca-Cola Products by Store',
                 color_discrete_map={
                     'Coles': '#E50000',
                     'IGA': '#00A651', 
                     'Woolworths': '#FF6B35'
                 })
    
    fig.update_layout(
        template='plotly_white',
        title_font_size=20,
        height=500
    )
    
    return fig

def create_price_distribution_chart(df):
    """Create price distribution chart"""
    if df.empty:
        return None
        
    fig = px.box(df, x='store', y='price_numeric',
                 title='Price Distribution by Store',
                 labels={'price_numeric': 'Price ($)', 'store': 'Store'},
                 color='store',
                 color_discrete_map={
                     'Coles': '#E50000',
                     'IGA': '#00A651', 
                     'Woolworths': '#FF6B35'
                 })
    
    fig.update_layout(
        template='plotly_white',
        title_font_size=20,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14,
        height=500
    )
    
    return fig

def setup_playwright():
    """Install Playwright browsers if not available"""
    try:
        if not os.path.exists("/home/appuser/.cache/ms-playwright"):
            subprocess.run(["playwright", "install", "firefox"], check=False)
            subprocess.run(["playwright", "install", "chromium"], check=False)
    except Exception as e:
        st.warning(f"Could not install browsers: {e}")

def main():
    setup_playwright()
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🛒 Grocery Price Comparison</h1>
        <p>Compare prices across Coles, IGA, and Woolworths</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Discover all available CSV files
    csv_files = discover_csv_files()
    
    # Sidebar for store and category selection
    st.sidebar.header("🏪 Store & Category Selection")
    
    # Store selection
    available_stores = [store for store, files in csv_files.items() if files]
    if not available_stores:
        st.error("No CSV files found in store folders!")
        st.stop()
    
    selected_store = st.sidebar.selectbox('Select Store:', available_stores)
    
    # Category selection based on selected store
    available_categories = list(csv_files[selected_store].keys())
    if not available_categories:
        st.warning(f"No categories found for {selected_store}")
        st.stop()
    
    selected_category = st.sidebar.selectbox('Select Category:', available_categories)
    
    # Load data for selected store and category
    csv_file_path = csv_files[selected_store][selected_category]
    
    with st.spinner(f'Loading {selected_category} products from {selected_store}...'):
        df = load_csv_data(csv_file_path, selected_store)
    
    if df.empty:
        st.error(f"No data could be loaded from {csv_file_path}")
        st.stop()
    
    # Display current selection info
    st.info(f"📋 Showing **{len(df)}** products from **{selected_store} - {selected_category}**")
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Price filter disabled for raw price data
    st.sidebar.info("Price filtering disabled - showing raw CSV prices")
    price_range = None  # No price filtering with raw data
    
    # Search filter
    search_term = st.sidebar.text_input('Search Products:', placeholder='Enter product name...')
    
    # Brand filter (if available)
    if 'brand' in df.columns and not df['brand'].isna().all():
        available_brands = ['All'] + sorted(df['brand'].dropna().unique().tolist())
        selected_brand = st.sidebar.selectbox('Select Brand:', available_brands)
    else:
        selected_brand = 'All'
    
    # Apply filters
    filtered_df = df.copy()
    
    # Skip price filter - using raw price data
    
    # Apply search filter
    if search_term:
        filtered_df = filtered_df[
            filtered_df['product_name'].str.contains(search_term, case=False, na=False)
        ]
    
    # Apply brand filter
    if selected_brand != 'All':
        filtered_df = filtered_df[filtered_df['brand'] == selected_brand]
    
    # Products section with pagination
    st.header("🛍️ Products")
    
    if not filtered_df.empty:
        # Pagination setup
        products_per_page = 30
        total_products = len(filtered_df)
        total_pages = math.ceil(total_products / products_per_page)
        
        # Page selection
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if total_pages > 1:
                current_page = st.selectbox(
                    f'Page (Total: {total_pages} pages, {total_products} products)',
                    range(1, total_pages + 1),
                    format_func=lambda x: f"Page {x} of {total_pages}"
                )
            else:
                current_page = 1
                st.write(f"Showing all {total_products} products")
        
        # Calculate pagination bounds
        start_idx = (current_page - 1) * products_per_page
        end_idx = min(start_idx + products_per_page, total_products)
        
        # Get products for current page
        page_df = filtered_df.iloc[start_idx:end_idx].reset_index(drop=True)
        
        # Sort options
        sort_options = ['Price (Low to High)', 'Price (High to Low)', 'Product Name', 'Brand']
        sort_by = st.selectbox('Sort by:', sort_options)
        
        if sort_by == 'Price (Low to High)':
            page_df = page_df.sort_values('price_numeric')
        elif sort_by == 'Price (High to Low)':
            page_df = page_df.sort_values('price_numeric', ascending=False)
        elif sort_by == 'Product Name':
            page_df = page_df.sort_values('product_name')
        elif sort_by == 'Brand':
            page_df = page_df.sort_values('brand')
        
        # Display pagination info
        st.caption(f"Showing products {start_idx + 1}-{end_idx} of {total_products}")
        
        # Display products
        for idx, product in page_df.iterrows():
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 4, 1, 1])
                
                with col1:
                    # Display image (clickable if URL is present)
                    if pd.notna(product.get('image_url')) and product.get('image_url'):
                        if product.get('product_url'):
                            st.markdown(
                                f"<a href='{product['product_url']}' target='_blank'><img src='{product['image_url']}' width='100' style='border-radius:8px' /></a>",
                                unsafe_allow_html=True
                            )
                        else:
                            st.image(product['image_url'], width=100)
                    else:
                        st.write("🖼️ No Image")
                
                with col2:
                    # Clickable product name
                    if product.get('product_url'):
                        st.markdown(
                            f"<a href='{product['product_url']}' target='_blank' style='text-decoration:none; color:inherit;'><h4 style='margin:0'>{product['product_name']}</h4></a>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.subheader(product['product_name'])
                    
                    # Show brand and category if available
                    if pd.notna(product.get('brand')):
                        st.write(f"**Brand:** {product['brand']}")
                    if pd.notna(product.get('category')):
                        st.write(f"**Category:** {product['category']}")
                    
                    # Store badge
                    store_colors = {
                        'Coles': '#E50000',
                        'IGA': '#00A651',
                        'Woolworths': '#FF6B35'
                    }
                    st.markdown(
                        f"<span style='background-color: {store_colors[product['store']]}; "
                        f"color: white; padding: 0.25rem 0.75rem; border-radius: 15px; "
                        f"font-size: 0.8rem; font-weight: bold;'>{product['store']}</span>",
                        unsafe_allow_html=True
                    )
                
                with col3:
                    # Always show raw CSV price - no session state caching
                    st.metric("Price", product['price'])
                    st.caption("Raw CSV Price")
                
                with col4:
                    # Live price update button - shows result temporarily
                    if product.get('product_url') and not pd.isna(product.get('product_url')):
                        button_key = f"update_{start_idx + idx}"
                        if st.button("🔄 Update Price", key=button_key, help=f"Get live price for {product['product_name']}"):
                            # Update live price and show result
                            live_price, status_message = update_live_price(
                                product['product_url'], 
                                product['store'], 
                                product['product_name']
                            )
                            
                            if live_price is not None:
                                st.success(f"Live Price: ${live_price:.2f}")
                            else:
                                st.error(status_message)
                    else:
                        # Product URL link
                        if product.get('product_url') and not pd.isna(product.get('product_url')):
                            st.markdown(f"[🔗 View Product]({product['product_url']})")
                        else:
                            st.caption("No URL available")
                
                st.divider()
        
        # Pagination navigation at bottom
        if total_pages > 1:
            st.markdown("---")
            col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
            
            with col1:
                if current_page > 1:
                    if st.button("⬅️ Previous"):
                        st.session_state.page = current_page - 1
                        st.rerun()
            
            with col3:
                st.write(f"Page {current_page} of {total_pages}")
            
            with col5:
                if current_page < total_pages:
                    if st.button("Next ➡️"):
                        st.session_state.page = current_page + 1
                        st.rerun()
    
    else:
        st.warning("No products match your current filters. Please adjust your search criteria.")
    
    # Summary statistics
    if not df.empty:
        st.markdown("---")
        st.header("📊 Category Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Products", len(df))
        
        with col2:
            # Show raw price data - no calculations since prices are strings
            st.metric("Price Format", "Raw CSV Data")
        
        with col3:
            # Display sample of price range from data
            if not df.empty:
                sample_prices = df['price'].head(3).tolist()
                sample_text = ", ".join([str(p) for p in sample_prices])
                if len(sample_text) > 20:
                    sample_text = sample_text[:20] + "..."
                st.metric("Sample Prices", sample_text)
            else:
                st.metric("Sample Prices", "N/A")
        
        with col4:
            # Show total unique prices
            if not df.empty:
                unique_prices = df['price'].nunique()
                st.metric("Unique Prices", unique_prices)
            else:
                st.metric("Unique Prices", "N/A")

if __name__ == "__main__":
    main()