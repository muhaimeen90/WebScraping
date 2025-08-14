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
from price_scrapers import get_live_price_sync

# Page configuration
st.set_page_config(
    page_title="Coca-Cola Products Price Comparison",
    page_icon="🥤",
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
def load_and_process_data():
    """Load and process all CSV files"""
    
    try:
        # Load Coles data
        coles_df = pd.read_csv('coles_coca_cola_products.csv')
        coles_df['store'] = 'Coles'
        
        # Rename columns to match other stores and handle the new structure
        if 'name' in coles_df.columns:
            coles_df = coles_df.rename(columns={'name': 'product_name'})
        if 'imageURL' in coles_df.columns:
            coles_df = coles_df.rename(columns={'imageURL': 'image_url'})
        # NEW: rename productURL -> product_url when present
        if 'productURL' in coles_df.columns:
            coles_df = coles_df.rename(columns={'productURL': 'product_url'})
        
        # Handle image URLs - replace "Image not available" with None
        if 'image_url' in coles_df.columns:
            coles_df['image_url'] = coles_df['image_url'].replace('Image not available', None)
        else:
            coles_df['image_url'] = None
        
        coles_df['brand'] = 'Coca-Cola'
        
        # Load IGA data
        iga_df = pd.read_csv('iga_coca_cola_products.csv')
        iga_df['store'] = 'IGA'
        
        # Load Woolworths data
        woolworths_df = pd.read_csv('woolworths_coca_cola_products.csv')
        woolworths_df['store'] = 'Woolworths'
        
        # Combine all dataframes
        all_data = []
        
        # Process Coles data
        for _, row in coles_df.iterrows():
            all_data.append({
                'product_name': row['product_name'],
                'brand': row['brand'],
                'price': row['price'],
                'store': row['store'],
                'image_url': row['image_url'],
                'product_url': row.get('product_url') if pd.notna(row.get('product_url')) else None
            })
        
        # Process IGA data
        for _, row in iga_df.iterrows():
            all_data.append({
                'product_name': row['product_name'],
                'brand': row['brand'],
                'price': row['price'],
                'store': row['store'],
                'image_url': row['image_url'],
                'product_url': row.get('product_url') if pd.notna(row.get('product_url')) else None
            })
        
        # Process Woolworths data
        for _, row in woolworths_df.iterrows():
            all_data.append({
                'product_name': row['product_name'],
                'brand': row['brand'],
                'price': row['price'],
                'store': row['store'],
                'image_url': row['image_url'] if row['image_url'] != 'Unknown' else None,
                'product_url': row.get('product_url') if pd.notna(row.get('product_url')) else None
            })
        
        # Create combined dataframe
        combined_df = pd.DataFrame(all_data)
        
        # Clean price data - remove $ and convert to float, handle non-numeric values
        def clean_price(price_str):
            if pd.isna(price_str) or price_str == 'Price not available' or price_str == '':
                return None
            try:
                # Remove $ and commas, then convert to float
                cleaned = str(price_str).replace('$', '').replace(',', '')
                return float(cleaned)
            except (ValueError, AttributeError):
                return None
        
        combined_df['price_numeric'] = combined_df['price'].apply(clean_price)
        
        # Filter out rows with no valid price
        combined_df = combined_df.dropna(subset=['price_numeric'])
        
        return combined_df
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
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
        # st.warning(f"Could not load image: {str(e)}")
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

def create_price_comparison_chart(df):
    """Create price comparison chart"""
    if df.empty:
        return None
        
    avg_prices = df.groupby('store')['price_numeric'].mean().reset_index()
    
    fig = px.bar(avg_prices, x='store', y='price_numeric', 
                 title='Average Coca-Cola Product Prices by Store',
                 labels={'price_numeric': 'Average Price ($)', 'store': 'Store'},
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
        <h1>🥤 Coca-Cola Products Price Comparison</h1>
        <p>Compare prices across Coles, IGA, and Woolworths</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load data
    with st.spinner('Loading data...'):
        df = load_and_process_data()
    
    if df.empty:
        st.error("No data could be loaded. Please check your CSV files.")
        st.stop()
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Store filter
    stores = ['All'] + list(df['store'].unique())
    selected_store = st.sidebar.selectbox('Select Store:', stores)
    
    # Price filter
    min_price = float(df['price_numeric'].min())
    max_price = float(df['price_numeric'].max())
    price_range = st.sidebar.slider(
        'Price Range ($)', 
        min_value=min_price, 
        max_value=max_price, 
        value=(min_price, max_price),
        step=0.50
    )
    
    # Search filter
    search_term = st.sidebar.text_input('Search Products:', placeholder='Enter product name...')
    
    # Live price update section
    st.sidebar.header("🔄 Live Price Updates")
    
    if st.sidebar.button("🔄 Update All Prices", help="Update live prices for all filtered products"):
        if not filtered_df.empty:
            progress_bar = st.sidebar.progress(0)
            status_text = st.sidebar.empty()
            
            total_products = len(filtered_df)
            updated_count = 0
            
            for i, (idx, product) in enumerate(filtered_df.iterrows()):
                if product.get('product_url') and not pd.isna(product.get('product_url')):
                    status_text.text(f"Updating {product['product_name'][:30]}...")
                    
                    live_price, status_message = update_live_price(
                        product['product_url'], 
                        product['store'], 
                        product['product_name']
                    )
                    
                    if live_price is not None:
                        price_key = f"price_{idx}"
                        st.session_state[price_key] = f"${live_price:.2f}"
                        updated_count += 1
                
                progress_bar.progress((i + 1) / total_products)
            
            status_text.text(f"✅ Updated {updated_count}/{total_products} products")
            st.sidebar.success(f"Bulk update completed! {updated_count} prices updated.")
            time.sleep(2)
            st.rerun()
    
    st.sidebar.markdown("---")
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_store != 'All':
        filtered_df = filtered_df[filtered_df['store'] == selected_store]
    
    filtered_df = filtered_df[
        (filtered_df['price_numeric'] >= price_range[0]) & 
        (filtered_df['price_numeric'] <= price_range[1])
    ]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['product_name'].str.contains(search_term, case=False, na=False)
        ]

    # Products section
    st.header("🛍️ Products")
    
    if not filtered_df.empty:
        # Sort options
        sort_options = ['Price (Low to High)', 'Price (High to Low)', 'Product Name', 'Store']
        sort_by = st.selectbox('Sort by:', sort_options)
        
        if sort_by == 'Price (Low to High)':
            filtered_df = filtered_df.sort_values('price_numeric')
        elif sort_by == 'Price (High to Low)':
            filtered_df = filtered_df.sort_values('price_numeric', ascending=False)
        elif sort_by == 'Product Name':
            filtered_df = filtered_df.sort_values('product_name')
        elif sort_by == 'Store':
            filtered_df = filtered_df.sort_values('store')
        
        # Display products with images
        for idx, product in filtered_df.iterrows():
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
                    st.write(f"**Brand:** {product['brand']}")
                    
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
                    # Current price with live update status
                    price_key = f"price_{idx}"
                    status_key = f"status_{idx}"
                    
                    if price_key not in st.session_state:
                        st.session_state[price_key] = product['price']
                        st.session_state[status_key] = ""
                    
                    st.metric("Price", st.session_state[price_key])
                    
                    # Show update status if available
                    if st.session_state[status_key]:
                        st.caption(st.session_state[status_key])
                
                with col4:
                    # Live price update button
                    if product.get('product_url') and not pd.isna(product.get('product_url')):
                        button_key = f"update_{idx}"
                        if st.button("🔄 Update Price", key=button_key, help=f"Get live price for {product['product_name']}"):
                            # Update live price
                            live_price, status_message = update_live_price(
                                product['product_url'], 
                                product['store'], 
                                product['product_name']
                            )
                            
                            if live_price is not None:
                                st.session_state[price_key] = f"${live_price:.2f}"
                                # Update the dataframe for charts
                                filtered_df.loc[idx, 'price'] = f"${live_price:.2f}"
                                filtered_df.loc[idx, 'price_numeric'] = live_price
                            
                            st.session_state[status_key] = status_message
                            st.rerun()
                    else:
                        st.caption("No URL available")
                
                st.divider()
    
    else:
        st.warning("No products match your current filters. Please adjust your search criteria.")

if __name__ == "__main__":
    main()