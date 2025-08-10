# Coca-Cola Price Comparison Tool

A live price scraping application that compares Coca-Cola product prices across three major Australian supermarket chains: IGA, Coles, and Woolworths.

## Features

- **Live Price Scraping**: Real-time price updates using Playwright browser automation
- **Multi-Store Support**: IGA, Coles, and Woolworths integration
- **Interactive Dashboard**: Streamlit-based web interface
- **Individual & Bulk Updates**: Update prices for single products or entire store catalogs
- **Visual Product Display**: Product images and detailed information
- **Price Comparison**: Compare CSV prices with live scraped prices

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

2. **Run the Application**:
   ```bash
   streamlit run streamlit_app.py
   ```

3. **Use the Interface**:
   - Click individual "🔄 Update" buttons to get live prices
   - Use sidebar bulk update buttons for entire store catalogs
   - Switch between store tabs to view different retailer data

## File Structure

```
├── streamlit_app.py          # Main Streamlit application
├── price_scrapers.py         # Live price scraping logic
├── requirements.txt          # Python dependencies
├── coles_coca_cola_products.csv     # Coles product data
├── iga_coca_cola_products.csv       # IGA product data
├── woolworths_coca_cola_products.csv # Woolworths product data
└── README.md                 # This file
```

## Technical Details

- **Frontend**: Streamlit with custom CSS styling
- **Backend**: Playwright for browser automation
- **Browsers**: Firefox (IGA, Woolworths), Chromium (Coles)
- **Data**: CSV files containing product information and URLs

## Dependencies

- streamlit>=1.32.0
- pandas>=2.2.0
- plotly>=5.17.0
- Pillow>=10.2.0
- requests>=2.31.0
- playwright>=1.40.0
- beautifulsoup4>=4.12.0
