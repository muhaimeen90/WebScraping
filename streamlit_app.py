import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import requests
from io import BytesIO
import re

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
    
    # Load Coles data
    coles_df = pd.read_csv('coles_coca_cola_products.csv')
    coles_df['store'] = 'Coles'
    
    # Rename columns to match other stores and handle the new structure
    if 'name' in coles_df.columns:
        coles_df = coles_df.rename(columns={'name': 'product_name'})
    if 'imageURL' in coles_df.columns:
        coles_df = coles_df.rename(columns={'imageURL': 'image_url'})
    
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
            'image_url': row['image_url']
        })
    
    # Process IGA data
    for _, row in iga_df.iterrows():
        all_data.append({
            'product_name': row['product_name'],
            'brand': row['brand'],
            'price': row['price'],
            'store': row['store'],
            'image_url': row['image_url']
        })
    
    # Process Woolworths data
    for _, row in woolworths_df.iterrows():
        all_data.append({
            'product_name': row['product_name'],
            'brand': row['brand'],
            'price': row['price'],
            'store': row['store'],
            'image_url': row['image_url'] if row['image_url'] != 'Unknown' else None
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

def load_image_from_url(url):
    """Load image from URL"""
    try:
        response = requests.get(url, timeout=5)
        img = Image.open(BytesIO(response.content))
        return img
    except:
        return None

def create_price_comparison_chart(df):
    """Create price comparison chart"""
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

def main():
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
    
    # Summary metrics
    st.header("📊 Summary Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Products",
            value=len(filtered_df),
            delta=f"{len(filtered_df) - len(df)} from total"
        )
    
    with col2:
        avg_price = filtered_df['price_numeric'].mean()
        total_avg = df['price_numeric'].mean()
        st.metric(
            label="Average Price",
            value=f"${avg_price:.2f}",
            delta=f"${avg_price - total_avg:.2f} vs total avg"
        )
    
    with col3:
        min_price_product = filtered_df.loc[filtered_df['price_numeric'].idxmin()] if not filtered_df.empty else None
        if min_price_product is not None:
            st.metric(
                label="Lowest Price",
                value=min_price_product['price'],
                delta=f"{min_price_product['store']}"
            )
    
    with col4:
        max_price_product = filtered_df.loc[filtered_df['price_numeric'].idxmax()] if not filtered_df.empty else None
        if max_price_product is not None:
            st.metric(
                label="Highest Price",
                value=max_price_product['price'],
                delta=f"{max_price_product['store']}"
            )
    
    # Charts
    st.header("📈 Price Analysis")
    
    if not filtered_df.empty:
        # Charts in columns
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = create_price_comparison_chart(filtered_df)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            fig2 = create_product_count_chart(filtered_df)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Price distribution chart (full width)
        fig3 = create_price_distribution_chart(filtered_df)
        st.plotly_chart(fig3, use_container_width=True)
        
        # Products section
        st.header("🛍️ Products")
        
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
                col1, col2, col3 = st.columns([1, 4, 1])
                
                with col1:
                    # Display image
                    if product['image_url']:
                        img = load_image_from_url(product['image_url'])
                        if img:
                            st.image(img, width=100)
                        else:
                            st.write("🖼️ No Image")
                    else:
                        st.write("🖼️ No Image")
                
                with col2:
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
                    st.metric("Price", product['price'])
                
                st.divider()
    
    else:
        st.warning("No products match your current filters. Please adjust your search criteria.")
    
    # Additional insights
    st.header("💡 Insights")
    
    if not df.empty:
        insights_col1, insights_col2 = st.columns(2)
        
        with insights_col1:
            st.subheader("Price Comparison by Store")
            store_stats = df.groupby('store')['price_numeric'].agg(['mean', 'min', 'max', 'count']).round(2)
            store_stats.columns = ['Average Price', 'Min Price', 'Max Price', 'Product Count']
            st.dataframe(store_stats, use_container_width=True)
        
        with insights_col2:
            st.subheader("Most Expensive Products")
            top_expensive = df.nlargest(5, 'price_numeric')[['product_name', 'store', 'price']]
            st.dataframe(top_expensive, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
