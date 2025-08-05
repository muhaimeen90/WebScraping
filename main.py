import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from flask import Flask, render_template, jsonify
import re

app = Flask(__name__)

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

def create_price_comparison_chart(df):
    """Create price comparison chart"""
    
    # Calculate average price by store
    avg_prices = df.groupby('store')['price_numeric'].mean().reset_index()
    
    fig = px.bar(avg_prices, x='store', y='price_numeric', 
                 title='Average Coca-Cola Product Prices by Store',
                 labels={'price_numeric': 'Average Price ($)', 'store': 'Store'},
                 color='store',
                 color_discrete_sequence=['#E50000', '#00A651', '#FF6B35'])
    
    fig.update_layout(
        template='plotly_white',
        title_font_size=20,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14
    )
    
    return fig.to_json()

def create_product_count_chart(df):
    """Create product count chart"""
    
    product_counts = df['store'].value_counts().reset_index()
    product_counts.columns = ['store', 'count']
    
    fig = px.pie(product_counts, values='count', names='store',
                 title='Number of Coca-Cola Products by Store',
                 color_discrete_sequence=['#E50000', '#00A651', '#FF6B35'])
    
    fig.update_layout(
        template='plotly_white',
        title_font_size=20
    )
    
    return fig.to_json()

def create_price_distribution_chart(df):
    """Create price distribution chart"""
    
    fig = px.box(df, x='store', y='price_numeric',
                 title='Price Distribution by Store',
                 labels={'price_numeric': 'Price ($)', 'store': 'Store'},
                 color='store',
                 color_discrete_sequence=['#E50000', '#00A651', '#FF6B35'])
    
    fig.update_layout(
        template='plotly_white',
        title_font_size=20,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14
    )
    
    return fig.to_json()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """API endpoint to get all data"""
    df = load_and_process_data()
    
    # Convert to list of dictionaries for JSON serialization
    data = df.to_dict('records')
    
    return jsonify({
        'products': data,
        'price_comparison': json.loads(create_price_comparison_chart(df)),
        'product_count': json.loads(create_product_count_chart(df)),
        'price_distribution': json.loads(create_price_distribution_chart(df))
    })

@app.route('/api/products/<store>')
def get_products_by_store(store):
    """API endpoint to get products by store"""
    df = load_and_process_data()
    store_data = df[df['store'] == store]
    return jsonify(store_data.to_dict('records'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)