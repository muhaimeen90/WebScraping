# 🥤 Coca-Cola Products Price Comparison

A comprehensive web application for comparing Coca-Cola product prices across Australian supermarket chains (Coles, IGA, and Woolworths).

## Features

### 📊 Interactive Data Visualization
- Price comparison charts across stores
- Product count distribution
- Price range analysis with box plots
- Real-time filtering and search

### 🖼️ Product Gallery
- Product images and details
- Store-specific color coding
- Price comparison views
- Responsive design

### 🔍 Advanced Filtering
- Filter by store
- Price range slider
- Product name search
- Real-time updates

## Technologies Used

- **Backend**: Python, Flask, Pandas
- **Data Visualization**: Plotly
- **Frontend**: HTML, Bootstrap, JavaScript
- **Alternative UI**: Streamlit
- **Data Processing**: CSV files with product information

## Project Structure

```
├── main.py                           # Flask web application
├── streamlit_app.py                 # Streamlit alternative interface
├── templates/
│   └── index.html                   # Flask HTML template
├── coles_coca_cola_products.csv     # Coles product data
├── iga_coca_cola_products.csv       # IGA product data
├── woolworths_coca_cola_products.csv # Woolworths product data
└── requirements.txt                 # Python dependencies
```

## Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "week 2"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Applications

### Flask Application
```bash
python main.py
```
Visit: `http://localhost:5000`

### Streamlit Application
```bash
streamlit run streamlit_app.py
```
Visit: `http://localhost:8501`

## Data Sources

The application uses CSV files containing product data from:
- **Coles**: Product names, prices, URLs, and images
- **IGA**: Product names, brands, prices, URLs, and images  
- **Woolworths**: Product names, brands, prices, URLs, and images

## Features Overview

### Flask Version
- Professional web interface with Bootstrap styling
- Interactive Plotly charts
- Real-time filtering without page refresh
- Product cards with images
- Store-specific color themes

### Streamlit Version
- Rapid prototyping interface
- Built-in widgets and components
- Automatic reactivity
- Summary metrics and insights
- Advanced data tables

## Data Processing

The application handles:
- Price normalization (removes '$', handles "Price not available")
- Image URL validation (handles "Image not available")
- Missing data gracefully
- Different CSV column structures

## Future Enhancements

- Real-time web scraping functionality
- Dynamic product search queries
- Price history tracking
- More detailed product comparisons
- Additional store integrations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is for educational and demonstration purposes.
