from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Dict,Tuple,Optional
from datetime import datetime, timedelta
import jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
from langchain_community.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from chat2plot import chat2plot
from matplotlib.figure import Figure
from fastapi.middleware.cors import CORSMiddleware
import warnings
import data_schema_1
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
import plotly.express as px
import json
import io
import re
import chart_keywords
import promptGuide
import instructions
import pandas as pd
import numpy as np
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings


# Suppress specific warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="Data Analysis API")
DATA_SCHEMA = data_schema_1.DATA_SCHEMA
DATA = None  # Global variable to store the dataset
CHAT_HISTORY = []  # Global variable to store chat history
MAX_HISTORY_LENGTH = 5  # Limit chat history length

# Authentication configuration
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Dummy users database
dummy_users = [
    {"username": "testadmin", "password": "Admin@777", "role": "admin"},
    {"username": "testuser", "password": "User@777", "role": "user"},
    {"username": "testuser1", "password": "User@111", "role": "user"},
    {"username": "testuser2", "password": "User@222", "role": "user"},
    {"username": "testuser3", "password": "User@333", "role": "user"},
]

# OAuth2 scheme for token authentication - UPDATED TO MATCH THE LOGIN ENDPOINT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set the CSV file path dynamically
CSV_FILE_PATH = r"Warranty-Aperture for After 2025.csv"  # Change this to the actual path of your CSV file
# CSV_FILE_PATH = os.path.join(BASE_DIR, "COPQ_ANALYTICS", "data.csv")


# User Schema
class User(BaseModel):
    username: str
    password: str
    role: str

# Token Schema
class Token(BaseModel):
    access_token: str
    token_type: str

# Query Request Schema
class QueryRequest(BaseModel):
    query: str

# Helper Function: Authenticate User
def authenticate_user(username: str, password: str):
    for user in dummy_users:
        if user["username"] == username and user["password"] == password:
            return user
    return None

# Helper Function: Create JWT Token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Helper Function: Get Current User
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "role": role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def robust_dataframe_conversion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enhanced robust DataFrame type conversion with consistent null handling
    """
    df = df.copy()
    
    for col in df.columns:
        try:
            # Try to convert to numeric first, coercing errors
            df[col] = pd.to_numeric(df[col], errors='ignore')
        except:
            pass
    
    # Specific schema-based conversions
    for schema_field in DATA_SCHEMA:
        col_name = schema_field['field']
        expected_type = schema_field['type']

        if col_name in df.columns:
            try:
                if expected_type == 'string':
                    # Convert to string, handling NaN values with "(uncategorized)"
                    df[col_name] = df[col_name].astype(str)
                    df[col_name] = df[col_name].replace(['nan', 'None', '', 'NaN','null'], '(Uncategorized)')
                
                elif expected_type == 'integer':
                    # More robust integer conversion - use 0 for nulls (not -1)
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                    df[col_name] = df[col_name].fillna(0).astype('int64')  # Changed from -1 to 0
                
                elif expected_type == 'float':
                    # Convert to float, coercing errors
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                    df[col_name] = df[col_name].fillna(0.0)
                
                elif expected_type == 'date':
                    # More flexible date parsing
                    df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
            
            except Exception as e:
                print(f"Warning: Could not convert column {col_name}. Error: {e}")
                continue

    return df

def load_data():
    """
    Enhanced data loading with more robust error handling
    """
    global DATA
    if os.path.exists(CSV_FILE_PATH):
        try:
            # Use more flexible CSV reading
            df = pd.read_csv(
                CSV_FILE_PATH, 
                encoding="ISO-8859-1", 
                low_memory=False,
                dtype_backend='pyarrow'  # Use pyarrow for better type inference
            )
            
            # Robust conversion
            DATA = robust_dataframe_conversion(df)
            
            # Additional data validation
            print(f"Dataset loaded successfully. Shape: {DATA.shape}")
            print("Available columns:", list(DATA.columns))
            
            # Print unique years if Date column exists
            if 'Date' in DATA.columns:
                years = DATA['Date'].dt.year.unique()
                print("Years in dataset:", sorted(years))
            
            return True
        except Exception as e:
            print(f"Error loading dataset: {e}")
            return False
    else:
        print("Error: CSV file not found at the specified path.")
        return False

def dataframe_to_html_table(df):
    """
    Convert a pandas DataFrame to a styled HTML table with consistent null handling
    """
    if df is None or df.empty:
        return "<p>No data available</p>"
    
    try:
        # Apply standardized formatting (ensure this happens first)
        df = standardize_output_format(df)  # This ensures consistent null handling
        
        # Apply styling to the HTML table
        table_html = df.to_html(
            index=False, 
            classes="table table-striped table-hover table-bordered", 
            border=1,
            escape=False,
            na_rep="0"  # Use "0" for numeric NA values rather than "(Uncategorized)"
        )
        
        # Add custom styling
        styled_table = f"""
        <div class="table-responsive">
        \n\n\n{table_html}\n\n
        </div>
        """
        return styled_table
    except Exception as e:
        print(f"Error creating HTML table: {e}")
        return f"<p>Error generating table: {str(e)}</p>"

def check_uncategorized_percentage(df: pd.DataFrame) -> Tuple[float, bool]:
    """
    Check the percentage of uncategorized values in the DataFrame.
    Returns: (percentage, is_too_high)
    """
    total_cells = df.size
    uncategorized_count = sum(
        df[col].isna().sum() if pd.api.types.is_numeric_dtype(df[col])
        else df[col].apply(lambda x: pd.isna(x) or str(x).lower() in ['nan', 'none', '', 'uncategorized', '(uncategorized)', 'null']).sum()
        for col in df.columns
    )
    percentage = (uncategorized_count / total_cells) * 100 if total_cells > 0 else 0
    return percentage, percentage > 30

#regioon test 001
def generate_plotly_chart(df: pd.DataFrame, query: str) -> str:
    """
    Generate a Plotly chart based on the DataFrame and query with robust handling.  
    """
    try:
        # Validate input DataFrame
        if df is None or df.empty:
            return "<p>No data available for visualization.</p>"
        
        # Check for excessive uncategorized values
        uncategorized_percentage, too_many_uncategorized = check_uncategorized_percentage(df)
        if too_many_uncategorized:
            return f"""
            <div class="alert alert-warning">
                <h4>Visualization Not Recommended</h4>
                <p>The data contains {uncategorized_percentage:.1f}% uncategorized values, which may result in a misleading chart.</p>
            </div>
            """
        
        # Preprocess DataFrame
        df = df.copy()
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(0)
            else:
                df[col] = df[col].fillna("(Uncategorized)").astype(str).replace(['nan', 'None', 'null', '<NA>'], '(Uncategorized)')
        
        # Determine chart type
        query_lower = query.lower().strip()
        chart_type = None
        
        # Keyword-based chart type detection
        from chart_keywords import (
            line_chart_keywords, pie_chart_keywords, scatter_chart_keywords,
            histogram_chart_keywords, bar_chart_keywords
        )
        
        if any(term in query_lower for term in line_chart_keywords):
            chart_type = "line"
        elif any(term in query_lower for term in pie_chart_keywords):
            chart_type = "pie"
        elif any(term in query_lower for term in scatter_chart_keywords):
            chart_type = "scatter"
        elif any(term in query_lower for term in histogram_chart_keywords):
            chart_type = "histogram"
        elif any(term in query_lower for term in bar_chart_keywords):
            chart_type = "bar"
        
        # Data-driven chart type fallback
        if not chart_type:
            date_cols = [col for col in df.columns if any(k in col.lower() for k in ['date', 'year', 'month', 'quarter', 'week'])]
            numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
            categorical_cols = [col for col in df.columns if col not in numeric_cols and df[col].nunique() <= 50]
            
            if date_cols and numeric_cols:
                chart_type = "line"  # Time series
            elif categorical_cols and numeric_cols and len(df) <= 20:
                chart_type = "bar"   # Small categorical dataset
            elif len(numeric_cols) >= 1 and len(df) > 20:
                chart_type = "histogram"  # Numeric distribution
            else:
                chart_type = "bar"   # Default
        
        # Extract x and y columns
        x_col, y_col = extract_columns_from_query(query, df)
        
        # Fallback if column selection fails
        if not x_col or not y_col:
            numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
            categorical_cols = [col for col in df.columns if df[col].nunique() <= 50]
            date_cols = [col for col in df.columns if any(k in col.lower() for k in ['date', 'year', 'month'])]
            
            x_col = next((col for col in date_cols + categorical_cols), df.columns[0] if len(df.columns) > 0 else None)
            y_col = next((col for col in numeric_cols), None)
            if not y_col:
                df['Count'] = 1
                y_col = 'Count'
        
        if x_col not in df.columns or y_col not in df.columns:
            return "<p>Invalid column selection for visualization.</p>"
        
        # Handle time series specifically
        if chart_type == "line" and any(k in x_col.lower() for k in ['date', 'year', 'month', 'quarter', 'week']):
            try:
                if not pd.api.types.is_datetime64_any_dtype(df[x_col]):
                    df[x_col] = pd.to_datetime(df[x_col], errors='coerce')
                df = df.sort_values(by=x_col)
            except:
                pass
        
        # Create chart
        chart_title = f"{y_col} by {x_col}"
        
        if chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, title=chart_title)
            if any(k in x_col.lower() for k in ['date', 'year', 'month']):
                fig.update_xaxes(tickangle=45)
        
        elif chart_type == "line":
            fig = px.line(df, x=x_col, y=y_col, title=chart_title)
            fig.update_traces(mode='lines+markers', marker=dict(size=8))
        
        elif chart_type == "pie":
            if df[x_col].nunique() > 10:
                top_values = df.groupby(x_col)[y_col].sum().nlargest(10).index
                df_pie = df[df[x_col].isin(top_values)].copy()
                if len(df_pie) < len(df):
                    other_sum = df[~df[x_col].isin(top_values)][y_col].sum()
                    other_row = pd.DataFrame({x_col: ['Other'], y_col: [other_sum]})
                    df_pie = pd.concat([df_pie, other_row], ignore_index=True)
                fig = px.pie(df_pie, names=x_col, values=y_col, title=chart_title)
            else:
                fig = px.pie(df, names=x_col, values=y_col, title=chart_title)
        
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, title=chart_title)
            fig.update_traces(marker=dict(size=8))
        
        elif chart_type == "histogram":
            fig = px.histogram(df, x=y_col, title=f"Distribution of {y_col}")
            fig.update_traces(marker_line_width=1, marker_line_color="white")
        
        else:
            return "<p>Unsupported chart type.</p>"
        
        # Update layout
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=50, r=50, t=80, b=80),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_title=x_col,
            yaxis_title=y_col,
            showlegend=True
        )
        
        # Format axes
        if any(k in x_col.lower() for k in ['date', 'year', 'month']):
            fig.update_xaxes(tickangle=45, tickformat="%b %Y" if 'date' in x_col.lower() else None)
        if pd.api.types.is_numeric_dtype(df[y_col]):
            fig.update_yaxes(tickformat=",.0f")
        
        # Convert to HTML
        chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        print("chart html >>>>",chart_html)
        return f"""
        <div class="chart-container">
            <h4>Visualization Type: {chart_type.capitalize()} Chart</h4>
            {chart_html}56
        </div>
        """
    
    except Exception as e:
        print(f"Error generating chart: {e}")
        # Fallback to prompt-based chart generation
        return prompt_based_chart_generation(df, query)

def plot_charts_from_dataframe(df, output_dir="charts"):
    """
    Analyze a DataFrame and generate various charts based on data types.
    
    Parameters:
    df (pandas.DataFrame): Input DataFrame
    output_dir (str): Directory to save the charts
    
    Returns:
    list: List of generated chart file paths
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Initialize list to store chart file paths
    chart_files = []
    
    # Get data types and column names
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    datetime_cols = df.select_dtypes(include=['datetime64']).columns
    
    # Set seaborn style for matplotlib-based charts
    sns.set_style('whitegrid')
    
    # 1. Histogram for numerical columns
    for col in numeric_cols:
        plt.figure(figsize=(8, 6))
        plt.hist(df[col].dropna(), bins=30, edgecolor='black')
        plt.title(f'Histogram of {col}\n(Shows distribution of numerical data)')
        plt.xlabel(col)
        plt.ylabel('Frequency')
        filename = f'{output_dir}/histogram_{col}.png'
        plt.savefig(filename, bbox_inches='tight')
        chart_files.append(filename)
        plt.close()
    
    # 2. Bar/Column Plot for categorical columns
    for col in categorical_cols:
        if df[col].nunique() <= 20:  # Limit to avoid cluttered plots
            plt.figure(figsize=(8, 6))
            df[col].value_counts().plot(kind='bar')
            plt.title(f'Bar Plot of {col}\n(Shows frequency of categorical data)')
            plt.xlabel(col)
            plt.ylabel('Count')
            plt.xticks(rotation=45)
            filename = f'{output_dir}/bar_{col}.png'
            plt.savefig(filename, bbox_inches='tight')
            chart_files.append(filename)
            plt.close()
    
    # 3. Line Plot for datetime vs numerical
    if len(datetime_cols) > 0 and len(numeric_cols) > 0:
        for num_col in numeric_cols:
            for dt_col in datetime_cols:
                plt.figure(figsize=(10, 6))
                plt.plot(df[dt_col], df[num_col])
                plt.title(f'Line Plot: {num_col} vs {dt_col}\n(Shows trends over time)')
                plt.xlabel(dt_col)
                plt.ylabel(num_col)
                plt.xticks(rotation=45)
                filename = f'{output_dir}/line_{num_col}_vs_{dt_col}.png'
                plt.savefig(filename, bbox_inches='tight')
                chart_files.append(filename)
                plt.close()
    
    # 4. Scatter Plot for pairs of numerical columns
    if len(numeric_cols) >= 2:
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                plt.figure(figsize=(8, 6))
                plt.scatter(df[col1], df[col2], alpha=0.5)
                plt.title(f'Scatter Plot: {col1} vs {col2}\n(Shows relationship between two numerical variables)')
                plt.xlabel(col1)
                plt.ylabel(col2)
                filename = f'{output_dir}/scatter_{col1}_vs_{col2}.png'
                plt.savefig(filename, bbox_inches='tight')
                chart_files.append(filename)
                plt.close()
    
    
     # 5. Box Plot for numerical columns by categorical columns
    if len(categorical_cols) > 0 and len(numeric_cols) > 0:
        for cat_col in categorical_cols:
            if df[cat_col].nunique() <= 10:  # Limit to avoid cluttered plots
                for num_col in numeric_cols:
                    plt.figure(figsize=(8, 6))
                    sns.boxplot(x=cat_col, y=num_col, data=df)
                    plt.title(f'Box Plot: {num_col} by {cat_col}\n(Shows distribution across categories)')
                    plt.xticks(rotation=45)
                    filename = f'{output_dir}/box_{num_col}_by_{cat_col}.png'  # Corrected line
                    plt.savefig(filename, bbox_inches='tight')
                    chart_files.append(filename)
                    plt.close()
    
    # 6. Pie Chart for categorical columns
    for col in categorical_cols:
        if df[col].nunique() <= 10:  # Limit for clarity
            plt.figure(figsize=(8, 8))
            df[col].value_counts().plot(kind='pie', autopct='%1.1f%%')
            plt.title(f'Pie Chart of {col}\n(Shows proportion of categories)')
            plt.ylabel('')
            filename = f'{output_dir}/pie_{col}.png'
            plt.savefig(filename, bbox_inches='tight')
            chart_files.append(filename)
            plt.close()
    
    # 7. Donut Chart (similar to pie but with a hole)
    for col in categorical_cols:
        if df[col].nunique() <= 10:
            plt.figure(figsize=(8, 8))
            df[col].value_counts().plot(kind='pie', autopct='%1.1f%%', wedgeprops=dict(width=0.4))
            plt.title(f'Donut Chart of {col}\n(Shows proportion of categories)')
            plt.ylabel('')
            filename = f'{output_dir}/donut_{col}.png'
            plt.savefig(filename, bbox_inches='tight')
            chart_files.append(filename)
            plt.close()
    
    # 8. Treemap Chart for categorical counts
    for col in categorical_cols:
        if df[col].nunique() <= 20:
            counts = df[col].value_counts()
            plt.figure(figsize=(10, 6))
            squarify.plot(sizes=counts, label=counts.index, alpha=0.8)
            plt.title(f'Treemap of {col}\n(Shows hierarchical proportion of categories)')
            plt.axis('off')
            filename = f'{output_dir}/treemap_{col}.png'
            plt.savefig(filename, bbox_inches='tight')
            chart_files.append(filename)
            plt.close()
    
    # 9. Heatmap for numerical correlations
    if len(numeric_cols) >= 2:
        plt.figure(figsize=(10, 8))
        corr = df[numeric_cols].corr()
        sns.heatmap(corr, annot=True, cmap='coolwarm', center=0)
        plt.title('Heatmap of Numerical Correlations\n(Shows correlation between numerical variables)')
        filename = f'{output_dir}/heatmap_correlation.png'
        plt.savefig(filename, bbox_inches='tight')
        chart_files.append(filename)
        plt.close()
    
    # 10. Pareto Chart for categorical counts
    for col in categorical_cols:
        if df[col].nunique() <= 20:
            counts = df[col].value_counts().sort_values(ascending=False)
            cum_percentage = counts.cumsum() / counts.sum() * 100
            fig, ax1 = plt.subplots(figsize=(10, 6))
            ax1.bar(counts.index, counts, color='C0')
            ax1.set_xlabel(col)
            ax1.set_ylabel('Count', color='C0')
            ax2 = ax1.twinx()
            ax2.plot(counts.index, cum_percentage, color='C1', marker='o')
            ax2.set_ylabel('Cumulative Percentage', color='C1')
            ax2.set_ylim(0, 100)
            plt.title(f'Pareto Chart of {col}\n(Shows cumulative contribution of categories)')
            plt.xticks(rotation=45)
            filename = f'{output_dir}/pareto_{col}.png'
            plt.savefig(filename, bbox_inches='tight')
            chart_files.append(filename)
            plt.close()
    
    # 11. Geo Chart (requires lat/lon or location data)
    location_cols = [col for col in df.columns if 'lat' in col.lower() or 'lon' in col.lower() or 'city' in col.lower() or 'country' in col.lower()]
    if len(location_cols) >= 1:
        for col in location_cols:
            try:
                fig = px.scatter_geo(df, locations=col, locationmode='country names', size=numeric_cols[0] if numeric_cols else None)
                fig.update_layout(title=f'Geo Chart of {col}\n(Shows data on a map)')
                filename = f'{output_dir}/geo_{col}.html'
                fig.write_html(filename)
                chart_files.append(filename)
            except:
                warnings.warn(f"Could not generate Geo Chart for {col}: Invalid or missing geospatial data")
    
    # 12. Scatter Map (similar to Geo but with lat/lon)
    if any('lat' in col.lower() for col in df.columns) and any('lon' in col.lower() for col in df.columns):
        lat_col = next(col for col in df.columns if 'lat' in col.lower())
        lon_col = next(col for col in df.columns if 'lon' in col.lower())
        try:
            fig = px.scatter_mapbox(df, lat=lat_col, lon=lon_col, size=numeric_cols[0] if numeric_cols else None, zoom=2)
            fig.update_layout(mapbox_style="open-street-map", title=f'Scatter Map\n(Shows data points on a map)')
            filename = f'{output_dir}/scatter_map.html'
            fig.write_html(filename)
            chart_files.append(filename)
        except:
            warnings.warn("Could not generate Scatter Map: Invalid or missing lat/lon data")
    
    # 13. Waterfall Chart for numerical changes
    if len(numeric_cols) >= 1 and len(datetime_cols) >= 1:
        for num_col in numeric_cols:
            for dt_col in datetime_cols:
                temp_df = df[[dt_col, num_col]].dropna()
                temp_df = temp_df.sort_values(dt_col)
                changes = temp_df[num_col].diff().fillna(temp_df[num_col].iloc[0])
                fig = go.Figure(go.Waterfall(
                    x=temp_df[dt_col], y=changes,
                    textposition="auto", text=[f"{x:.2f}" for x in changes]
                ))
                fig.update_layout(title=f'Waterfall Chart: {num_col} Changes\n(Shows incremental changes over time)')
                filename = f'{output_dir}/waterfall_{num_col}_vs_{dt_col}.html'
                fig.write_html(filename)
                chart_files.append(filename)
    
    # 14. Funnel Chart for categorical stages
    for col in categorical_cols:
        if df[col].nunique() <= 10:
            counts = df[col].value_counts().sort_values(ascending=False)
            fig = go.Figure(go.Funnel(
                y=counts.index, x=counts.values
            ))
            fig.update_layout(title=f'Funnel Chart of {col}\n(Shows sequential stages)')
            filename = f'{output_dir}/funnel_{col}.html'
            fig.write_html(filename)
            chart_files.append(filename)
    
    # 15. Bubble Chart (extension of scatter with size)
    if len(numeric_cols) >= 3:
        col1, col2, col3 = numeric_cols[:3]
        plt.figure(figsize=(8, 6))
        plt.scatter(df[col1], df[col2], s=df[col3]*10, alpha=0.5)
        plt.title(f'Bubble Chart: {col1} vs {col2} (Size: {col3})\n(Shows three numerical variables)')
        plt.xlabel(col1)
        plt.ylabel(col2)
        filename = f'{output_dir}/bubble_{col1}_vs_{col2}.png'
        plt.savefig(filename, bbox_inches='tight')
        chart_files.append(filename)
        plt.close()
    
    # 16. Candlestick Chart (requires OHLC data)
    ohlc_cols = [col for col in df.columns if col.lower() in ['open', 'high', 'low', 'close']]
    if len(ohlc_cols) >= 4 and len(datetime_cols) >= 1:
        temp_df = df[ohlc_cols + [datetime_cols[0]]].dropna()
        fig = go.Figure(data=[go.Candlestick(
            x=temp_df[datetime_cols[0]],
            open=temp_df['open'], high=temp_df['high'],
            low=temp_df['low'], close=temp_df['close']
        )])
        fig.update_layout(title=f'Candlestick Chart\n(Shows stock price movements)')
        filename = f'{output_dir}/candlestick.html'
        fig.write_html(filename)
        chart_files.append(filename)
    else:
        warnings.warn("Could not generate Candlestick Chart: Missing OHLC data")
    
    # 17. Area Chart for datetime vs numerical
    if len(datetime_cols) > 0 and len(numeric_cols) > 0:
        for num_col in numeric_cols:
            for dt_col in datetime_cols:
                plt.figure(figsize=(10, 6))
                plt.fill_between(df[dt_col], df[num_col], alpha=0.5)
                plt.plot(df[dt_col], df[num_col], color='black')
                plt.title(f'Area Chart: {num_col} vs {dt_col}\n(Shows cumulative trends over time)')
                plt.xlabel(dt_col)
                plt.ylabel(num_col)
                plt.xticks(rotation=45)
                filename = f'{output_dir}/area_{num_col}_vs_{dt_col}.png'
                plt.savefig(filename, bbox_inches='tight')
                chart_files.append(filename)
                plt.close()
    
    # 18. KPI Chart (simple metric display)
    for col in numeric_cols:
        plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, f'{col}\nMean: {df[col].mean():.2f}\nMedian: {df[col].median():.2f}',
                 ha='center', va='center', fontsize=12)
        plt.axis('off')
        plt.title(f'KPI Chart for {col}\n(Shows key metrics)')
        filename = f'{output_dir}/kpi_{col}.png'
        plt.savefig(filename, bbox_inches='tight')
        chart_files.append(filename)
        plt.close()
    
    # 19. Sankey Chart (requires source-target data)
    if len(categorical_cols) >= 2:
        src_col, tgt_col = categorical_cols[:2]
        flow = df.groupby([src_col, tgt_col]).size().reset_index(name='value')
        if not flow.empty:
            labels = list(set(flow[src_col]).union(set(flow[tgt_col])))
            src = [labels.index(s) for s in flow[src_col]]
            tgt = [labels.index(t) for t in flow[tgt_col]]
            fig = go.Figure(data=[go.Sankey(
                node=dict(label=labels),
                link=dict(source=src, target=tgt, value=flow['value'])
            )])
            fig.update_layout(title=f'Sankey Chart: {src_col} to {tgt_col}\n(Shows flow between categories)')
            filename = f'{output_dir}/sankey_{src_col}_to_{tgt_col}.html'
            fig.write_html(filename)
            chart_files.append(filename)
        else:
            warnings.warn(f"Could not generate Sankey Chart: No valid flow data between {src_col} and {tgt_col}")
    
    # 20. Radar Chart for numerical columns
    if len(numeric_cols) >= 3:
        means = df[numeric_cols].mean()
        angles = np.linspace(0, 2*np.pi, len(means), endpoint=False).tolist()
        means = means.tolist() + [means[0]]  # Close the loop
        angles += [angles[0]]
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
        ax.fill(angles, means, alpha=0.25)
        ax.plot(angles, means)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(numeric_cols)
        plt.title('Radar Chart of Numerical Means\n(Shows comparison across variables)')
        filename = f'{output_dir}/radar_numerical.png'
        plt.savefig(filename, bbox_inches='tight')
        chart_files.append(filename)
        plt.close()
    
    return chart_files

def prompt_based_chart_generation(df: pd.DataFrame, query: str) -> str:
    """
    Fallback to generate a chart using a prompt to an LLM when defined functions fail.
    """
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not client.api_key:
            raise ValueError("OpenAI API key is missing")

        # Prepare DataFrame summary
        df_summary = f"""
        DataFrame Columns: {list(df.columns)}
        Data Types: {df.dtypes.to_dict()}
        Sample Data (first 3 rows):
        {df.head(3).to_markdown(index=False)}
        Unique Values per Column:
        {{ {', '.join(f"'{col}': {df[col].nunique()}" for col in df.columns)} }}
        """

        # Define the prompt
        prompt = f"""
        You are an expert data visualization assistant. The user has requested a visualization for the query: "{query}".
        The data is provided below:

        {df_summary}

        Based on the query and data:
        1. Recommend the most appropriate chart type (bar, line, pie, scatter, or histogram).
        2. Specify the x-axis and y-axis columns (must exist in the DataFrame).
        3. Provide any necessary data preprocessing steps (e.g., sorting, grouping, handling nulls).
        4. Suggest a chart title.
        5. Provide Plotly Express code to generate the chart.

        Respond in JSON format with the following structure:
        ```json
        {{
            "chart_type": "string",
            "x_column": "string",
            "y_column": "string",
            "preprocessing_steps": ["string"],
            "title": "string",
            "plotly_code": "string"
        }}
        """

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data visualization expert providing accurate Plotly chart recommendations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )

        # Parse response
        response_text = response.choices[0].message.content
        try:
            chart_config = json.loads(response_text)
        except json.JSONDecodeError:
            return "<p>Failed to parse LLM response for chart generation.</p>"

        # Validate response
        required_keys = ["chart_type", "x_column", "y_column", "preprocessing_steps", "title", "plotly_code"]
        if not all(key in chart_config for key in required_keys):
            return "<p>Incomplete chart configuration from LLM.</p>"

        # Validate columns
        if chart_config["x_column"] not in df.columns or chart_config["y_column"] not in df.columns:
            return "<p>Invalid column names in chart configuration.</p>"

        # Apply preprocessing steps
        df_processed = df.copy()
        for step in chart_config["preprocessing_steps"]:
            try:
                if "fillna" in step.lower():
                    df_processed[chart_config["y_column"]] = df_processed[chart_config["y_column"]].fillna(0)
                    df_processed[chart_config["x_column"]] = df_processed[chart_config["x_column"]].fillna("(Uncategorized)")
                elif "sort" in step.lower():
                    df_processed = df_processed.sort_values(by=chart_config["x_column"])
                elif "group" in step.lower():
                    df_processed = df_processed.groupby(chart_config["x_column"])[chart_config["y_column"]].sum().reset_index()
                elif "datetime" in step.lower():
                    df_processed[chart_config["x_column"]] = pd.to_datetime(df_processed[chart_config["x_column"]], errors="coerce")
            except Exception as e:
                print(f"Preprocessing step failed: {step}, Error: {e}")
                continue

        # Generate chart based on chart_type
        chart_type = chart_config["chart_type"].lower()
        title = chart_config["title"]
        x_col = chart_config["x_column"]
        y_col = chart_config["y_column"]

        if chart_type == "bar":
            fig = px.bar(df_processed, x=x_col, y=y_col, title=title)
            fig.update_xaxes(tickangle=45)
        elif chart_type == "line":
            fig = px.line(df_processed, x=x_col, y=y_col, title=title)
            fig.update_traces(mode="lines+markers", marker=dict(size=8))
        elif chart_type == "pie":
            if df_processed[x_col].nunique() > 10:
                top_values = df_processed.groupby(x_col)[y_col].sum().nlargest(10).index
                df_pie = df_processed[df_processed[x_col].isin(top_values)].copy()
                if len(df_pie) < len(df_processed):
                    other_sum = df_processed[~df_processed[x_col].isin(top_values)][y_col].sum()
                    other_row = pd.DataFrame({x_col: ["Other"], y_col: [other_sum]})
                    df_pie = pd.concat([df_pie, other_row], ignore_index=True)
                fig = px.pie(df_pie, names=x_col, values=y_col, title=title)
            else:
                fig = px.pie(df_processed, names=x_col, values=y_col, title=title)
        elif chart_type == "scatter":
            fig = px.scatter(df_processed, x=x_col, y=y_col, title=title)
            fig.update_traces(marker=dict(size=8))
        elif chart_type == "histogram":
            fig = px.histogram(df_processed, x=y_col, title=f"Distribution of {y_col}")
            fig.update_traces(marker_line_width=1, marker_line_color="white")
        else:
            return "<p>Unsupported chart type from LLM response.</p>"

        # Update layout
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=50, r=50, t=80, b=80),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_title=x_col,
            yaxis_title=y_col,
            showlegend=True
        )

        # Format axes
        if any(k in x_col.lower() for k in ["date", "year", "month"]):
            fig.update_xaxes(tickangle=45, tickformat="%b %Y" if "date" in x_col.lower() else None)
        if pd.api.types.is_numeric_dtype(df_processed[y_col]):
            fig.update_yaxes(tickformat=",.0f")

        # Convert to HTML
        chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

        return f"""
        <div class="chart-container">
            <h4>Visualization Type: {chart_type.capitalize()} Chart (LLM Generated)</h4>
            {chart_html}
        </div>
        """

    except Exception as e:
        print(f"Error in prompt-based chart generation: {e}")
        return "<p>Failed to generate chart using LLM fallback.</p>"

def extract_columns_from_query(query: str, df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract potential x and y column names from the query with improved context awareness.
    Returns: (x_col, y_col)
    """
    query_lower = query.lower().strip()
    df_cols_lower = {col.lower(): col for col in df.columns}
    
    metric_keywords = ['cost', 'amount', 'price', 'value', 'sales', 'revenue', 'profit', 'units', 'quantity', 'count']
    category_keywords = ['year', 'month', 'date', 'quarter', 'week', 'business unit', 'region', 'category', 'type', 'code']
    
    x_col, y_col = None, None
    
    # Handle "by" clause explicitly (e.g., "cost by year")
    by_match = re.search(r'\bby\s+(\w+)', query_lower)
    if by_match:
        by_term = by_match.group(1)
        for col_lower, col in df_cols_lower.items():
            if by_term in col_lower or any(keyword in col_lower for keyword in category_keywords):
                x_col = col
                break
    
    # Extract potential column names from query
    query_words = re.findall(r'\b\w+\b', query_lower)
    for word in query_words:
        # Y-axis: Look for metric-related terms
        if not y_col and any(keyword in word for keyword in metric_keywords):
            for col_lower, col in df_cols_lower.items():
                if word in col_lower or any(keyword in col_lower for keyword in metric_keywords):
                    if pd.api.types.is_numeric_dtype(df[col]):  # Ensure numeric
                        y_col = col
                        break
        # X-axis: Look for category/time-related terms
        if not x_col and any(keyword in word for keyword in category_keywords):
            for col_lower, col in df_cols_lower.items():
                if word in col_lower or any(keyword in col_lower for keyword in category_keywords):
                    if df[col].nunique() <= 50:  # Avoid high-cardinality
                        x_col = col
                        break
    
    # Fallback: Use data characteristics if query-based extraction fails
    if not y_col:
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        if numeric_cols:
            # Prefer columns with meaningful names or highest variance
            y_col = max(numeric_cols, key=lambda col: (
                10 if any(k in col.lower() for k in metric_keywords) else 1
            ) * (df[col].var() if not pd.isna(df[col].var()) else 0))
    
    if not x_col:
        # Prefer date/time or low-cardinality categorical columns
        date_cols = [col for col in df.columns if any(k in col.lower() for k in ['date', 'year', 'month', 'quarter', 'week'])]
        categorical_cols = [col for col in df.columns if col not in numeric_cols and df[col].nunique() <= 50]
        x_col = next((col for col in date_cols + categorical_cols), df.columns[0] if len(df.columns) > 0 else None)
    
    return x_col, y_col

def generate_time_series_chart(df, time_col, value_col, title=None):
    """
    Generate a time series chart with proper date handling
    """
    try:
        # Convert time column to datetime if not already
        if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
            # Handle year+month combination
            if time_col.lower() == 'year' and 'month' in df.columns:
                try:
                    # Create a proper date column
                    df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str), format='%Y-%m')
                    time_col = 'Date'
                except:
                    # Try to convert as is
                    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
            else:
                # Standard date conversion
                df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        
        # Sort by date for line chart
        df_sorted = df.sort_values(by=time_col)
        
        # Create chart title if not provided
        if not title:
            title = f"{value_col} over Time"
            
        # Create line chart
        fig = px.line(df_sorted, x=time_col, y=value_col, title=title)
        
        # Add markers for data points
        fig.update_traces(mode='lines+markers', marker=dict(size=8))
        
        # Format axes
        fig.update_xaxes(
            title_text="Time Period",
            tickangle=45,
            tickformat="%b %Y" if 'Date' in df.columns else None
        )
        
        fig.update_yaxes(
            title_text=value_col,
            tickformat=",.0f"  # Format large numbers with commas
        )
        
        # Enhanced layout
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=40, r=40, t=60, b=60),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # Add a trend line
        try:
            if len(df_sorted) >= 3:  # Need at least 3 points for a meaningful trendline
                fig.add_traces(
                    px.scatter(df_sorted, x=time_col, y=value_col, trendline="ols").data[1]
                )
        except:
            pass  # Skip trendline if error
            
        # Return HTML
        chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        
        return chart_html
        
    except Exception as e:
        print(f"Error generating time series chart: {e}")
        return f"<p>Error generating time series visualization: {str(e)}</p>"

def extract_dataframe_from_text(text):
    """
    Attempt to extract table-like data from text response and convert to DataFrame
    """
    try:
        # Check if the response contains structured table data
        if '|' in text and '\n' in text:
            # Try to parse markdown table
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            # Find table boundaries
            start_idx = None
            end_idx = None
            
            for i, line in enumerate(lines):
                if '|' in line:
                    if start_idx is None:
                        start_idx = i
                    end_idx = i
            
            if start_idx is not None and end_idx is not None:
                table_lines = lines[start_idx:end_idx+1]
                # Remove markdown table formatting lines (those with dashes)
                table_lines = [line for line in table_lines if not line.replace('|', '').strip().startswith('---')]
                
                # Parse headers and data
                headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
                data = []
                
                for line in table_lines[1:]:
                    row_data = [cell.strip() for cell in line.split('|') if cell.strip()]
                    if row_data:
                        data.append(row_data)
                
                # Create DataFrame
                if headers and data:
                    # Make sure data rows have the same length as headers
                    data = [row for row in data if len(row) == len(headers)]
                    df = pd.DataFrame(data, columns=headers)
                    return df
        
        # If basic parsing failed, try more aggressive methods
        import re
        
        # Look for table patterns in the text
        table_pattern = r'\b(\w+)\s*\|\s*([\w\s\.]+)\s*\|\s*([\w\s\.]+)'
        matches = re.findall(table_pattern, text)
        
        if matches:
            # Try to determine the number of columns
            col_count = len(matches[0])
            headers = ["Column" + str(i+1) for i in range(col_count)]
            df = pd.DataFrame(matches, columns=headers)
            return df
        
        return None
    except Exception as e:
        print(f"Error extracting DataFrame: {e}")
        return None

def combine_chart_and_table(chart_html, table_html, title="Data Analysis Results"):
    """
    Combine chart and table into a single HTML page
    """
    combined_html = f"""
    <div class="analysis-container">
        <h2>{title}</h2>
        <div class="chart-container">
            <h3>Visualization</h3>
            {chart_html}
        </div>
        <div class="table-container">
            <h3>Data Table</h3>
            {table_html}
        </div>
    </div>
    """
    return combined_html

# Call load_data during startup
load_data()

# Create routers for each group
auth_router = APIRouter(tags=["Auth"])
data_router = APIRouter(tags=["data-analysis"])

# Authentication Endpoints
@auth_router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token({"sub": user["username"], "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.get("/me")
async def read_current_user(current_user: dict = Depends(get_current_user)):
    return current_user

@auth_router.post("/register", response_model=User)
async def register(user: User):
    for existing_user in dummy_users:
        if existing_user["username"] == user.username:
            raise HTTPException(status_code=400, detail="Username already exists")
    new_user = {"username": user.username, "password": user.password, "role": user.role}
    dummy_users.append(new_user)
    return new_user

@auth_router.post("/logout")
async def logout():
    return {"message": "Logout successful. Remove token on frontend."}


def standardize_output_format(df):
    """
    Standardize DataFrame output formatting with consistent null handling
    """
    formatted_df = df.copy()
    
    # Ensure consistent handling of null/NA values
    for col in formatted_df.columns:
        # Check if the column is numeric
        is_numeric = pd.api.types.is_numeric_dtype(formatted_df[col])
        
        if is_numeric:
            # For numeric columns, replace nulls with 0
            formatted_df[col] = formatted_df[col].fillna(0)
        else:
            # For non-numeric columns, replace nulls with "(Uncategorized)"
            formatted_df[col] = formatted_df[col].fillna("(Uncategorized)")
            # Convert objects like pandas NA to string "(Uncategorized)"
            formatted_df[col] = formatted_df[col].astype(str)
            formatted_df[col] = formatted_df[col].replace(['nan', 'None', '', 'NaN', 'null', '<NA>'], '(Uncategorized)')
        
        # Specifically handle percentage columns
        if 'CHANGE' in col.upper() and '%' in str(formatted_df[col].iloc[0]):  # Check if column is a percentage change
            formatted_df[col] = formatted_df[col].replace(['nan%', 'NaN%'], '0%')
            formatted_df[col] = formatted_df[col].fillna('0%')
    
    return formatted_df

# Add this function to check if the response is a list
def is_list_response(text):
    """
    Determine if the response appears to be a list of items rather than tabular data
    """
    # Check for common list indicators
    list_indicators = [
        text.count("\n1.") > 0,  # Numbered list starting with 1.
        text.count("\n- ") > 1,  # Bullet points with dashes
        text.count("\n* ") > 1,  # Bullet points with asterisks
        text.count("\n•") > 1,   # Bullet points with bullet character
        bool(re.search(r'\n\d+\.\s+', text)),  # Any numbered list
        bool(re.search(r'Top \d+ ', text)) and text.count("\n") > 2,  # Contains "Top N" and multiple lines
        bool(re.search(r'(\n\s*([A-Za-z0-9][\)\.:]|\d+[\)\.:])\s+)', text))  # Formatted list with parentheses or periods
    ]
    
    # Look for "Top N" or "N questions" type patterns in the query
    list_keywords = [
        'list', 'top', 'questions', 'reasons', 'factors', 'steps',
        'best', 'worst', 'highest', 'lowest', 'most common',
        'frequently', 'commonly', 'popular', 'tips', 'advice', 'suggestions'
    ]
    
    contains_list_keywords = any(keyword in text.lower() for keyword in list_keywords)
    
    # If we have at least one list indicator or contains list keywords and has multiple lines
    return any(list_indicators) or (contains_list_keywords and text.count("\n") > 2)

# Also update the query_data function to handle lists better
@data_router.post("/query/")
async def query_data(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    global DATA, CHAT_HISTORY
    if DATA is None:
        # Attempt to reload data if not already loaded
        if not load_data():
            raise HTTPException(status_code=400, detail="No data loaded.")
    
    query = request.query
    
   
    
    # Check if this is likely a request for a list
    is_list_request = any(keyword in query.lower() for keyword in [
        'list', 'top', 'questions', 'reasons', 'factors', 'steps',
        'best', 'worst', 'highest', 'lowest', 'most common',
        'frequently', 'commonly', 'popular', 'tips', 'advice', 'suggestions'
    ])
    
    # Check if this is a time comparison request (YoY/MoM)
    is_time_comparison = any(term in query.lower() for term in [
        'yoy', 'mom', 'year over year', 'month over month', 'yearly', 'monthly',
        'compared to last', 'previous year', 'previous month', 'comparison',
        'trend', 'performance over time', 'change since', 'growth'
    ])
    
    # Log the user making the query
    print(f"Query received from user: {current_user['username']} with role: {current_user['role']}")
    print(f"Is this likely a list request? {is_list_request}")
    print(f"Is this likely a time comparison? {is_time_comparison}")

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key is missing")

    final_result = ""
    html_table = ""
    final_result1 = ""
    # Helper function to ensure text summaries
    def ensure_text_summary(response_text, result_df, query, is_time_comparison=False):
        """Ensures that a proper text summary exists without table formatting"""
        
        # Check if there's already a text summary in the response
        lines = response_text.strip().split('\n')
        
        # Extract only the text part before any table formatting
        summary_lines = []
        for line in lines:
            if '|' in line and '-' in line:  # We've reached the table
                break
            if not line.strip().startswith('|'):  # Skip any table lines
                summary_lines.append(line)
        
        summary_text = '\n'.join(summary_lines).strip()
        
        # If we don't have a summary and we have a dataframe, generate one
        if (not summary_text or len(summary_text) < 40) and result_df is not None and not result_df.empty:
            try:
                # Find time columns if they exist
                time_cols = [col for col in result_df.columns if col.lower() in [
                    'year', 'month', 'date', 'period', 'quarter', 'time', 'week'
                ]]
                
                # Create a basic summary
                summary_parts = []
                
                # If this is a time comparison and we have time columns
                if is_time_comparison and time_cols:
                    time_col = time_cols[0]  # Use the first identified time column
                    
                    # Get unique time periods
                    time_periods = sorted(result_df[time_col].unique())
                    
                    if len(time_periods) >= 2:
                        # Find numeric columns for analysis (exclude percentage columns)
                        numeric_cols = [col for col in result_df.columns 
                                      if col not in time_cols and 
                                      col.lower() not in ['difference in %', '% change', 'percent', 'percentage'] and
                                      pd.api.types.is_numeric_dtype(result_df[col])]
                        
                        # For each numeric column, check the changes
                        for col in numeric_cols[:3]:  # Limit to top 3 columns
                            try:
                                # For simple two-period comparison
                                if len(time_periods) == 2:
                                    val1 = result_df[result_df[time_col] == time_periods[0]][col].iloc[0]
                                    val2 = result_df[result_df[time_col] == time_periods[1]][col].iloc[0]
                                    
                                    if val1 != 0:
                                        pct_change = ((val2 - val1) / val1) * 100
                                        direction = "increased" if pct_change > 0 else "decreased"
                                        summary_parts.append(f"{col} {direction} by {abs(pct_change):.1f}% from {time_periods[0]} to {time_periods[1]}")
                            except:
                                continue
                
                # If we couldn't generate specific time comparisons, create a generic summary
                if not summary_parts:
                    # Get column with largest values
                    try:
                        numeric_cols = [col for col in result_df.columns 
                                       if pd.api.types.is_numeric_dtype(result_df[col])]
                        
                        if numeric_cols:
                            max_col = max(numeric_cols, key=lambda col: result_df[max_col].max())
                            max_row_idx = result_df[max_col].idxmax()
                            max_row = result_df.iloc[max_row_idx]
                            
                            # Create a summary for this finding
                            max_value = max_row[max_col]
                            id_col = next((col for col in result_df.columns 
                                          if col.lower() in ['name', 'id', 'category', 'type', 'description']), 
                                          result_df.columns[0])
                            
                            id_value = max_row[id_col]
                            summary_parts.append(f"The highest {max_col} is {max_value:,.2f} for {id_value}.")
                    except:
                        pass
                
                # If we have summary parts, create the summary
                if summary_parts:
                    if len(summary_parts) > 1:
                        summary = f"{summary_parts[0]} {summary_parts[1]}"
                    else:
                        summary = summary_parts[0]
                        
                    # Add information about the dataset
                    summary += f" This analysis is based on {len(result_df)} data points."
                else:
                    # Create a generic summary
                    summary = f"Analysis of {query} based on {len(result_df)} data points. "
                    
                    # For time comparisons, add more context about the periods
                    if is_time_comparison and time_cols:
                        time_col = time_cols[0]
                        time_periods = sorted(result_df[time_col].unique())
                        if len(time_periods) >= 2:
                            summary += f"Comparing {time_periods[0]} to {time_periods[-1]}, "
                    
                    # Add basic info about what's in the data
                    if len(result_df.columns) > 1:
                        main_cols = [col for col in result_df.columns if col not in ['% Change_Cost', '% Change_Units']][:3]
                        summary += f"The data shows values for {', '.join(main_cols)}."
                
                return summary
                    
            except Exception as e:
                print(f"Error generating summary: {e}")
        
        return summary_text if summary_text else "Analysis of the requested data:"

    try:
        # Use latest OpenAI model with enhanced capabilities
        agent = create_pandas_dataframe_agent(
            ChatOpenAI(
                temperature=0, 
                model="gpt-4o-mini", 
                api_key=OPENAI_API_KEY
            ),
            DATA,
            verbose=True,  # Enable for more detailed debugging
            agent_type=AgentType.OPENAI_FUNCTIONS,
            allow_dangerous_code=True
        )

            # print("AGENT OUTPUT: \n"+  agent + "\n")
        
        # Enhanced chat2plot with more robust plotting
        c2p = chat2plot(
            DATA, 
            language="English", 
            chat=ChatOpenAI(
                model="gpt-4o-mini", 
                api_key=OPENAI_API_KEY
            )
        )
        
        # Prepare context from chat history
        context = "\n".join([f"Previous User Query: {entry['query']}\nPrevious Bot Response: {entry['response']}" for entry in CHAT_HISTORY[-MAX_HISTORY_LENGTH:]])
        
      
        # Customize the query format based on the request type
        if is_list_request:
            query_format = "Your response should be formatted as a concise numbered list preceded by a brief introduction, NOT as a table."
        elif is_time_comparison:
            query_format = "This is a time comparison query. Begin with a 2-4 sentence text summary highlighting the key changes, THEN show a properly formatted markdown table with a percentage change column."
        else:
            query_format = "If showing complex data, include a 2-4 sentence description followed by a properly formatted markdown table with proper header and separator rows."
        
        refined_query = f"""Considering previous conversation context:
{context}

Important formatting instructions: {instructions.formatting_instruction}
Format note: {query_format}

New Query: {query}

Remember: For tables, ALWAYS START with a 2-4 sentence text summary BEFORE the table explaining key findings.
For time-based comparisons (YoY, MoM), ALWAYS include percentage changes with + or - prefixes.
For lists of items (like "top N" questions), use a simple numbered list format, not a table.
For tabular data, use proper markdown table format with | separators, header row, and separator row with dashes.
"""
        
        # Check if it's a visualization request
        is_visualization_request = any(term in query.lower() for term in [
            'chart', 'plot', 'graph', 'visualize', 'show', 'display', 'visualisation', 
            'pie', 'bar', 'line', 'scatter', 'histogram', 'trend'
        ])
        
        # For visualization requests, use Plotly
        if is_visualization_request:
            
            try:
                # First get data for visualization
                data_query = f"Based on this query: '{query}', provide the data needed for visualization as a pandas DataFrame with clear column names. Format your response to include only the necessary data in a well-structured markdown table format with proper header and separator rows."
                
                data_res = agent.invoke(data_query)
                data_text = (
                    data_res.get("output") if isinstance(data_res, dict) else 
                    str(data_res) if data_res else 
                    "Could not find data for visualization."
                )
                
                # Extract DataFrame from the text response
                visualization_df = extract_dataframe_from_text(data_text)
                
                if visualization_df is None or visualization_df.empty:
                    # If extraction failed, run a more direct query
                    direct_query = f"For the query '{query}', return a pandas DataFrame with at most 20 rows that would be suitable for visualization. Format your response to show just the table of data with proper markdown table formatting."
                    
                    direct_res = agent.invoke(direct_query)
                    direct_text = (
                        direct_res.get("output") if isinstance(direct_res, dict) else 
                        str(direct_res) if direct_res else 
                        "Could not find data for visualization."
                    )
                    print("************* direct text ****************",direct_text)
                    visualization_df = extract_dataframe_from_text(direct_text)
                
                # If we now have a DataFrame, generate visualization
                if visualization_df is not None and not visualization_df.empty:
                    # Standardize the output format
                    visualization_df = standardize_output_format(visualization_df)
                    
                    # Create a text summary for the visualization
                    summary_query = f"""Based on this data:
{visualization_df.to_string(index=False)}

Generate a 2-3 sentence summary highlighting:
1. The most significant patterns or findings
2. Any notable outliers or special cases
3. The key insight this visualization will demonstrate

Format as plain text paragraph only, no tables."""

                    summary_res = agent.invoke(summary_query)
                    summary_text = (
                        summary_res.get("output") if isinstance(summary_res, dict) else 
                        str(summary_res) if summary_res else 
                        "Visualization of query results."
                    )
                    
                    # Print the exact same DataFrame to terminal for consistency
                    print("************* direct text ****************",direct_text)
                    print("\nVisualization DataFrame (Terminal Output):")
                    print(visualization_df.to_string(index=False))
                    
                    # Generate chart HTML
                    chart_html = generate_plotly_chart(visualization_df, query)
                    
                    # Generate table HTML
                    table_html = dataframe_to_html_table(visualization_df)
                    
                    # Combine into a single HTML response with summary
                    combined_html = combine_chart_and_table(chart_html, table_html, f"{summary_text}")
                    
                    # Store chat history
                    CHAT_HISTORY.append({
                        "query": query,
                        "response": f"{summary_text}",  # Only store the summary
                        "user": current_user["username"]
                    })
                    
                    # Trim chat history if it exceeds max length
                    if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
                        CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
                    
                    print("HTML Content : ", table_html)

                    return {
                        "response": f"{summary_text}",  # Only return the summary
                        "html_content": combined_html,
                        "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
                    }
                else:
                    # Fallback to traditional response
                    print("Could not extract DataFrame for visualization, falling back to text response")
            except Exception as viz_error:
                print(f"Visualization error: {viz_error}")
                # Continue with text-based response as fallback
        
        # Process the analytical query
        res = agent.invoke(refined_query)
        
        # Extract response with multiple fallback mechanisms
        response_text = (
            res.get("output") if isinstance(res, dict) else 
            str(res) if res else 
            "Could not find a definitive answer to your question."
        )
        
        # Enhanced post-processing to ensure proper markdown table formatting
        response_text = response_text.replace(" (blank)", " (Uncategorized)")
        response_text = response_text.replace(" (null)", " (Uncategorized)")
        response_text = response_text.replace(" (empty)", " (Uncategorized)")
        response_text = response_text.replace("Blank: ", "(Uncategorized): ")
        response_text = response_text.replace("Empty: ", "(Uncategorized): ")
        response_text = response_text.replace("Null: ", "(Uncategorized): ")
        response_text = response_text.replace("NA: ", "(Uncategorized): ")
        response_text = response_text.replace("<NA>", "(Uncategorized)")
        
        # Debug output to see what was received
        #print(f"\nRaw response text:\n{response_text[:500]}...")
        
        # Check if the response appears to be a list rather than tabular data
        is_list_response_result = is_list_response(response_text)
        #print(f"Is list response: {is_list_response_result}")
        
        # First check if there's a table in the response
        has_table = '|' in response_text and '\n' in response_text and '-' in response_text
        #print(f"Has table markers: {has_table}")
        
        # Check if the response is short
        is_short_response = len(response_text.split('\n')) < 3 and len(response_text) < 300 and not has_table
        
        # Always attempt to extract DataFrame even if it looks like a list
        result_df = None
        if not is_short_response:
            # Try to extract DataFrame - this uses our improved function
            result_df = extract_dataframe_from_text(response_text)
            #raw_text = remove_newlines_replace(response_text)
            
         

            # Debug output
            if result_df is not None:
                print(f"Successfully extracted DataFrame with shape: {result_df.shape}")
            else:
                print("Failed to extract DataFrame")
        
        # If we found a DataFrame, format it as HTML table
        if result_df is not None and not result_df.empty:
            # Standardize the output format
            result_df = standardize_output_format(result_df)
            
            # Print the exact same DataFrame to terminal for consistency
            #print("\nResult DataFrame (Terminal Output):")
            print(result_df.to_string(index=False))
            
            # Get just the text summary without table formatting
            text_summary = ensure_text_summary(response_text, result_df, query, is_time_comparison)
            
            # Use our improved HTML table function
            html_table = dataframe_to_html_table(result_df)
            # chart_html = generate_plotly_chart(result_df, query)
            chart_html = generate_plotly_chart(result_df, response_text)
            final_table = remove_newlines_replace(html_table)
            # chart_htm = generate_plotly_chart(result_df, response_text)
            final_result = replace_between_pipe_and_I(response_text,"\n" + final_table + "\n")
            #final_result = replace_between_pipe_and_I(final_result1,"\n" + chart_html  + "\n")
            # final_result = final_result + "\n" + chart_html
            

            # print("\n\nfinal_result1: ", final_result1)
            print("\n\nfinal_result: ", final_result)
            print("\n\nchart_html: ",chart_html)

            # print("\nHTML chart content: ", chart_html)
            # print("\ntext_summary: ", text_summary)
            # print("\nhtml_table: ", html_table)
            # print("\nfinal_table: ", final_table)
            
            # Store chat history with user information - using just the text summary
            CHAT_HISTORY.append({
                "query": query,
                "response": text_summary,
                "user": current_user["username"]
            })
            
            # Trim chat history if it exceeds max length
            if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
                CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            
            # Only return the summary text in the response
            return {
                    "response": final_result,
                    "chart_html": chart_html # Only include the summary text
                   }
        else:
            # Force a fallback attempt for responses that contain pipe characters but weren't properly parsed
            if has_table and '|' in response_text:
                print("Attempting fallback table parsing for response with pipe characters")
                
                # Clean up the text to make it more parseable
                cleaned_text = re.sub(r'\n\s*\n', '\n', response_text)  # Remove extra blank lines
                
                lines = [line.strip() for line in cleaned_text.split('\n') if '|' in line.strip()]
                
                if len(lines) >= 2:  # Need at least header and one data row
                    # Try to find the header line
                    header_line = lines[0]
                    
                    # Extract header cells
                    header_cells = [cell.strip() for cell in header_line.split('|') if cell.strip()]
                    
                    if header_cells:
                        data_rows = []
                        for line in lines[1:]:
                            # Skip separator rows
                            if re.match(r'^[\s\-\+\|:]*$', line):
                                continue
                                
                            # Extract cells
                            cells = [cell.strip() for cell in line.split('|') if cell]
                            
                            if cells:
                                # Adjust length to match headers
                                while len(cells) < len(header_cells):
                                    cells.append("(Uncategorized)")
                                    
                                if len(cells) > len(header_cells):
                                    cells = cells[:len(header_cells)]
                                    
                                data_rows.append(cells)
                        
                        if data_rows:
                            # Create dataframe
                            manual_df = pd.DataFrame(data_rows, columns=header_cells)
                            manual_df = standardize_output_format(manual_df)
                            
                            # Extract only the text summary
                            text_summary = ensure_text_summary(response_text, manual_df, query, is_time_comparison)
                            
                            # Generate HTML
                            html_table = dataframe_to_html_table(manual_df)
                            
                            print("Generated HTML table content (fallback method)")
                            
                            # Store in chat history - only the text summary
                            CHAT_HISTORY.append({
                                "query": query,
                                "response": text_summary,
                                "user": current_user["username"]
                            })
                            
                            # Trim if needed
                            if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
                                CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
                            
                            # Return only the text summary in the response
                            return {
                                "response": text_summary,  # Only include the summary text
                                "html_content": html_table,
                                "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
                            }
            
            # If still no DataFrame, just return the text response
            # print("\nText Response (Terminal Output):")
            # print(response_text)
            # print("\Final Result Response (Terminal Output): "+ final_result)
            
            
            # Store chat history with user information
            CHAT_HISTORY.append({
                "query": query,
                "response": response_text,
                "user": current_user["username"]
            })
            
            # Trim chat history if it exceeds max length
            if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
                CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            
            # final_result = final_result or response_text
            final_result = final_result if final_result != "" else response_text

            return {
                "response": final_result,
                "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
            }
    
    except Exception as e:
        print(f"Query processing error: {e}")
        return {
            "response": f"An error occurred during query processing: {str(e)}",
            "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
        }

def replace_between_pipe_and_I(text, replacement):
    start = text.find('|')
    end = text.rfind('|')
    if start != -1 and end != -1 and start < end:
        return text[:start] + replacement + text[end+1:]
    return text  # Return original if conditions not met

def remove_newlines_replace(text):
    return text.replace('\n', '')

# Also update the extract_dataframe_from_text function for better table detection
def extract_dataframe_from_text(text):
    """
    Enhanced function to extract table-like data from text response and convert to DataFrame
    With improved detection to handle various table formats
    """
    try:
        # Check if the response contains structured table data
        if '|' in text and '\n' in text:
            # Try to parse markdown table with more lenient approach
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Look for lines with pipe characters (potential table rows)
            table_lines = [line for line in lines if '|' in line]
            
            if len(table_lines) >= 2:  # Need at least header and one data row
                # Find the most common pipe count to handle inconsistent formatting
                pipe_counts = [line.count('|') for line in table_lines]
                most_common_count = max(set(pipe_counts), key=pipe_counts.count)
                
                # Filter lines to those with the most common pipe count (± 1 to allow minor variations)
                consistent_lines = [line for line, count in zip(table_lines, pipe_counts) 
                                   if abs(count - most_common_count) <= 1]
                
                if len(consistent_lines) >= 2:  # Still need at least header and one data row
                    # Skip separator rows (those with mostly dashes)
                    data_lines = [line for line in consistent_lines 
                                 if not (line.replace('|', '').replace('-', '').replace(':', '').strip() == '')]
                    
                    if len(data_lines) >= 2:
                        # Parse headers from first line
                        headers = [h.strip() for h in data_lines[0].split('|') if h.strip()]
                        
                        # If we have reasonable headers, proceed with data extraction
                        if len(headers) >= 2:
                            data = []
                            for line in data_lines[1:]:
                                # Split by pipe and clean up each cell
                                cells = [cell.strip() for cell in line.split('|')]
                                # Remove empty elements at start/end if they exist (from leading/trailing pipes)
                                if cells and not cells[0]: cells = cells[1:]
                                if cells and not cells[-1]: cells = cells[:-1]
                                
                                if cells:
                                    # Ensure rows match header length
                                    while len(cells) < len(headers):
                                        cells.append("(Uncategorized)")
                                    # Truncate if too long
                                    cells = cells[:len(headers)]
                                    data.append(cells)
                            
                            if data:
                                df = pd.DataFrame(data, columns=headers)
                                return standardize_output_format(df)
        
        # Check for HTML tables
        if '<table' in text and '</table>' in text:
            try:
                # Use pandas to parse HTML tables
                dfs = pd.read_html(text)
               # print("gfdddff: ",dfs)
                if dfs and len(dfs) > 0:
                    return standardize_output_format(dfs[0])
            except Exception as html_err:
                print(f"HTML table parsing error: {html_err}")
        
        # Fall back to checking for tabular patterns in plain text
        if '\n' in text:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) >= 3:  # Need header, separator, and at least one data row
                # Check if there's a consistent pattern of data alignment
                # First look for spaces or common separators
                potential_delimiters = ['\t', '  ', ',', ';']
                
                for delimiter in potential_delimiters:
                    if any(delimiter in line for line in lines[:3]):
                        try:
                            # Try parsing with this delimiter
                            headers = [h.strip() for h in re.split(r'\s{2,}|\t|,|;', lines[0]) if h.strip()]
                            if len(headers) >= 2:
                                data = []
                                for line in lines[1:]:
                                    # Skip separator lines
                                    if re.match(r'^[-+:|\s]+$', line):
                                        continue
                                    
                                    cells = [c.strip() for c in re.split(r'\s{2,}|\t|,|;', line) if c.strip()]
                                    if len(cells) >= len(headers) * 0.7:  # Allow some flexibility
                                        # Pad or truncate as needed
                                        while len(cells) < len(headers):
                                            cells.append("(Uncategorized)")
                                        cells = cells[:len(headers)]
                                        data.append(cells)
                                
                                if data:
                                    df = pd.DataFrame(data, columns=headers)
                                    return standardize_output_format(df)
                        except Exception as delim_err:
                            print(f"Delimiter parsing error: {delim_err}")
                            continue
        
        return None
    except Exception as e:
        print(f"Error extracting DataFrame: {e}")
        return None

@data_router.post("/clear_chat/")
async def clear_chat(current_user: dict = Depends(get_current_user)):
    """Clear entire chat history"""
    global CHAT_HISTORY
    
    # Check if user is admin for additional permissions
    if current_user["role"] == "admin":
        CHAT_HISTORY = []
        return {"message": "Chat history cleared successfully."}
    else:
        # For non-admin users, only clear their own chat history
        CHAT_HISTORY = [entry for entry in CHAT_HISTORY if entry.get("user") != current_user["username"]]
        return {"message": f"Chat history for user {current_user['username']} cleared successfully."}

# Include both routers in the main app
app.include_router(auth_router)
app.include_router(data_router)

if __name__ == "__main__":
    # uvicorn.run(app, host="10.61.24.68", port=8000)
    uvicorn.run(app, host="localhost", port=8000)


###########################################################################################################################
# from fastapi import FastAPI, HTTPException, Depends, status
# from pydantic import BaseModel
# from typing import List, Dict
# from datetime import datetime, timedelta
# import jwt
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# import pandas as pd
# import os
# from dotenv import load_dotenv
# from openai import OpenAI
# from langchain_community.chat_models import ChatOpenAI
# from langchain.agents.agent_types import AgentType
# from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
# from chat2plot import chat2plot
# from matplotlib.figure import Figure
# from fastapi.middleware.cors import CORSMiddleware
# import warnings
# import data_schema_1
# import uvicorn
# from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
# import plotly.express as px
# import json
# import io
# import re
# import chart_keywords
# import promptGuide
# import instructions
# from functools import lru_cache
# from langchain.chat_models import ChatOpenAI  # If not already imported

# @lru_cache(maxsize=128)
# def get_cached_llm():
#     return ChatOpenAI(
#         temperature=0,
#         model="gpt-4o-mini",
#         api_key=OPENAI_API_KEY,
#     )


# # Suppress specific warnings
# warnings.filterwarnings('ignore', category=UserWarning)
# warnings.filterwarnings('ignore', category=DeprecationWarning)

# # Load environment variables
# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# app = FastAPI(title="Data Analysis API")
# DATA_SCHEMA = data_schema_1.DATA_SCHEMA
# DATA = None  # Global variable to store the dataset
# CHAT_HISTORY = []  # Global variable to store chat history
# MAX_HISTORY_LENGTH = 5  # Limit chat history length

# # Authentication configuration
# SECRET_KEY = "your_secret_key_here"
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 60

# # Dummy users database
# dummy_users = [
#     {"username": "testadmin", "password": "Admin@777", "role": "admin"},
#     {"username": "testuser", "password": "User@777", "role": "user"},
#     {"username": "testuser1", "password": "User@111", "role": "user"},
#     {"username": "testuser2", "password": "User@222", "role": "user"},
#     {"username": "testuser3", "password": "User@333", "role": "user"},
# ]

# # OAuth2 scheme for token authentication - UPDATED TO MATCH THE LOGIN ENDPOINT
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# # CORS middleware setup
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Set the CSV file path dynamically
# CSV_FILE_PATH = r"Warranty_Apertures_After2023 Latest Data.csv"  # Change this to the actual path of your CSV file
# # CSV_FILE_PATH = os.path.join(BASE_DIR, "COPQ_ANALYTICS", "data.csv")


# # User Schema
# class User(BaseModel):
#     username: str
#     password: str
#     role: str

# # Token Schema
# class Token(BaseModel):
#     access_token: str
#     token_type: str

# # Query Request Schema
# class QueryRequest(BaseModel):
#     query: str

# # Helper Function: Authenticate User
# def authenticate_user(username: str, password: str):
#     for user in dummy_users:
#         if user["username"] == username and user["password"] == password:
#             return user
#     return None

# # Helper Function: Create JWT Token
# def create_access_token(data: dict, expires_delta: timedelta = None):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# # Helper Function: Get Current User
# def get_current_user(token: str = Depends(oauth2_scheme)):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username = payload.get("sub")
#         role = payload.get("role")
#         if username is None:
#             raise HTTPException(status_code=401, detail="Invalid token")
#         return {"username": username, "role": role}
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token expired")
#     except jwt.InvalidTokenError:
#         raise HTTPException(status_code=401, detail="Invalid token")


# def robust_dataframe_conversion(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Enhanced robust DataFrame type conversion with consistent null handling
#     """
#     df = df.copy()
    
#     for col in df.columns:
#         try:
#             # Try to convert to numeric first, coercing errors
#             df[col] = pd.to_numeric(df[col], errors='ignore')
#         except:
#             pass
    
#     # Specific schema-based conversions
#     for schema_field in DATA_SCHEMA:
#         col_name = schema_field['field']
#         expected_type = schema_field['type']

#         if col_name in df.columns:
#             try:
#                 if expected_type == 'string':
#                     # Convert to string, handling NaN values with "(uncategorized)"
#                     df[col_name] = df[col_name].astype(str)
#                     df[col_name] = df[col_name].replace(['nan', 'None', '', 'NaN','null'], '(Uncategorized)')
                
#                 elif expected_type == 'integer':
#                     # More robust integer conversion - use 0 for nulls (not -1)
#                     df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
#                     df[col_name] = df[col_name].fillna(0).astype('int64')  # Changed from -1 to 0
                
#                 elif expected_type == 'float':
#                     # Convert to float, coercing errors
#                     df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
#                     df[col_name] = df[col_name].fillna(0.0)
                
#                 elif expected_type == 'date':
#                     # More flexible date parsing
#                     df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
            
#             except Exception as e:
#                 print(f"Warning: Could not convert column {col_name}. Error: {e}")
#                 continue

#     return df

# def load_data():
#     """
#     Enhanced data loading with more robust error handling
#     """
#     global DATA
#     if os.path.exists(CSV_FILE_PATH):
#         try:
#             # Use more flexible CSV reading
#             df = pd.read_csv(
#                 CSV_FILE_PATH, 
#                 encoding="ISO-8859-1", 
#                 low_memory=False,
#                 dtype_backend='pyarrow'  # Use pyarrow for better type inference
#             )
            
#             # Robust conversion
#             DATA = robust_dataframe_conversion(df)
            
#             # Additional data validation
#             print(f"Dataset loaded successfully. Shape: {DATA.shape}")
#             print("Available columns:", list(DATA.columns))
            
#             # Print unique years if Date column exists
#             if 'Date' in DATA.columns:
#                 years = DATA['Date'].dt.year.unique()
#                 print("Years in dataset:", sorted(years))
            
#             return True
#         except Exception as e:
#             print(f"Error loading dataset: {e}")
#             return False
#     else:
#         print("Error: CSV file not found at the specified path.")
#         return False

# def dataframe_to_html_table(df):
#     """
#     Convert a pandas DataFrame to a styled HTML table with consistent null handling
#     """
#     if df is None or df.empty:
#         return "<p>No data available</p>"
    
#     try:
#         # Apply standardized formatting (ensure this happens first)
#         df = standardize_output_format(df)  # This ensures consistent null handling
        
#         # Apply styling to the HTML table
#         table_html = df.to_html(
#             index=False, 
#             classes="table table-striped table-hover table-bordered", 
#             border=1,
#             escape=False,
#             na_rep="0"  # Use "0" for numeric NA values rather than "(Uncategorized)"
#         )
        
#         # Add custom styling
#         styled_table = f"""
#         <div class="table-responsive">
#         \n\n\n{table_html}\n\n
#         </div>
#         """
#         return styled_table
#     except Exception as e:
#         print(f"Error creating HTML table: {e}")
#         return f"<p>Error generating table: {str(e)}</p>"



# def check_uncategorized_percentage(df):
#     """
#     Check what percentage of the DataFrame contains uncategorized values
#     Returns the percentage and a boolean indicating if it's too high for visualization
#     """
#     total_cells = df.size
#     uncategorized_count = 0
    
#     for col in df.columns:
#         # Count uncategorized values based on column type
#         if pd.api.types.is_numeric_dtype(df[col]):
#             # For numeric columns, count NaN values (we will replace these with 0)
#             uncategorized_count += df[col].isna().sum()
#         else:
#             # For non-numeric columns, check for various empty/null representations
#             uncategorized_count += df[col].apply(lambda x: 
#                 1 if pd.isna(x) or str(x).lower() in ['nan', 'none', '', 'uncategorized', '(uncategorized)', 'null'] 
#                 else 0).sum()
    
#     percentage = (uncategorized_count / total_cells) * 100 if total_cells > 0 else 0
#     # If more than 30% of data is uncategorized, avoid visualization
#     return percentage, percentage > 30


# # def generate_plotly_chart(df, query):
# #     """
# #     Generate a Plotly chart based on the DataFrame and query content
# #     """
# #     try:
# #         # Check for too many uncategorized values
# #         uncategorized_percentage, too_many_uncategorized = check_uncategorized_percentage(df)
        
# #         if too_many_uncategorized:
# #             return f"""
# #             <div class="alert alert-warning">
# #                 <h4>Visualization Not Recommended</h4>
# #                 <p>The data contains {uncategorized_percentage:.1f}% uncategorized values, which would result in a misleading chart. 
# #                 Please refer to the table for details.</p>
# #             </div>
# #             """

# #         # --- Determine chart type based on keywords ---
# #         query_lower = query.lower()
# #         chart_type = "unknown"

# #         if any(term in query_lower for term in chart_keywords.line_chart_keywords):
# #             chart_type = "line"
# #         elif any(term in query_lower for term in chart_keywords.pie_chart_keywords):
# #             chart_type = "pie"
# #         elif any(term in query_lower for term in chart_keywords.scatter_plot_keywords):
# #             chart_type = "scatter"
# #         elif any(term in query_lower for term in chart_keywords.histogram_keywords):
# #             chart_type = "histogram"
# #         elif any(term in query_lower for term in chart_keywords.bar_chart_keywords):
# #             chart_type = "bar"
# #         else:
# #             # Default to bar for categorical data, line for time series, or bar as general fallback
# #             categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
# #             numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
# #             date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower() or 'year' in col.lower() or 'month' in col.lower()]
            
# #             if date_cols and numeric_cols:
# #                 chart_type = "line"  # Time-series data
# #             elif categorical_cols and numeric_cols:
# #                 chart_type = "bar"   # Categorical data
# #             else:
# #                 chart_type = "bar"   # Default fallback

# #         # --- Identify X and Y columns ---
# #         numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
# #         categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()

# #         if len(df.columns) >= 2:
# #             x_col = categorical_cols[0] if categorical_cols else df.columns[0]
# #             y_col = numeric_cols[0] if numeric_cols else df.columns[1]

# #             # --- Create chart based on type ---
# #             chart_title = f"{chart_type.capitalize()} Chart: {y_col} by {x_col}"
            
# #             if chart_type == "bar":
# #                 fig = px.bar(df, x=x_col, y=y_col, title=chart_title)
# #             elif chart_type == "line":
# #                 fig = px.line(df, x=x_col, y=y_col, title=chart_title)
# #             elif chart_type == "pie":
# #                 fig = px.pie(df, names=x_col, values=y_col, title=chart_title)
# #             elif chart_type == "scatter":
# #                 fig = px.scatter(df, x=x_col, y=y_col, title=chart_title)
# #             elif chart_type == "histogram":
# #                 fig = px.histogram(df, x=y_col, title=f"Histogram of {y_col}")
# #             else:
# #                 return "<p>Could not determine a suitable chart type from the query.</p>"

# #             # --- Update layout ---
# #             fig.update_layout(
# #                 template="plotly_white",
# #                 margin=dict(l=40, r=40, t=40, b=40),
# #                 legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
# #             )

# #             # --- Convert to HTML ---
# #             chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
            
# #             # Add a header to clearly identify the chart type
# #             chart_with_header = f"""
# #             <div class="chart-container">
# #                 <h4>Visualization Type: {chart_type.capitalize()} Chart</h4>
# #                 {chart_html}
# #             </div>
# #             """
# #             return chart_with_header
# #         else:
# #             return "<p>Insufficient data for visualization</p>"
# #     except Exception as e:
# #         print(f"Error generating chart: {e}")
# #         return f"<p>Error generating visualization: {str(e)}</p>"

# def infer_chart_type_from_data(df: pd.DataFrame):
#     """
#     Determine chart type based on actual dataframe content
#     """
#     numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
#     categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()
#     date_cols = [col for col in df.columns if 'date' in col.lower() or 'year' in col.lower() or 'month' in col.lower()]

#     if len(numeric_cols) >= 2:
#         return "scatter"
#     elif date_cols and numeric_cols:
#         return "line"
#     elif categorical_cols and numeric_cols:
#         if df[categorical_cols[0]].nunique() <= 10:
#             return "pie" if len(numeric_cols) == 1 else "bar"
#         else:
#             return "bar"
#     elif len(numeric_cols) == 1:
#         return "histogram"
#     return "bar"  # Fallback

# def generate_plotly_chart(df, query):
#     try:
#         uncategorized_percentage, too_many_uncategorized = check_uncategorized_percentage(df)
#         if too_many_uncategorized:
#             return f"""
#             <div class=\"alert alert-warning\">
#                 <h4>Visualization Not Recommended</h4>
#                 <p>The data contains {uncategorized_percentage:.1f}% uncategorized values, which would result in a misleading chart. 
#                 Please refer to the table for details.</p>
#             </div>
#             """

#         # Step 1: Data-driven inference
#         chart_type = infer_chart_type_from_data(df)

#         # Step 2: Override if keywords are highly specific
#         query_lower = query.lower()
#         if any(term in query_lower for term in chart_keywords.line_chart_keywords):
#             chart_type = "line"
#         elif any(term in query_lower for term in chart_keywords.pie_chart_keywords):
#             chart_type = "pie"
#         elif any(term in query_lower for term in chart_keywords.scatter_chart_keywords):
#             chart_type = "scatter"
#         elif any(term in query_lower for term in chart_keywords.histogram_chart_keywords):
#             chart_type = "histogram"
#         elif any(term in query_lower for term in chart_keywords.bar_chart_keywords):
#             chart_type = "bar"

#         # --- X and Y axis detection ---
#         numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
#         categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()
#         date_cols = [col for col in df.columns if col.lower() in ['date', 'year', 'month', 'quarter', 'week', 'time']]

#         x_col = None
#         y_col = None

#         if date_cols:
#             x_col = date_cols[0]
#             cost_cols = [col for col in numeric_cols if any(term in col.lower() for term in ['cost', 'amount', 'price', 'value', 'sales'])]
#             if cost_cols:
#                 y_col = cost_cols[0]
#             elif numeric_cols:
#                 y_col = numeric_cols[0]

#         if not x_col or not y_col:
#             year_col = next((col for col in df.columns if col.lower() == 'year'), None)
#             month_col = next((col for col in df.columns if col.lower() == 'month'), None)

#             if year_col and month_col:
#                 try:
#                     df['Date'] = pd.to_datetime(df[year_col].astype(str) + '-' + df[month_col].astype(str), format='%Y-%m')
#                     x_col = 'Date'
#                 except:
#                     x_col = year_col

#             if not x_col:
#                 for col in categorical_cols:
#                     if df[col].nunique() <= 30:
#                         x_col = col
#                         break
#                 if not x_col:
#                     x_col = df.columns[0]

#             if not y_col and numeric_cols:
#                 value_cols = [col for col in numeric_cols if any(term in col.lower() for term in ['cost', 'amount', 'price', 'value', 'sales', 'revenue', 'profit'])]
#                 if value_cols:
#                     y_col = value_cols[0]
#                 else:
#                     y_col = max(numeric_cols, key=lambda col: df[col].var() if not pd.isna(df[col].var()) else 0)

#         if not x_col:
#             x_col = df.columns[0]
#         if not y_col:
#             df['Count'] = 1
#             y_col = 'Count'

#         if chart_type == "pie" and df[x_col].nunique() > 20:
#             return "<p>Too many categories for pie chart. Try using a bar chart instead.</p>"

#         chart_title = f"{y_col} by {x_col}"

#         if chart_type == "bar":
#             fig = px.bar(df, x=x_col, y=y_col, title=chart_title)
#             if x_col in date_cols:
#                 fig.update_xaxes(tickangle=45)

#         elif chart_type == "line":
#             try:
#                 if not pd.api.types.is_datetime64_any_dtype(df[x_col]):
#                     df[x_col] = pd.to_datetime(df[x_col], errors='coerce')
#                 df = df.sort_values(by=x_col)
#             except:
#                 pass
#             fig = px.line(df, x=x_col, y=y_col, title=chart_title)
#             fig.update_traces(mode='lines+markers')

#         elif chart_type == "pie":
#             if df[x_col].nunique() > 10:
#                 top_values = df.groupby(x_col)[y_col].sum().nlargest(10).index.tolist()
#                 df_pie = df[df[x_col].isin(top_values)].copy()
#                 if len(df_pie) < len(df):
#                     other_sum = df[~df[x_col].isin(top_values)][y_col].sum()
#                     other_row = pd.DataFrame({x_col: ['Other'], y_col: [other_sum]})
#                     df_pie = pd.concat([df_pie, other_row])
#                 fig = px.pie(df_pie, names=x_col, values=y_col, title=f"Distribution of {y_col} by {x_col}")
#             else:
#                 fig = px.pie(df, names=x_col, values=y_col, title=f"Distribution of {y_col} by {x_col}")

#         elif chart_type == "scatter":
#             fig = px.scatter(df, x=x_col, y=y_col, title=chart_title)
#             fig.update_traces(marker=dict(size=8))

#         elif chart_type == "histogram":
#             fig = px.histogram(df, x=y_col, title=f"Distribution of {y_col}")
#             fig.update_traces(marker_line_width=1, marker_line_color="white")

#         else:
#             return "<p>Could not determine a suitable chart type from the query.</p>"

#         fig.update_layout(
#             template="plotly_white",
#             margin=dict(l=40, r=40, t=60, b=60),
#             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
#             xaxis_title=x_col,
#             yaxis_title=y_col
#         )

#         if x_col in date_cols or any(word in x_col.lower() for word in ['date', 'year', 'month']):
#             fig.update_xaxes(tickangle=45)

#         if y_col in numeric_cols:
#             fig.update_yaxes(tickformat=",.0f")

#         chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
#         chart_with_header = f"""
#         <div class=\"chart-container\">
#             <h4>Visualization Type: {chart_type.capitalize()} Chart</h4>
#             {chart_html}
#         </div>
#         """
#         return chart_with_header

#     except Exception as e:
#         print(f"Error generating chart: {e}")
#         return f"<p>Error generating visualization: {str(e)}</p>"



# # def generate_plotly_chart(df, query):
# #     """
# #     Generate a Plotly chart based on the DataFrame and query content with improved axis detection
# #     """
# #     try:
# #         # Check for too many uncategorized values
# #         uncategorized_percentage, too_many_uncategorized = check_uncategorized_percentage(df)
        
# #         if too_many_uncategorized:
# #             return f"""
# #             <div class="alert alert-warning">
# #                 <h4>Visualization Not Recommended</h4>
# #                 <p>The data contains {uncategorized_percentage:.1f}% uncategorized values, which would result in a misleading chart. 
# #                 Please refer to the table for details.</p>
# #             </div>
# #             """

# #         # --- Determine chart type based on keywords ---
# #         query_lower = query.lower()
# #         chart_type = "unknown"
        
# #         # Improved chart type detection
# #         if any(term in query_lower for term in chart_keywords.line_chart_keywords) or "trend" in query_lower:
# #             chart_type = "line"
# #         elif any(term in query_lower for term in chart_keywords.pie_chart_keywords):
# #             chart_type = "pie"
# #         elif any(term in query_lower for term in chart_keywords.scatter_plot_keywords):
# #             chart_type = "scatter"
# #         elif any(term in query_lower for term in chart_keywords.histogram_keywords):
# #             chart_type = "histogram"
# #         elif any(term in query_lower for term in chart_keywords.bar_chart_keywords):
# #             chart_type = "bar"
# #         else:
# #             # Better default chart type detection
# #             # Check for time series data first
# #             date_cols = [col for col in df.columns if col.lower() in ['date', 'year', 'month', 'quarter', 'week', 'time']]
# #             numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
# #             if date_cols and numeric_cols:
# #                 chart_type = "line"  # Time-series data
# #             elif len(df) <= 10:  # For small datasets with few rows
# #                 chart_type = "bar"
# #             else:
# #                 # More intelligent determination based on data cardinality
# #                 categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
# #                 if categorical_cols and any(df[col].nunique() <= 10 for col in categorical_cols):
# #                     chart_type = "bar"  # Categorical with few unique values
# #                 else:
# #                     chart_type = "line"  # Default to line for most other cases

# #         # --- Improved X and Y axis detection ---
# #         numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
# #         # Special handling for time series data
# #         date_cols = [col for col in df.columns if col.lower() in ['date', 'year', 'month', 'quarter', 'week', 'time']]
# #         time_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower() or 'year' in col.lower() or 'month' in col.lower()]
        
# #         # Try to identify the most meaningful columns for x and y
# #         x_col = None
# #         y_col = None
        
# #         # For time series, prioritize date/time columns for x-axis
# #         if date_cols:
# #             x_col = date_cols[0]
            
# #             # If there's a column with 'cost' or 'amount' for time series, use that for y
# #             cost_cols = [col for col in numeric_cols if any(term in col.lower() for term in ['cost', 'amount', 'price', 'value', 'sales'])]
# #             if cost_cols:
# #                 y_col = cost_cols[0]
# #             elif numeric_cols:
# #                 y_col = numeric_cols[0]  # Default to first numeric column
        
# #         # If we still don't have x and y, use heuristics
# #         if not x_col or not y_col:
# #             # If we have year/month columns, try to use them properly
# #             year_col = next((col for col in df.columns if col.lower() == 'year'), None)
# #             month_col = next((col for col in df.columns if col.lower() == 'month'), None)
            
# #             if year_col and month_col:
# #                 # Create a combined date column for proper time series
# #                 try:
# #                     df['Date'] = pd.to_datetime(df[year_col].astype(str) + '-' + df[month_col].astype(str), format='%Y-%m')
# #                     x_col = 'Date'
# #                 except:
# #                     x_col = year_col  # Fallback to just year
            
# #             # If still no x_col, use the first non-numeric column with low cardinality
# #             if not x_col:
# #                 categorical_cols = [col for col in df.columns if col not in numeric_cols]
# #                 if categorical_cols:
# #                     # Select categorical column with reasonable cardinality
# #                     for col in categorical_cols:
# #                         if df[col].nunique() <= 30:  # Not too many unique values
# #                             x_col = col
# #                             break
                    
# #                     # If no suitable categorical column found, use first column
# #                     if not x_col:
# #                         x_col = df.columns[0]
            
# #             # For y-axis, if not already determined, use most interesting numeric column
# #             if not y_col and numeric_cols:
# #                 # Prefer columns with 'cost', 'amount', etc.
# #                 value_cols = [col for col in numeric_cols if any(term in col.lower() for term in 
# #                                                               ['cost', 'amount', 'price', 'value', 'sales', 'revenue', 'profit'])]
# #                 if value_cols:
# #                     y_col = value_cols[0]
# #                 else:
# #                     # Use column with highest variance (likely most informative)
# #                     y_col = max(numeric_cols, key=lambda col: df[col].var() if not pd.isna(df[col].var()) else 0)
        
# #         # Fallback to default columns if we somehow still don't have x and y
# #         if not x_col:
# #             x_col = df.columns[0]
# #         if not y_col and len(df.columns) >= 2:
# #             if df.columns[0] == x_col:
# #                 y_col = df.columns[1]
# #             else:
# #                 y_col = df.columns[0]
# #         elif not y_col:
# #             # Emergency fallback - create a count column
# #             df['Count'] = 1
# #             y_col = 'Count'

# #         # --- Create chart based on type ---
# #         chart_title = f"{y_col} by {x_col}"
        
# #         # Handle special cases for chart creation
# #         if chart_type == "bar":
# #             fig = px.bar(df, x=x_col, y=y_col, title=chart_title)
# #             # For date x-axis with bars, we might want to format x-axis 
# #             if x_col in date_cols:
# #                 fig.update_xaxes(tickangle=45)
                
# #         elif chart_type == "line":
# #             # For date columns, ensure proper sorting
# #             if x_col in date_cols or x_col in time_cols:
# #                 try:
# #                     # Try to convert to datetime for proper sorting
# #                     if not pd.api.types.is_datetime64_any_dtype(df[x_col]):
# #                         df[x_col] = pd.to_datetime(df[x_col], errors='coerce')
# #                     # Sort by date
# #                     df = df.sort_values(by=x_col)
# #                 except:
# #                     # If date conversion fails, just use as is
# #                     pass
                    
# #             fig = px.line(df, x=x_col, y=y_col, title=chart_title)
# #             # Add markers to line chart for better readability
# #             fig.update_traces(mode='lines+markers')
            
# #         elif chart_type == "pie":
# #             # For pie charts, limit to top 10 categories if needed
# #             if df[x_col].nunique() > 10:
# #                 top_values = df.groupby(x_col)[y_col].sum().nlargest(10).index.tolist()
# #                 df_pie = df[df[x_col].isin(top_values)].copy()
# #                 # Add an "Other" category
# #                 if len(df_pie) < len(df):
# #                     other_sum = df[~df[x_col].isin(top_values)][y_col].sum()
# #                     other_row = pd.DataFrame({x_col: ['Other'], y_col: [other_sum]})
# #                     df_pie = pd.concat([df_pie, other_row])
# #                 fig = px.pie(df_pie, names=x_col, values=y_col, title=f"Distribution of {y_col} by {x_col}")
# #             else:
# #                 fig = px.pie(df, names=x_col, values=y_col, title=f"Distribution of {y_col} by {x_col}")
                
# #         elif chart_type == "scatter":
# #             fig = px.scatter(df, x=x_col, y=y_col, title=chart_title)
# #             # Add trendline
# #             fig.update_traces(marker=dict(size=8))
            
# #         elif chart_type == "histogram":
# #             fig = px.histogram(df, x=y_col, title=f"Distribution of {y_col}")
# #             fig.update_traces(marker_line_width=1, marker_line_color="white")
        
# #         else:
# #             return "<p>Could not determine a suitable chart type from the query.</p>"

# #         # --- Update layout with better defaults ---
# #         fig.update_layout(
# #             template="plotly_white",
# #             margin=dict(l=40, r=40, t=60, b=60),  # Increased margins
# #             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
# #             xaxis_title=x_col,
# #             yaxis_title=y_col
# #         )
        
# #         # Handle special case for dates - rotate labels
# #         if x_col in date_cols or any(word in x_col.lower() for word in ['date', 'year', 'month']):
# #             fig.update_xaxes(tickangle=45)
        
# #         # Format y-axis for numeric values - human readable (e.g., 1K instead of 1000)
# #         if y_col in numeric_cols:
# #             fig.update_yaxes(tickformat=",.0f")

# #         # --- Convert to HTML ---
# #         chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        
# #         # Add a header to clearly identify the chart type
# #         chart_with_header = f"""
# #         <div class="chart-container">
# #             <h4>Visualization Type: {chart_type.capitalize()} Chart</h4>
# #             {chart_html}
# #         </div>
# #         """
# #         return chart_with_header
# #     except Exception as e:
# #         print(f"Error generating chart: {e}")
# #         return f"<p>Error generating visualization: {str(e)}</p>"


# def generate_time_series_chart(df, time_col, value_col, title=None):
#     """
#     Generate a time series chart with proper date handling
#     """
#     try:
#         # Convert time column to datetime if not already
#         if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
#             # Handle year+month combination
#             if time_col.lower() == 'year' and 'month' in df.columns:
#                 try:
#                     # Create a proper date column
#                     df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str), format='%Y-%m')
#                     time_col = 'Date'
#                 except:
#                     # Try to convert as is
#                     df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
#             else:
#                 # Standard date conversion
#                 df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        
#         # Sort by date for line chart
#         df_sorted = df.sort_values(by=time_col)
        
#         # Create chart title if not provided
#         if not title:
#             title = f"{value_col} over Time"
            
#         # Create line chart
#         fig = px.line(df_sorted, x=time_col, y=value_col, title=title)
        
#         # Add markers for data points
#         fig.update_traces(mode='lines+markers', marker=dict(size=8))
        
#         # Format axes
#         fig.update_xaxes(
#             title_text="Time Period",
#             tickangle=45,
#             tickformat="%b %Y" if 'Date' in df.columns else None
#         )
        
#         fig.update_yaxes(
#             title_text=value_col,
#             tickformat=",.0f"  # Format large numbers with commas
#         )
        
#         # Enhanced layout
#         fig.update_layout(
#             template="plotly_white",
#             margin=dict(l=40, r=40, t=60, b=60),
#             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
#         )
        
#         # Add a trend line
#         try:
#             if len(df_sorted) >= 3:  # Need at least 3 points for a meaningful trendline
#                 fig.add_traces(
#                     px.scatter(df_sorted, x=time_col, y=value_col, trendline="ols").data[1]
#                 )
#         except:
#             pass  # Skip trendline if error
            
#         # Return HTML
#         chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        
#         return chart_html
        
#     except Exception as e:
#         print(f"Error generating time series chart: {e}")
#         return f"<p>Error generating time series visualization: {str(e)}</p>"

# def extract_dataframe_from_text(text):
#     """
#     Attempt to extract table-like data from text response and convert to DataFrame
#     """
#     try:
#         # Check if the response contains structured table data
#         if '|' in text and '\n' in text:
#             # Try to parse markdown table
#             lines = [line.strip() for line in text.split('\n') if line.strip()]
#             # Find table boundaries
#             start_idx = None
#             end_idx = None
            
#             for i, line in enumerate(lines):
#                 if '|' in line:
#                     if start_idx is None:
#                         start_idx = i
#                     end_idx = i
            
#             if start_idx is not None and end_idx is not None:
#                 table_lines = lines[start_idx:end_idx+1]
#                 # Remove markdown table formatting lines (those with dashes)
#                 table_lines = [line for line in table_lines if not line.replace('|', '').strip().startswith('---')]
                
#                 # Parse headers and data
#                 headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
#                 data = []
                
#                 for line in table_lines[1:]:
#                     row_data = [cell.strip() for cell in line.split('|') if cell.strip()]
#                     if row_data:
#                         data.append(row_data)
                
#                 # Create DataFrame
#                 if headers and data:
#                     # Make sure data rows have the same length as headers
#                     data = [row for row in data if len(row) == len(headers)]
#                     df = pd.DataFrame(data, columns=headers)
#                     return df
        
#         # If basic parsing failed, try more aggressive methods
#         import re
        
#         # Look for table patterns in the text
#         table_pattern = r'\b(\w+)\s*\|\s*([\w\s\.]+)\s*\|\s*([\w\s\.]+)'
#         matches = re.findall(table_pattern, text)
        
#         if matches:
#             # Try to determine the number of columns
#             col_count = len(matches[0])
#             headers = ["Column" + str(i+1) for i in range(col_count)]
#             df = pd.DataFrame(matches, columns=headers)
#             return df
        
#         return None
#     except Exception as e:
#         print(f"Error extracting DataFrame: {e}")
#         return None

# def combine_chart_and_table(chart_html, table_html, title="Data Analysis Results"):
#     """
#     Combine chart and table into a single HTML page
#     """
#     combined_html = f"""
#     <div class="analysis-container">
#         <h2>{title}</h2>
#         <div class="chart-container">
#             <h3>Visualization</h3>
#             {chart_html}
#         </div>
#         <div class="table-container">
#             <h3>Data Table</h3>
#             {table_html}
#         </div>
#     </div>
#     """
#     return combined_html

# # Call load_data during startup
# load_data()

# # Create routers for each group
# auth_router = APIRouter(tags=["Auth"])
# data_router = APIRouter(tags=["data-analysis"])

# # Authentication Endpoints
# @auth_router.post("/login", response_model=Token)
# async def login(form_data: OAuth2PasswordRequestForm = Depends()):
#     user = authenticate_user(form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token = create_access_token({"sub": user["username"], "role": user["role"]})
#     return {"access_token": access_token, "token_type": "bearer"}

# @auth_router.get("/me")
# async def read_current_user(current_user: dict = Depends(get_current_user)):
#     return current_user

# @auth_router.post("/register", response_model=User)
# async def register(user: User):
#     for existing_user in dummy_users:
#         if existing_user["username"] == user.username:
#             raise HTTPException(status_code=400, detail="Username already exists")
#     new_user = {"username": user.username, "password": user.password, "role": user.role}
#     dummy_users.append(new_user)
#     return new_user

# @auth_router.post("/logout")
# async def logout():
#     return {"message": "Logout successful. Remove token on frontend."}


# def standardize_output_format(df):
#     """
#     Standardize DataFrame output formatting with consistent null handling
#     """
#     # Create a deep copy to avoid modifying the original
#     formatted_df = df.copy()
    
#     # Ensure consistent handling of null/NA values
#     for col in formatted_df.columns:
#         # Check if the column is numeric
#         is_numeric = pd.api.types.is_numeric_dtype(formatted_df[col])
        
#         if is_numeric:
#             # For numeric columns, replace nulls with 0 (not -1)
#             formatted_df[col] = formatted_df[col].fillna(0)
#         else:
#             # For non-numeric columns, replace nulls with "(Uncategorized)"
#             formatted_df[col] = formatted_df[col].fillna("(Uncategorized)")
#             # Convert objects like pandas NA to string "(Uncategorized)"
#             formatted_df[col] = formatted_df[col].astype(str)
#             formatted_df[col] = formatted_df[col].replace(['nan', 'None', '', 'NaN', 'null', '<NA>'], '(Uncategorized)')
    
#     return formatted_df

# # Add this function to check if the response is a list
# def is_list_response(text):
#     """
#     Determine if the response appears to be a list of items rather than tabular data
#     """
#     # Check for common list indicators
#     list_indicators = [
#         text.count("\n1.") > 0,  # Numbered list starting with 1.
#         text.count("\n- ") > 1,  # Bullet points with dashes
#         text.count("\n* ") > 1,  # Bullet points with asterisks
#         text.count("\n•") > 1,   # Bullet points with bullet character
#         bool(re.search(r'\n\d+\.\s+', text)),  # Any numbered list
#         bool(re.search(r'Top \d+ ', text)) and text.count("\n") > 2,  # Contains "Top N" and multiple lines
#         bool(re.search(r'(\n\s*([A-Za-z0-9][\)\.:]|\d+[\)\.:])\s+)', text))  # Formatted list with parentheses or periods
#     ]
    
#     # Look for "Top N" or "N questions" type patterns in the query
#     list_keywords = [
#         'list', 'top', 'questions', 'reasons', 'factors', 'steps',
#         'best', 'worst', 'highest', 'lowest', 'most common',
#         'frequently', 'commonly', 'popular', 'tips', 'advice', 'suggestions'
#     ]
    
#     contains_list_keywords = any(keyword in text.lower() for keyword in list_keywords)
    
#     # If we have at least one list indicator or contains list keywords and has multiple lines
#     return any(list_indicators) or (contains_list_keywords and text.count("\n") > 2)

# # Also update the query_data function to handle lists better
# @data_router.post("/query/")
# async def query_data(request: QueryRequest, current_user: dict = Depends(get_current_user)):
#     global DATA, CHAT_HISTORY
#     if DATA is None:
#         # Attempt to reload data if not already loaded
#         if not load_data():
#             raise HTTPException(status_code=400, detail="No data loaded.")
    
#     query = request.query
    
#     # Special case for greetings or simple queries
#     # greeting_keywords = ["hi", "hello", "hey", "greetings", "howdy", "good morning", "good afternoon", "good evening"]
    
#     # if query.lower() in greeting_keywords or len(query.split()) <= 1:
#     #     greeting_response = f"Hello {current_user['username']}! I'm your data analysis assistant. You can ask me questions about your warranty data, such as 'What are the top problem codes by cost?' or 'Show me warranty trends by business unit'. How can I help you analyze your data today?"
        
#     #     # Store in chat history
#     #     CHAT_HISTORY.append({
#     #         "query": query,
#     #         "response": greeting_response,
#     #         "user": current_user["username"]
#     #     })
        
#     #     # Trim if needed
#     #     if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#     #         CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
        
#     #     return {
#     #         "response": greeting_response
#     #     }
    
#     # Check if this is likely a request for a list
#     is_list_request = any(keyword in query.lower() for keyword in [
#         'list', 'top', 'questions', 'reasons', 'factors', 'steps',
#         'best', 'worst', 'highest', 'lowest', 'most common',
#         'frequently', 'commonly', 'popular', 'tips', 'advice', 'suggestions'
#     ])
    
#     # Check if this is a time comparison request (YoY/MoM)
#     is_time_comparison = any(term in query.lower() for term in [
#         'yoy', 'mom', 'year over year', 'month over month', 'yearly', 'monthly',
#         'compared to last', 'previous year', 'previous month', 'comparison',
#         'trend', 'performance over time', 'change since', 'growth'
#     ])
    
#     # Log the user making the query
#     print(f"Query received from user: {current_user['username']} with role: {current_user['role']}")
#     print(f"Is this likely a list request? {is_list_request}")
#     print(f"Is this likely a time comparison? {is_time_comparison}")

#     if not OPENAI_API_KEY:
#         raise HTTPException(status_code=500, detail="OpenAI API key is missing")

#     final_result = ""
#     html_table = ""
#     final_result1 = ""
#     # Helper function to ensure text summaries
#     def ensure_text_summary(response_text, result_df, query, is_time_comparison=False):
#         """Ensures that a proper text summary exists without table formatting"""
        
#         # Check if there's already a text summary in the response
#         lines = response_text.strip().split('\n')
        
#         # Extract only the text part before any table formatting
#         summary_lines = []
#         for line in lines:
#             if '|' in line and '-' in line:  # We've reached the table
#                 break
#             if not line.strip().startswith('|'):  # Skip any table lines
#                 summary_lines.append(line)
        
#         summary_text = '\n'.join(summary_lines).strip()
        
#         # If we don't have a summary and we have a dataframe, generate one
#         if (not summary_text or len(summary_text) < 40) and result_df is not None and not result_df.empty:
#             try:
#                 # Find time columns if they exist
#                 time_cols = [col for col in result_df.columns if col.lower() in [
#                     'year', 'month', 'date', 'period', 'quarter', 'time', 'week'
#                 ]]
                
#                 # Create a basic summary
#                 summary_parts = []
                
#                 # If this is a time comparison and we have time columns
#                 if is_time_comparison and time_cols:
#                     time_col = time_cols[0]  # Use the first identified time column
                    
#                     # Get unique time periods
#                     time_periods = sorted(result_df[time_col].unique())
                    
#                     if len(time_periods) >= 2:
#                         # Find numeric columns for analysis (exclude percentage columns)
#                         numeric_cols = [col for col in result_df.columns 
#                                       if col not in time_cols and 
#                                       col.lower() not in ['difference in %', '% change', 'percent', 'percentage'] and
#                                       pd.api.types.is_numeric_dtype(result_df[col])]
                        
#                         # For each numeric column, check the changes
#                         for col in numeric_cols[:3]:  # Limit to top 3 columns
#                             try:
#                                 # For simple two-period comparison
#                                 if len(time_periods) == 2:
#                                     val1 = result_df[result_df[time_col] == time_periods[0]][col].iloc[0]
#                                     val2 = result_df[result_df[time_col] == time_periods[1]][col].iloc[0]
                                    
#                                     if val1 != 0:
#                                         pct_change = ((val2 - val1) / val1) * 100
#                                         direction = "increased" if pct_change > 0 else "decreased"
#                                         summary_parts.append(f"{col} {direction} by {abs(pct_change):.1f}% from {time_periods[0]} to {time_periods[1]}")
#                             except:
#                                 continue
                
#                 # If we couldn't generate specific time comparisons, create a generic summary
#                 if not summary_parts:
#                     # Get column with largest values
#                     try:
#                         numeric_cols = [col for col in result_df.columns 
#                                        if pd.api.types.is_numeric_dtype(result_df[col])]
                        
#                         if numeric_cols:
#                             max_col = max(numeric_cols, key=lambda col: result_df[max_col].max())
#                             max_row_idx = result_df[max_col].idxmax()
#                             max_row = result_df.iloc[max_row_idx]
                            
#                             # Create a summary for this finding
#                             max_value = max_row[max_col]
#                             id_col = next((col for col in result_df.columns 
#                                           if col.lower() in ['name', 'id', 'category', 'type', 'description']), 
#                                           result_df.columns[0])
                            
#                             id_value = max_row[id_col]
#                             summary_parts.append(f"The highest {max_col} is {max_value:,.2f} for {id_value}.")
#                     except:
#                         pass
                
#                 # If we have summary parts, create the summary
#                 if summary_parts:
#                     if len(summary_parts) > 1:
#                         summary = f"{summary_parts[0]} {summary_parts[1]}"
#                     else:
#                         summary = summary_parts[0]
                        
#                     # Add information about the dataset
#                     summary += f" This analysis is based on {len(result_df)} data points."
#                 else:
#                     # Create a generic summary
#                     summary = f"Analysis of {query} based on {len(result_df)} data points. "
                    
#                     # For time comparisons, add more context about the periods
#                     if is_time_comparison and time_cols:
#                         time_col = time_cols[0]
#                         time_periods = sorted(result_df[time_col].unique())
#                         if len(time_periods) >= 2:
#                             summary += f"Comparing {time_periods[0]} to {time_periods[-1]}, "
                    
#                     # Add basic info about what's in the data
#                     if len(result_df.columns) > 1:
#                         main_cols = [col for col in result_df.columns if col not in ['% Change_Cost', '% Change_Units']][:3]
#                         summary += f"The data shows values for {', '.join(main_cols)}."
                
#                 return summary
                    
#             except Exception as e:
#                 print(f"Error generating summary: {e}")
        
#         return summary_text if summary_text else "Analysis of the requested data:"

#     try:
#         # Use latest OpenAI model with enhanced capabilities
#         agent = create_pandas_dataframe_agent(
#             get_cached_llm(),
#             DATA,
#             verbose=True,
#             agent_type=AgentType.OPENAI_FUNCTIONS,
#             allow_dangerous_code=True
#         )


#             # print("AGENT OUTPUT: \n"+  agent + "\n")
        
#         # Enhanced chat2plot with more robust plotting
#         c2p = chat2plot(
#             DATA, 
#             language="English", 
#             chat=ChatOpenAI(
#                 model="gpt-4o-mini", 
#                 api_key=OPENAI_API_KEY
#             )
#         )
        
#         # Prepare context from chat history
#         context = "\n".join([f"Previous User Query: {entry['query']}\nPrevious Bot Response: {entry['response']}" for entry in CHAT_HISTORY[-MAX_HISTORY_LENGTH:]])
        
      
#         # Customize the query format based on the request type
#         if is_list_request:
#             query_format = "Your response should be formatted as a concise numbered list preceded by a brief introduction, NOT as a table."
#         elif is_time_comparison:
#             query_format = "This is a time comparison query. Begin with a 2-4 sentence text summary highlighting the key changes, THEN show a properly formatted markdown table with a percentage change column."
#         else:
#             query_format = "If showing complex data, include a 2-4 sentence description followed by a properly formatted markdown table with proper header and separator rows."
        
#         refined_query = f"""Considering previous conversation context:
# {context}

# Important formatting instructions: {instructions.formatting_instruction}
# Format note: {query_format}

# New Query: {query}

# Remember: For tables, ALWAYS START with a 2-4 sentence text summary BEFORE the table explaining key findings.
# For time-based comparisons (YoY, MoM), ALWAYS include percentage changes with + or - prefixes.
# For lists of items (like "top N" questions), use a simple numbered list format, not a table.
# For tabular data, use proper markdown table format with | separators, header row, and separator row with dashes.
# """
        
#         # Check if it's a visualization request
#         is_visualization_request = any(term in query.lower() for term in [
#             'chart', 'plot', 'graph', 'visualize', 'show', 'display', 'visualisation', 
#             'pie', 'bar', 'line', 'scatter', 'histogram', 'trend'
#         ])
        
#         # For visualization requests, use Plotly
#         if is_visualization_request:
            
#             try:
#                 # First get data for visualization
#                 data_query = f"Based on this query: '{query}', provide the data needed for visualization as a pandas DataFrame with clear column names. Format your response to include only the necessary data in a well-structured markdown table format with proper header and separator rows."
                
#                 data_res = agent.invoke(data_query)
#                 data_text = (
#                     data_res.get("output") if isinstance(data_res, dict) else 
#                     str(data_res) if data_res else 
#                     "Could not find data for visualization."
#                 )
                
#                 # Extract DataFrame from the text response
#                 visualization_df = extract_dataframe_from_text(data_text)
                
#                 if visualization_df is None or visualization_df.empty:
#                     # If extraction failed, run a more direct query
#                     direct_query = f"For the query '{query}', return a pandas DataFrame with at most 20 rows that would be suitable for visualization. Format your response to show just the table of data with proper markdown table formatting."
                    
#                     direct_res = agent.invoke(direct_query)
#                     direct_text = (
#                         direct_res.get("output") if isinstance(direct_res, dict) else 
#                         str(direct_res) if direct_res else 
#                         "Could not find data for visualization."
#                     )
                    
#                     visualization_df = extract_dataframe_from_text(direct_text)
                
#                 # If we now have a DataFrame, generate visualization
#                 if visualization_df is not None and not visualization_df.empty:
#                     # Standardize the output format
#                     visualization_df = standardize_output_format(visualization_df)
                    
#                     # Create a text summary for the visualization
#                     summary_query = f"""Based on this data:
# {visualization_df.to_string(index=False)}

# Generate a 2-3 sentence summary highlighting:
# 1. The most significant patterns or findings
# 2. Any notable outliers or special cases
# 3. The key insight this visualization will demonstrate

# Format as plain text paragraph only, no tables."""

#                     summary_res = agent.invoke(summary_query)
#                     summary_text = (
#                         summary_res.get("output") if isinstance(summary_res, dict) else 
#                         str(summary_res) if summary_res else 
#                         "Visualization of query results."
#                     )
                    
#                     # Print the exact same DataFrame to terminal for consistency
#                     print("\nVisualization DataFrame (Terminal Output):")
#                     print(visualization_df.to_string(index=False))
                    
#                     # Generate chart HTML
#                     chart_html = generate_plotly_chart(visualization_df, query)
                    
#                     # Generate table HTML
#                     table_html = dataframe_to_html_table(visualization_df)
                    
#                     # Combine into a single HTML response with summary
#                     combined_html = combine_chart_and_table(chart_html, table_html, f"{summary_text}")
                    
#                     # Store chat history
#                     CHAT_HISTORY.append({
#                         "query": query,
#                         "response": f"{summary_text}",  # Only store the summary
#                         "user": current_user["username"]
#                     })
                    
#                     # Trim chat history if it exceeds max length
#                     if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#                         CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
                    
#                     print("HTML Content : ", table_html)

#                     return {
#                         "response": f"{summary_text}",  # Only return the summary
#                         "html_content": combined_html,
#                         "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
#                     }
#                 else:
#                     # Fallback to traditional response
#                     print("Could not extract DataFrame for visualization, falling back to text response")
#             except Exception as viz_error:
#                 print(f"Visualization error: {viz_error}")
#                 # Continue with text-based response as fallback
        
#         # Process the analytical query
#         res = agent.invoke(refined_query)
        
#         # Extract response with multiple fallback mechanisms
#         response_text = (
#             res.get("output") if isinstance(res, dict) else 
#             str(res) if res else 
#             "Could not find a definitive answer to your question."
#         )
        
#         # Enhanced post-processing to ensure proper markdown table formatting
#         response_text = response_text.replace(" (blank)", " (Uncategorized)")
#         response_text = response_text.replace(" (null)", " (Uncategorized)")
#         response_text = response_text.replace(" (empty)", " (Uncategorized)")
#         response_text = response_text.replace("Blank: ", "(Uncategorized): ")
#         response_text = response_text.replace("Empty: ", "(Uncategorized): ")
#         response_text = response_text.replace("Null: ", "(Uncategorized): ")
#         response_text = response_text.replace("NA: ", "(Uncategorized): ")
#         response_text = response_text.replace("<NA>", "(Uncategorized)")
        
#         # Debug output to see what was received
#         #print(f"\nRaw response text:\n{response_text[:500]}...")
        
#         # Check if the response appears to be a list rather than tabular data
#         is_list_response_result = is_list_response(response_text)
#         #print(f"Is list response: {is_list_response_result}")
        
#         # First check if there's a table in the response
#         has_table = '|' in response_text and '\n' in response_text and '-' in response_text
#         #print(f"Has table markers: {has_table}")
        
#         # Check if the response is short
#         is_short_response = len(response_text.split('\n')) < 3 and len(response_text) < 300 and not has_table
        
#         # Always attempt to extract DataFrame even if it looks like a list
#         result_df = None
#         if not is_short_response:
#             # Try to extract DataFrame - this uses our improved function
#             result_df = extract_dataframe_from_text(response_text)
#             #raw_text = remove_newlines_replace(response_text)
            
         

#             # Debug output
#             if result_df is not None:
#                 print(f"Successfully extracted DataFrame with shape: {result_df.shape}")
#             else:
#                 print("Failed to extract DataFrame")
        
#         # If we found a DataFrame, format it as HTML table
#         if result_df is not None and not result_df.empty:
#             # Standardize the output format
#             result_df = standardize_output_format(result_df)
            
#             # Print the exact same DataFrame to terminal for consistency
#             #print("\nResult DataFrame (Terminal Output):")
#             print(result_df.to_string(index=False))
            
#             # Get just the text summary without table formatting
#             text_summary = ensure_text_summary(response_text, result_df, query, is_time_comparison)
            
#             # Use our improved HTML table function
#             html_table = dataframe_to_html_table(result_df)
#             # chart_html = generate_plotly_chart(result_df, query)
#             chart_html = generate_plotly_chart(result_df, response_text)
#             final_table = remove_newlines_replace(html_table)
#             # chart_htm = generate_plotly_chart(result_df, response_text)
#             final_result = replace_between_pipe_and_I(response_text,"\n" + final_table + "\n")
#             #final_result = replace_between_pipe_and_I(final_result1,"\n" + chart_html  + "\n")
#             # final_result = final_result + "\n" + chart_html
            

#             # print("\n\nfinal_result1: ", final_result1)
#             # print("\n\nfinal_result: ", final_result)
#             print("\n\nchart_html: ",chart_html)

#             # print("\nHTML chart content: ", chart_html)
#             # print("\ntext_summary: ", text_summary)
#             # print("\nhtml_table: ", html_table)
#             # print("\nfinal_table: ", final_table)
            
#             # Store chat history with user information - using just the text summary
#             CHAT_HISTORY.append({
#                 "query": query,
#                 "response": text_summary,
#                 "user": current_user["username"]
#             })
            
#             # Trim chat history if it exceeds max length
#             if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#                 CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            
#             # Only return the summary text in the response
#             return {
#                     "response": final_result,
#                     "chart_html": chart_html # Only include the summary text
#                    }
#         else:
#             # Force a fallback attempt for responses that contain pipe characters but weren't properly parsed
#             if has_table and '|' in response_text:
#                 print("Attempting fallback table parsing for response with pipe characters")
                
#                 # Clean up the text to make it more parseable
#                 cleaned_text = re.sub(r'\n\s*\n', '\n', response_text)  # Remove extra blank lines
                
#                 lines = [line.strip() for line in cleaned_text.split('\n') if '|' in line.strip()]
                
#                 if len(lines) >= 2:  # Need at least header and one data row
#                     # Try to find the header line
#                     header_line = lines[0]
                    
#                     # Extract header cells
#                     header_cells = [cell.strip() for cell in header_line.split('|') if cell.strip()]
                    
#                     if header_cells:
#                         data_rows = []
#                         for line in lines[1:]:
#                             # Skip separator rows
#                             if re.match(r'^[\s\-\+\|:]*$', line):
#                                 continue
                                
#                             # Extract cells
#                             cells = [cell.strip() for cell in line.split('|') if cell]
                            
#                             if cells:
#                                 # Adjust length to match headers
#                                 while len(cells) < len(header_cells):
#                                     cells.append("(Uncategorized)")
                                    
#                                 if len(cells) > len(header_cells):
#                                     cells = cells[:len(header_cells)]
                                    
#                                 data_rows.append(cells)
                        
#                         if data_rows:
#                             # Create dataframe
#                             manual_df = pd.DataFrame(data_rows, columns=header_cells)
#                             manual_df = standardize_output_format(manual_df)
                            
#                             # Extract only the text summary
#                             text_summary = ensure_text_summary(response_text, manual_df, query, is_time_comparison)
                            
#                             # Generate HTML
#                             html_table = dataframe_to_html_table(manual_df)
                            
#                             print("Generated HTML table content (fallback method)")
                            
#                             # Store in chat history - only the text summary
#                             CHAT_HISTORY.append({
#                                 "query": query,
#                                 "response": text_summary,
#                                 "user": current_user["username"]
#                             })
                            
#                             # Trim if needed
#                             if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#                                 CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
                            
#                             # Return only the text summary in the response
#                             return {
#                                 "response": text_summary,  # Only include the summary text
#                                 "html_content": html_table,
#                                 "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
#                             }
            
#             # If still no DataFrame, just return the text response
#             # print("\nText Response (Terminal Output):")
#             # print(response_text)
#             # print("\Final Result Response (Terminal Output): "+ final_result)
            
            
#             # Store chat history with user information
#             CHAT_HISTORY.append({
#                 "query": query,
#                 "response": response_text,
#                 "user": current_user["username"]
#             })
            
#             # Trim chat history if it exceeds max length
#             if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#                 CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            
#             # final_result = final_result or response_text
#             final_result = final_result if final_result != "" else response_text

#             return {
#                 "response": final_result,
#                 "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
#             }
    
#     except Exception as e:
#         print(f"Query processing error: {e}")
#         return {
#             "response": f"An error occurred during query processing: {str(e)}",
#             "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
#         }

# def replace_between_pipe_and_I(text, replacement):
#     start = text.find('|')
#     end = text.rfind('|')
#     if start != -1 and end != -1 and start < end:
#         return text[:start] + replacement + text[end+1:]
#     return text  # Return original if conditions not met

# def remove_newlines_replace(text):
#     return text.replace('\n', '')

# # Also update the extract_dataframe_from_text function for better table detection
# def extract_dataframe_from_text(text):
#     """
#     Enhanced function to extract table-like data from text response and convert to DataFrame
#     With improved detection to handle various table formats
#     """
#     try:
#         # Check if the response contains structured table data
#         if '|' in text and '\n' in text:
#             # Try to parse markdown table with more lenient approach
#             lines = [line.strip() for line in text.split('\n') if line.strip()]
            
#             # Look for lines with pipe characters (potential table rows)
#             table_lines = [line for line in lines if '|' in line]
            
#             if len(table_lines) >= 2:  # Need at least header and one data row
#                 # Find the most common pipe count to handle inconsistent formatting
#                 pipe_counts = [line.count('|') for line in table_lines]
#                 most_common_count = max(set(pipe_counts), key=pipe_counts.count)
                
#                 # Filter lines to those with the most common pipe count (± 1 to allow minor variations)
#                 consistent_lines = [line for line, count in zip(table_lines, pipe_counts) 
#                                    if abs(count - most_common_count) <= 1]
                
#                 if len(consistent_lines) >= 2:  # Still need at least header and one data row
#                     # Skip separator rows (those with mostly dashes)
#                     data_lines = [line for line in consistent_lines 
#                                  if not (line.replace('|', '').replace('-', '').replace(':', '').strip() == '')]
                    
#                     if len(data_lines) >= 2:
#                         # Parse headers from first line
#                         headers = [h.strip() for h in data_lines[0].split('|') if h.strip()]
                        
#                         # If we have reasonable headers, proceed with data extraction
#                         if len(headers) >= 2:
#                             data = []
#                             for line in data_lines[1:]:
#                                 # Split by pipe and clean up each cell
#                                 cells = [cell.strip() for cell in line.split('|')]
#                                 # Remove empty elements at start/end if they exist (from leading/trailing pipes)
#                                 if cells and not cells[0]: cells = cells[1:]
#                                 if cells and not cells[-1]: cells = cells[:-1]
                                
#                                 if cells:
#                                     # Ensure rows match header length
#                                     while len(cells) < len(headers):
#                                         cells.append("(Uncategorized)")
#                                     # Truncate if too long
#                                     cells = cells[:len(headers)]
#                                     data.append(cells)
                            
#                             if data:
#                                 df = pd.DataFrame(data, columns=headers)
#                                 return standardize_output_format(df)
        
#         # Check for HTML tables
#         if '<table' in text and '</table>' in text:
#             try:
#                 # Use pandas to parse HTML tables
#                 dfs = pd.read_html(text)
#                # print("gfdddff: ",dfs)
#                 if dfs and len(dfs) > 0:
#                     return standardize_output_format(dfs[0])
#             except Exception as html_err:
#                 print(f"HTML table parsing error: {html_err}")
        
#         # Fall back to checking for tabular patterns in plain text
#         if '\n' in text:
#             lines = [line.strip() for line in text.split('\n') if line.strip()]
#             if len(lines) >= 3:  # Need header, separator, and at least one data row
#                 # Check if there's a consistent pattern of data alignment
#                 # First look for spaces or common separators
#                 potential_delimiters = ['\t', '  ', ',', ';']
                
#                 for delimiter in potential_delimiters:
#                     if any(delimiter in line for line in lines[:3]):
#                         try:
#                             # Try parsing with this delimiter
#                             headers = [h.strip() for h in re.split(r'\s{2,}|\t|,|;', lines[0]) if h.strip()]
#                             if len(headers) >= 2:
#                                 data = []
#                                 for line in lines[1:]:
#                                     # Skip separator lines
#                                     if re.match(r'^[-+:|\s]+$', line):
#                                         continue
                                    
#                                     cells = [c.strip() for c in re.split(r'\s{2,}|\t|,|;', line) if c.strip()]
#                                     if len(cells) >= len(headers) * 0.7:  # Allow some flexibility
#                                         # Pad or truncate as needed
#                                         while len(cells) < len(headers):
#                                             cells.append("(Uncategorized)")
#                                         cells = cells[:len(headers)]
#                                         data.append(cells)
                                
#                                 if data:
#                                     df = pd.DataFrame(data, columns=headers)
#                                     return standardize_output_format(df)
#                         except Exception as delim_err:
#                             print(f"Delimiter parsing error: {delim_err}")
#                             continue
        
#         return None
#     except Exception as e:
#         print(f"Error extracting DataFrame: {e}")
#         return None

# @data_router.post("/clear_chat/")
# async def clear_chat(current_user: dict = Depends(get_current_user)):
#     """Clear entire chat history"""
#     global CHAT_HISTORY
    
#     # Check if user is admin for additional permissions
#     if current_user["role"] == "admin":
#         CHAT_HISTORY = []
#         return {"message": "Chat history cleared successfully."}
#     else:
#         # For non-admin users, only clear their own chat history
#         CHAT_HISTORY = [entry for entry in CHAT_HISTORY if entry.get("user") != current_user["username"]]
#         return {"message": f"Chat history for user {current_user['username']} cleared successfully."}

# # Include both routers in the main app
# app.include_router(auth_router)
# app.include_router(data_router)

# if __name__ == "__main__":
#     # uvicorn.run(app, host="localhost", port=8000)
#     # uvicorn.run(app, host="10.61.24.68", port=8000)
#     uvicorn.run(app, host="localhost", port=8000)





##################################################################################################################################
# from fastapi import FastAPI, HTTPException, Depends, status
# from pydantic import BaseModel
# from typing import List, Dict
# from datetime import datetime, timedelta
# import jwt
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# import pandas as pd
# import os
# from dotenv import load_dotenv
# from openai import OpenAI
# from langchain_community.chat_models import ChatOpenAI
# from langchain.agents.agent_types import AgentType
# from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
# from chat2plot import chat2plot
# from matplotlib.figure import Figure
# from fastapi.middleware.cors import CORSMiddleware
# import warnings
# import data_schema_1
# import uvicorn
# from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
# import plotly.express as px
# import json
# import io
# import re
# import chart_keywords
# import promptGuide
# import instructions

# # Suppress specific warnings
# warnings.filterwarnings('ignore', category=UserWarning)
# warnings.filterwarnings('ignore', category=DeprecationWarning)

# # Load environment variables
# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# app = FastAPI(title="Data Analysis API")
# DATA_SCHEMA = data_schema_1.DATA_SCHEMA
# DATA = None  # Global variable to store the dataset
# CHAT_HISTORY = []  # Global variable to store chat history
# MAX_HISTORY_LENGTH = 5  # Limit chat history length

# # Authentication configuration
# SECRET_KEY = "your_secret_key_here"
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 60

# # Dummy users database
# dummy_users = [
#     {"username": "testadmin", "password": "Admin@777", "role": "admin"},
#     {"username": "testuser", "password": "User@777", "role": "user"},
#     {"username": "testuser1", "password": "User@111", "role": "user"},
#     {"username": "testuser2", "password": "User@222", "role": "user"},
#     {"username": "testuser3", "password": "User@333", "role": "user"},
# ]

# # OAuth2 scheme for token authentication - UPDATED TO MATCH THE LOGIN ENDPOINT
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# # CORS middleware setup
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Set the CSV file path dynamically
# CSV_FILE_PATH = r"Warranty_Apertures_After2023 Latest Data.csv"

# # User Schema
# class User(BaseModel):
#     username: str
#     password: str
#     role: str

# # Token Schema
# class Token(BaseModel):
#     access_token: str
#     token_type: str

# # Query Request Schema
# class QueryRequest(BaseModel):
#     query: str

# # Helper Function: Authenticate User
# def authenticate_user(username: str, password: str):
#     for user in dummy_users:
#         if user["username"] == username and user["password"] == password:
#             return user
#     return None

# # Helper Function: Create JWT Token
# def create_access_token(data: dict, expires_delta: timedelta = None):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# # Helper Function: Get Current User
# def get_current_user(token: str = Depends(oauth2_scheme)):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username = payload.get("sub")
#         role = payload.get("role")
#         if username is None:
#             raise HTTPException(status_code=401, detail="Invalid token")
#         return {"username": username, "role": role}
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token expired")
#     except jwt.InvalidTokenError:
#         raise HTTPException(status_code=401, detail="Invalid token")

# # def robust_dataframe_conversion(df: pd.DataFrame) -> pd.DataFrame:
# #     """
# #     Enhanced robust DataFrame type conversion with flexible handling
# #     """
# #     # First, ensure all columns are read in the most flexible manner
# #     df = df.copy()
    
# #     for col in df.columns:
# #         try:
# #             # Try to convert to numeric first, coercing errors
# #             df[col] = pd.to_numeric(df[col], errors='ignore')
# #         except:
# #             pass
    
# #     # Specific schema-based conversions
# #     for schema_field in DATA_SCHEMA:
# #         col_name = schema_field['field']
# #         expected_type = schema_field['type']

# #         if col_name in df.columns:
# #             try:
# #                 if expected_type == 'string':
# #                     # Convert to string, handling NaN values with "(uncategorized)"
# #                     df[col_name] = df[col_name].astype(str)
# #                     df[col_name] = df[col_name].replace(['nan', 'None', '', 'NaN','null'], '(Uncategorized)')
                
# #                 elif expected_type == 'integer':
# #                     # More robust integer conversion - use a numeric placeholder for nulls
# #                     df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
# #                     # Use a numeric placeholder like -1 for nulls before converting to Int64
# #                     df[col_name] = df[col_name].fillna(-1).astype('int64')
# #                     # If you need to preserve the Int64 type with NA values instead:
# #                     # df[col_name] = pd.to_numeric(df[col_name], errors='coerce').astype('Int64')
                
# #                 elif expected_type == 'float':
# #                     # Convert to float, coercing errors
# #                     df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
# #                     df[col_name] = df[col_name].fillna(0.0)
                
# #                 elif expected_type == 'date':
# #                     # More flexible date parsing
# #                     df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
            
# #             except Exception as e:
# #                 print(f"Warning: Could not convert column {col_name}. Error: {e}")
# #                 continue

# #     return df

# def robust_dataframe_conversion(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Enhanced robust DataFrame type conversion with consistent null handling
#     """
#     df = df.copy()
    
#     for col in df.columns:
#         try:
#             # Try to convert to numeric first, coercing errors
#             df[col] = pd.to_numeric(df[col], errors='ignore')
#         except:
#             pass
    
#     # Specific schema-based conversions
#     for schema_field in DATA_SCHEMA:
#         col_name = schema_field['field']
#         expected_type = schema_field['type']

#         if col_name in df.columns:
#             try:
#                 if expected_type == 'string':
#                     # Convert to string, handling NaN values with "(uncategorized)"
#                     df[col_name] = df[col_name].astype(str)
#                     df[col_name] = df[col_name].replace(['nan', 'None', '', 'NaN','null'], '(Uncategorized)')
                
#                 elif expected_type == 'integer':
#                     # More robust integer conversion - use 0 for nulls (not -1)
#                     df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
#                     df[col_name] = df[col_name].fillna(0).astype('int64')  # Changed from -1 to 0
                
#                 elif expected_type == 'float':
#                     # Convert to float, coercing errors
#                     df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
#                     df[col_name] = df[col_name].fillna(0.0)
                
#                 elif expected_type == 'date':
#                     # More flexible date parsing
#                     df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
            
#             except Exception as e:
#                 print(f"Warning: Could not convert column {col_name}. Error: {e}")
#                 continue

#     return df

# def load_data():
#     """
#     Enhanced data loading with more robust error handling
#     """
#     global DATA
#     if os.path.exists(CSV_FILE_PATH):
#         try:
#             # Use more flexible CSV reading
#             df = pd.read_csv(
#                 CSV_FILE_PATH, 
#                 encoding="ISO-8859-1", 
#                 low_memory=False,
#                 dtype_backend='pyarrow'  # Use pyarrow for better type inference
#             )
            
#             # Robust conversion
#             DATA = robust_dataframe_conversion(df)
            
#             # Additional data validation
#             print(f"Dataset loaded successfully. Shape: {DATA.shape}")
#             print("Available columns:", list(DATA.columns))
            
#             # Print unique years if Date column exists
#             if 'Date' in DATA.columns:
#                 years = DATA['Date'].dt.year.unique()
#                 print("Years in dataset:", sorted(years))
            
#             return True
#         except Exception as e:
#             print(f"Error loading dataset: {e}")
#             return False
#     else:
#         print("Error: CSV file not found at the specified path.")
#         return False

# # NEW HELPER FUNCTIONS FOR VISUALIZATION

# # def dataframe_to_html_table(df):
# #     """
# #     Convert a pandas DataFrame to a styled HTML table with more robust formatting
# #     """
# #     if df is None or df.empty:
# #         return "<p>No data available</p>"
    
# #     try:
# #         # First ensure all values are properly represented as strings
# #         for col in df.columns:
# #             df[col] = df[col].apply(lambda x: "(Uncategorized)" if pd.isna(x) or x == "" or x == "nan" or x == "None" or x == "null" else str(x))
        
# #         # Apply styling to the HTML table
# #         table_html = df.to_html(
# #             index=False, 
# #             classes="table table-striped table-hover table-bordered", 
# #             border=1,
# #             escape=False,
# #             na_rep="(Uncategorized)"
# #         )
        
# #         # Add custom styling
# #         styled_table = f"""
# #         <div class="table-responsive">
# #         \n\n\n{table_html}\n\n
# #         </div>
# #         """
# #         return styled_table
# #     except Exception as e:
# #         print(f"Error creating HTML table: {e}")
# #         return f"<p>Error generating table: {str(e)}</p>"

# def dataframe_to_html_table(df):
#     """
#     Convert a pandas DataFrame to a styled HTML table with consistent null handling
#     """
#     if df is None or df.empty:
#         return "<p>No data available</p>"
    
#     try:
#         # Apply standardized formatting (ensure this happens first)
#         df = standardize_output_format(df)  # This ensures consistent null handling
        
#         # Apply styling to the HTML table
#         table_html = df.to_html(
#             index=False, 
#             classes="table table-striped table-hover table-bordered", 
#             border=1,
#             escape=False,
#             na_rep="0"  # Use "0" for numeric NA values rather than "(Uncategorized)"
#         )
        
#         # Add custom styling
#         styled_table = f"""
#         <div class="table-responsive">
#         \n\n\n{table_html}\n\n
#         </div>
#         """
#         return styled_table
#     except Exception as e:
#         print(f"Error creating HTML table: {e}")
#         return f"<p>Error generating table: {str(e)}</p>"


# # def check_uncategorized_percentage(df):
# #     """
# #     Check what percentage of the DataFrame contains uncategorized values
# #     Returns the percentage and a boolean indicating if it's too high for visualization
# #     """
# #     total_cells = df.size
# #     uncategorized_count = 0
    
# #     for col in df.columns:
# #         # Count uncategorized values in this column
# #         uncategorized_count += df[col].apply(lambda x: 
# #             1 if pd.isna(x) or str(x).lower() in ['nan', 'none', '', 'uncategorized', '(uncategorized)'] 
# #             else 0).sum()
    
# #     percentage = (uncategorized_count / total_cells) * 100 if total_cells > 0 else 0
# #     # If more than 30% of data is uncategorized, avoid visualization
# #     return percentage, percentage > 30


# def check_uncategorized_percentage(df):
#     """
#     Check what percentage of the DataFrame contains uncategorized values
#     Returns the percentage and a boolean indicating if it's too high for visualization
#     """
#     total_cells = df.size
#     uncategorized_count = 0
    
#     for col in df.columns:
#         # Count uncategorized values based on column type
#         if pd.api.types.is_numeric_dtype(df[col]):
#             # For numeric columns, count NaN values (we will replace these with 0)
#             uncategorized_count += df[col].isna().sum()
#         else:
#             # For non-numeric columns, check for various empty/null representations
#             uncategorized_count += df[col].apply(lambda x: 
#                 1 if pd.isna(x) or str(x).lower() in ['nan', 'none', '', 'uncategorized', '(uncategorized)', 'null'] 
#                 else 0).sum()
    
#     percentage = (uncategorized_count / total_cells) * 100 if total_cells > 0 else 0
#     # If more than 30% of data is uncategorized, avoid visualization
#     return percentage, percentage > 30


# def generate_plotly_chart(df, query):
#     """
#     Generate a Plotly chart based on the DataFrame and query content
#     """
#     try:
#         # Check for too many uncategorized values
#         uncategorized_percentage, too_many_uncategorized = check_uncategorized_percentage(df)
        
#         if too_many_uncategorized:
#             return f"""
#             <div class="alert alert-warning">
#                 <h4>Visualization Not Recommended</h4>
#                 <p>The data contains {uncategorized_percentage:.1f}% uncategorized values, which would result in a misleading chart. 
#                 Please refer to the table for details.</p>
#             </div>
#             """

#         # --- Determine chart type based on keywords ---
#         query_lower = query.lower()
#         chart_type = "unknown"

#         if any(term in query_lower for term in chart_keywords.line_chart_keywords):
#             chart_type = "line"
#         elif any(term in query_lower for term in chart_keywords.pie_chart_keywords):
#             chart_type = "pie"
#         elif any(term in query_lower for term in chart_keywords.scatter_chart_keywords):
#             chart_type = "scatter"
#         # elif any(term in query_lower for term in chart_keywords.histogram_keywords):
#         #     chart_type = "histogram"
#         elif any(term in query_lower for term in chart_keywords.bar_chart_keywords):
#             chart_type = "bar"
#         else:
#             # Default to bar for categorical data, line for time series, or bar as general fallback
#             categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
#             numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
#             date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower() or 'year' in col.lower() or 'month' in col.lower()]
            
#             if date_cols and numeric_cols:
#                 chart_type = "line"  # Time-series data
#             elif categorical_cols and numeric_cols:
#                 chart_type = "bar"   # Categorical data
#             else:
#                 chart_type = "bar"   # Default fallback

#         # --- Identify X and Y columns ---
#         numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
#         categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()

#         if len(df.columns) >= 2:
#             x_col = categorical_cols[0] if categorical_cols else df.columns[0]
#             y_col = numeric_cols[0] if numeric_cols else df.columns[1]

#             # --- Create chart based on type ---
#             chart_title = f"{chart_type.capitalize()} Chart: {y_col} by {x_col}"
            
#             if chart_type == "bar":
#                 fig = px.bar(df, x=x_col, y=y_col, title=chart_title)
#             elif chart_type == "line":
#                 fig = px.line(df, x=x_col, y=y_col, title=chart_title)
#             elif chart_type == "pie":
#                 fig = px.pie(df, names=x_col, values=y_col, title=chart_title)
#             elif chart_type == "scatter":
#                 fig = px.scatter(df, x=x_col, y=y_col, title=chart_title)
#             elif chart_type == "histogram":
#                 fig = px.histogram(df, x=y_col, title=f"Histogram of {y_col}")
#             else:
#                 return "<p>Could not determine a suitable chart type from the query.</p>"

#             # --- Update layout ---
#             fig.update_layout(
#                 template="plotly_white",
#                 margin=dict(l=40, r=40, t=40, b=40),
#                 legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
#             )

#             # --- Convert to HTML ---
#             chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
            
#             # Add a header to clearly identify the chart type
#             chart_with_header = f"""
#             <div class="chart-container">
#                 <h4>Visualization Type: {chart_type.capitalize()} Chart</h4>
#                 {chart_html}
#             </div>
#             """
#             return chart_with_header
#         else:
#             return "<p>Insufficient data for visualization</p>"
#     except Exception as e:
#         print(f"Error generating chart: {e}")
#         return f"<p>Error generating visualization: {str(e)}</p>"


# def extract_dataframe_from_text(text):
#     """
#     Attempt to extract table-like data from text response and convert to DataFrame
#     """
#     try:
#         # Check if the response contains structured table data
#         if '|' in text and '\n' in text:
#             # Try to parse markdown table
#             lines = [line.strip() for line in text.split('\n') if line.strip()]
#             # Find table boundaries
#             start_idx = None
#             end_idx = None
            
#             for i, line in enumerate(lines):
#                 if '|' in line:
#                     if start_idx is None:
#                         start_idx = i
#                     end_idx = i
            
#             if start_idx is not None and end_idx is not None:
#                 table_lines = lines[start_idx:end_idx+1]
#                 # Remove markdown table formatting lines (those with dashes)
#                 table_lines = [line for line in table_lines if not line.replace('|', '').strip().startswith('---')]
                
#                 # Parse headers and data
#                 headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
#                 data = []
                
#                 for line in table_lines[1:]:
#                     row_data = [cell.strip() for cell in line.split('|') if cell.strip()]
#                     if row_data:
#                         data.append(row_data)
                
#                 # Create DataFrame
#                 if headers and data:
#                     # Make sure data rows have the same length as headers
#                     data = [row for row in data if len(row) == len(headers)]
#                     df = pd.DataFrame(data, columns=headers)
#                     return df
        
#         # If basic parsing failed, try more aggressive methods
#         import re
        
#         # Look for table patterns in the text
#         table_pattern = r'\b(\w+)\s*\|\s*([\w\s\.]+)\s*\|\s*([\w\s\.]+)'
#         matches = re.findall(table_pattern, text)
        
#         if matches:
#             # Try to determine the number of columns
#             col_count = len(matches[0])
#             headers = ["Column" + str(i+1) for i in range(col_count)]
#             df = pd.DataFrame(matches, columns=headers)
#             return df
        
#         return None
#     except Exception as e:
#         print(f"Error extracting DataFrame: {e}")
#         return None

# def combine_chart_and_table(chart_html, table_html, title="Data Analysis Results"):
#     """
#     Combine chart and table into a single HTML page
#     """
#     combined_html = f"""
#     <div class="analysis-container">
#         <h2>{title}</h2>
#         <div class="chart-container">
#             <h3>Visualization</h3>
#             {chart_html}
#         </div>
#         <div class="table-container">
#             <h3>Data Table</h3>
#             {table_html}
#         </div>
#     </div>
#     """
#     return combined_html

# # Call load_data during startup
# load_data()

# # Create routers for each group
# auth_router = APIRouter(tags=["Auth"])
# data_router = APIRouter(tags=["data-analysis"])

# # Authentication Endpoints
# @auth_router.post("/login", response_model=Token)
# async def login(form_data: OAuth2PasswordRequestForm = Depends()):
#     user = authenticate_user(form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token = create_access_token({"sub": user["username"], "role": user["role"]})
#     return {"access_token": access_token, "token_type": "bearer"}

# @auth_router.get("/me")
# async def read_current_user(current_user: dict = Depends(get_current_user)):
#     return current_user

# @auth_router.post("/register", response_model=User)
# async def register(user: User):
#     for existing_user in dummy_users:
#         if existing_user["username"] == user.username:
#             raise HTTPException(status_code=400, detail="Username already exists")
#     new_user = {"username": user.username, "password": user.password, "role": user.role}
#     dummy_users.append(new_user)
#     return new_user

# @auth_router.post("/logout")
# async def logout():
#     return {"message": "Logout successful. Remove token on frontend."}

# # def standardize_output_format(df):
# #     """
# #     Standardize DataFrame output formatting for both terminal and API responses
# #     """
# #     # Create a deep copy to avoid modifying the original
# #     formatted_df = df.copy()
    
# #     # Ensure consistent handling of null/NA values
# #     for col in formatted_df.columns:
# #         # Check if the column is numeric
# #         is_numeric = pd.api.types.is_numeric_dtype(formatted_df[col])
        
# #         if is_numeric:
# #             # For numeric columns, leave nulls as is or replace with a numeric value
# #             formatted_df[col] = formatted_df[col].fillna(-1)
# #         else:
# #             # For non-numeric columns, replace nulls with "(Uncategorized)"
# #             formatted_df[col] = formatted_df[col].fillna("(Uncategorized)")
# #             # Convert objects like pandas NA to string "(Uncategorized)"
# #             formatted_df[col] = formatted_df[col].astype(str)
# #             formatted_df[col] = formatted_df[col].replace(['nan', 'None', '', 'NaN', 'null', '<NA>'], '(Uncategorized)')
    
# #     return formatted_df

# def standardize_output_format(df):
#     """
#     Standardize DataFrame output formatting with consistent null handling
#     """
#     # Create a deep copy to avoid modifying the original
#     formatted_df = df.copy()
    
#     # Ensure consistent handling of null/NA values
#     for col in formatted_df.columns:
#         # Check if the column is numeric
#         is_numeric = pd.api.types.is_numeric_dtype(formatted_df[col])
        
#         if is_numeric:
#             # For numeric columns, replace nulls with 0 (not -1)
#             formatted_df[col] = formatted_df[col].fillna(0)
#         else:
#             # For non-numeric columns, replace nulls with "(Uncategorized)"
#             formatted_df[col] = formatted_df[col].fillna("(Uncategorized)")
#             # Convert objects like pandas NA to string "(Uncategorized)"
#             formatted_df[col] = formatted_df[col].astype(str)
#             formatted_df[col] = formatted_df[col].replace(['nan', 'None', '', 'NaN', 'null', '<NA>'], '(Uncategorized)')
    
#     return formatted_df

# # Add this function to check if the response is a list
# def is_list_response(text):
#     """
#     Determine if the response appears to be a list of items rather than tabular data
#     """
#     # Check for common list indicators
#     list_indicators = [
#         text.count("\n1.") > 0,  # Numbered list starting with 1.
#         text.count("\n- ") > 1,  # Bullet points with dashes
#         text.count("\n* ") > 1,  # Bullet points with asterisks
#         text.count("\n•") > 1,   # Bullet points with bullet character
#         bool(re.search(r'\n\d+\.\s+', text)),  # Any numbered list
#         bool(re.search(r'Top \d+ ', text)) and text.count("\n") > 2,  # Contains "Top N" and multiple lines
#         bool(re.search(r'(\n\s*([A-Za-z0-9][\)\.:]|\d+[\)\.:])\s+)', text))  # Formatted list with parentheses or periods
#     ]
    
#     # Look for "Top N" or "N questions" type patterns in the query
#     list_keywords = [
#         'list', 'top', 'questions', 'reasons', 'factors', 'steps',
#         'best', 'worst', 'highest', 'lowest', 'most common',
#         'frequently', 'commonly', 'popular', 'tips', 'advice', 'suggestions'
#     ]
    
#     contains_list_keywords = any(keyword in text.lower() for keyword in list_keywords)
    
#     # If we have at least one list indicator or contains list keywords and has multiple lines
#     return any(list_indicators) or (contains_list_keywords and text.count("\n") > 2)

# # Also update the query_data function to handle lists better
# @data_router.post("/query/")
# async def query_data(request: QueryRequest, current_user: dict = Depends(get_current_user)):
#     global DATA, CHAT_HISTORY
#     if DATA is None:
#         # Attempt to reload data if not already loaded
#         if not load_data():
#             raise HTTPException(status_code=400, detail="No data loaded.")
    
#     query = request.query
    
#     # # Special case for greetings or simple queries
#     # greeting_keywords = ["hi", "hello", "hey", "greetings", "howdy", "good morning", "good afternoon", "good evening"]
    
#     # if query.lower() in greeting_keywords or len(query.split()) <= 3:
#     #     greeting_response = f"Hello {current_user['username']}! I'm your data analysis assistant. You can ask me questions about your warranty data, such as 'What are the top problem codes by cost?' or 'Show me warranty trends by business unit'. How can I help you analyze your data today?"
        
#     #     # Store in chat history
#     #     CHAT_HISTORY.append({
#     #         "query": query,
#     #         "response": greeting_response,
#     #         "user": current_user["username"]
#     #     })
        
#     #     # Trim if needed
#     #     if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#     #         CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
        
#     #     return {
#     #         "response": greeting_response
#     #     }
    
#     # Check if this is likely a request for a list
#     is_list_request = any(keyword in query.lower() for keyword in [
#         'list', 'top', 'questions', 'reasons', 'factors', 'steps',
#         'best', 'worst', 'highest', 'lowest', 'most common',
#         'frequently', 'commonly', 'popular', 'tips', 'advice', 'suggestions'
#     ])
    
#     # Check if this is a time comparison request (YoY/MoM)
#     is_time_comparison = any(term in query.lower() for term in [
#         'yoy', 'mom', 'year over year', 'month over month', 'yearly', 'monthly',
#         'compared to last', 'previous year', 'previous month', 'comparison',
#         'trend', 'performance over time', 'change since', 'growth'
#     ])
    
#     # Log the user making the query
#     print(f"Query received from user: {current_user['username']} with role: {current_user['role']}")
#     print(f"Is this likely a list request? {is_list_request}")
#     print(f"Is this likely a time comparison? {is_time_comparison}")

#     if not OPENAI_API_KEY:
#         raise HTTPException(status_code=500, detail="OpenAI API key is missing")

#     final_result = ""
#     html_table = ""
    
#     # Helper function to ensure text summaries
#     def ensure_text_summary(response_text, result_df, query, is_time_comparison=False):
#         """Ensures that a proper text summary exists without table formatting"""
        
#         # Check if there's already a text summary in the response
#         lines = response_text.strip().split('\n')
        
#         # Extract only the text part before any table formatting
#         summary_lines = []
#         for line in lines:
#             if '|' in line and '-' in line:  # We've reached the table
#                 break
#             if not line.strip().startswith('|'):  # Skip any table lines
#                 summary_lines.append(line)
        
#         summary_text = '\n'.join(summary_lines).strip()
        
#         # If we don't have a summary and we have a dataframe, generate one
#         if (not summary_text or len(summary_text) < 40) and result_df is not None and not result_df.empty:
#             try:
#                 # Find time columns if they exist
#                 time_cols = [col for col in result_df.columns if col.lower() in [
#                     'year', 'month', 'date', 'period', 'quarter', 'time', 'week'
#                 ]]
                
#                 # Create a basic summary
#                 summary_parts = []
                
#                 # If this is a time comparison and we have time columns
#                 if is_time_comparison and time_cols:
#                     time_col = time_cols[0]  # Use the first identified time column
                    
#                     # Get unique time periods
#                     time_periods = sorted(result_df[time_col].unique())
                    
#                     if len(time_periods) >= 2:
#                         # Find numeric columns for analysis (exclude percentage columns)
#                         numeric_cols = [col for col in result_df.columns 
#                                       if col not in time_cols and 
#                                       col.lower() not in ['difference in %', '% change', 'percent', 'percentage'] and
#                                       pd.api.types.is_numeric_dtype(result_df[col])]
                        
#                         # For each numeric column, check the changes
#                         for col in numeric_cols[:3]:  # Limit to top 3 columns
#                             try:
#                                 # For simple two-period comparison
#                                 if len(time_periods) == 2:
#                                     val1 = result_df[result_df[time_col] == time_periods[0]][col].iloc[0]
#                                     val2 = result_df[result_df[time_col] == time_periods[1]][col].iloc[0]
                                    
#                                     if val1 != 0:
#                                         pct_change = ((val2 - val1) / val1) * 100
#                                         direction = "increased" if pct_change > 0 else "decreased"
#                                         summary_parts.append(f"{col} {direction} by {abs(pct_change):.1f}% from {time_periods[0]} to {time_periods[1]}")
#                             except:
#                                 continue
                
#                 # If we couldn't generate specific time comparisons, create a generic summary
#                 if not summary_parts:
#                     # Get column with largest values
#                     try:
#                         numeric_cols = [col for col in result_df.columns 
#                                        if pd.api.types.is_numeric_dtype(result_df[col])]
                        
#                         if numeric_cols:
#                             max_col = max(numeric_cols, key=lambda col: result_df[max_col].max())
#                             max_row_idx = result_df[max_col].idxmax()
#                             max_row = result_df.iloc[max_row_idx]
                            
#                             # Create a summary for this finding
#                             max_value = max_row[max_col]
#                             id_col = next((col for col in result_df.columns 
#                                           if col.lower() in ['name', 'id', 'category', 'type', 'description']), 
#                                           result_df.columns[0])
                            
#                             id_value = max_row[id_col]
#                             summary_parts.append(f"The highest {max_col} is {max_value:,.2f} for {id_value}.")
#                     except:
#                         pass
                
#                 # If we have summary parts, create the summary
#                 if summary_parts:
#                     if len(summary_parts) > 1:
#                         summary = f"{summary_parts[0]} {summary_parts[1]}"
#                     else:
#                         summary = summary_parts[0]
                        
#                     # Add information about the dataset
#                     summary += f" This analysis is based on {len(result_df)} data points."
#                 else:
#                     # Create a generic summary
#                     summary = f"Analysis of {query} based on {len(result_df)} data points. "
                    
#                     # For time comparisons, add more context about the periods
#                     if is_time_comparison and time_cols:
#                         time_col = time_cols[0]
#                         time_periods = sorted(result_df[time_col].unique())
#                         if len(time_periods) >= 2:
#                             summary += f"Comparing {time_periods[0]} to {time_periods[-1]}, "
                    
#                     # Add basic info about what's in the data
#                     if len(result_df.columns) > 1:
#                         main_cols = [col for col in result_df.columns if col not in ['% Change_Cost', '% Change_Units']][:3]
#                         summary += f"The data shows values for {', '.join(main_cols)}."
                
#                 return summary
                    
#             except Exception as e:
#                 print(f"Error generating summary: {e}")
        
#         return summary_text if summary_text else "Analysis of the requested data:"

#     try:
#         # Use latest OpenAI model with enhanced capabilities
#         agent = create_pandas_dataframe_agent(
#             ChatOpenAI(
#                 temperature=0, 
#                 model="gpt-4o-mini", 
#                 api_key=OPENAI_API_KEY
#             ),
#             DATA,
#             # verbose=True,  # Enable for more detailed debugging
#             verbose=False,  # Enable for more detailed debugging
#             agent_type=AgentType.OPENAI_FUNCTIONS,
#             allow_dangerous_code=True
#         )

#             # print("AGENT OUTPUT: \n"+  agent + "\n")
        
#         # Enhanced chat2plot with more robust plotting
#         c2p = chat2plot(
#             DATA, 
#             language="English", 
#             chat=ChatOpenAI(
#                 model="gpt-4o-mini", 
#                 api_key=OPENAI_API_KEY
#             )
#         )
        
#         # Prepare context from chat history
#         context = "\n".join([f"Previous User Query: {entry['query']}\nPrevious Bot Response: {entry['response']}" for entry in CHAT_HISTORY[-MAX_HISTORY_LENGTH:]])
        
      
#         # Customize the query format based on the request type
#         if is_list_request:
#             query_format = "Your response should be formatted as a concise numbered list preceded by a brief introduction, NOT as a table."
#         elif is_time_comparison:
#             query_format = "This is a time comparison query. Begin with a 2-4 sentence text summary highlighting the key changes, THEN show a properly formatted markdown table with a percentage change column."
#         else:
#             query_format = "If showing complex data, include a 2-4 sentence description followed by a properly formatted markdown table with proper header and separator rows."
        
#         refined_query = f"""Considering previous conversation context:
# {context}

# Important formatting instructions: {instructions.formatting_instruction}
# Format note: {query_format}

# New Query: {query}

# Remember: For tables, ALWAYS START with a 2-4 sentence text summary BEFORE the table explaining key findings.
# For time-based comparisons (YoY, MoM), ALWAYS include percentage changes with + or - prefixes.
# For lists of items (like "top N" questions), use a simple numbered list format, not a table.
# For tabular data, use proper markdown table format with | separators, header row, and separator row with dashes.
# """
        
#         # Check if it's a visualization request
#         is_visualization_request = any(term in query.lower() for term in [
#             'chart', 'plot', 'graph', 'visualize', 'show', 'display', 'visualisation', 
#             'pie', 'bar', 'line', 'scatter', 'histogram', 'trend'
#         ])
        
#         # For visualization requests, use Plotly
#         if is_visualization_request:
            
#             try:
#                 # First get data for visualization
#                 data_query = f"Based on this query: '{query}', provide the data needed for visualization as a pandas DataFrame with clear column names. Format your response to include only the necessary data in a well-structured markdown table format with proper header and separator rows."
                
#                 data_res = agent.invoke(data_query)
#                 data_text = (
#                     data_res.get("output") if isinstance(data_res, dict) else 
#                     str(data_res) if data_res else 
#                     "Could not find data for visualization."
#                 )
                
#                 # Extract DataFrame from the text response
#                 visualization_df = extract_dataframe_from_text(data_text)
                
#                 if visualization_df is None or visualization_df.empty:
#                     # If extraction failed, run a more direct query
#                     direct_query = f"For the query '{query}', return a pandas DataFrame with at most 20 rows that would be suitable for visualization. Format your response to show just the table of data with proper markdown table formatting."
                    
#                     direct_res = agent.invoke(direct_query)
#                     direct_text = (
#                         direct_res.get("output") if isinstance(direct_res, dict) else 
#                         str(direct_res) if direct_res else 
#                         "Could not find data for visualization."
#                     )
                    
#                     visualization_df = extract_dataframe_from_text(direct_text)
                
#                 # If we now have a DataFrame, generate visualization
#                 if visualization_df is not None and not visualization_df.empty:
#                     # Standardize the output format
#                     visualization_df = standardize_output_format(visualization_df)
                    
#                     # Create a text summary for the visualization
#                     summary_query = f"""Based on this data:
# {visualization_df.to_string(index=False)}

# Generate a 2-3 sentence summary highlighting:
# 1. The most significant patterns or findings
# 2. Any notable outliers or special cases
# 3. The key insight this visualization will demonstrate

# Format as plain text paragraph only, no tables."""

#                     summary_res = agent.invoke(summary_query)
#                     summary_text = (
#                         summary_res.get("output") if isinstance(summary_res, dict) else 
#                         str(summary_res) if summary_res else 
#                         "Visualization of query results."
#                     )
                    
#                     # Print the exact same DataFrame to terminal for consistency
#                     print("\nVisualization DataFrame (Terminal Output):")
#                     print(visualization_df.to_string(index=False))
                    
#                     # Generate chart HTML
#                     chart_html = generate_plotly_chart(visualization_df, query)
                    
#                     # Generate table HTML
#                     table_html = dataframe_to_html_table(visualization_df)
                    
#                     # Combine into a single HTML response with summary
#                     combined_html = combine_chart_and_table(chart_html, table_html, f"{summary_text}")
                    
#                     # Store chat history
#                     CHAT_HISTORY.append({
#                         "query": query,
#                         "response": f"{summary_text}",  # Only store the summary
#                         "user": current_user["username"]
#                     })
                    
#                     # Trim chat history if it exceeds max length
#                     if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#                         CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
                    
#                     print("HTML Content : ", table_html)

#                     return {
#                         "response": f"{summary_text}",  # Only return the summary
#                         "html_content": combined_html,
#                         "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
#                     }
#                 else:
#                     # Fallback to traditional response
#                     print("Could not extract DataFrame for visualization, falling back to text response")
#             except Exception as viz_error:
#                 print(f"Visualization error: {viz_error}")
#                 # Continue with text-based response as fallback
        
#         # Process the analytical query
#         res = agent.invoke(refined_query)
        
#         # Extract response with multiple fallback mechanisms
#         response_text = (
#             res.get("output") if isinstance(res, dict) else 
#             str(res) if res else 
#             "Could not find a definitive answer to your question."
#         )
        
#         # Enhanced post-processing to ensure proper markdown table formatting
#         response_text = response_text.replace(" (blank)", " (Uncategorized)")
#         response_text = response_text.replace(" (null)", " (Uncategorized)")
#         response_text = response_text.replace(" (empty)", " (Uncategorized)")
#         response_text = response_text.replace("Blank: ", "(Uncategorized): ")
#         response_text = response_text.replace("Empty: ", "(Uncategorized): ")
#         response_text = response_text.replace("Null: ", "(Uncategorized): ")
#         response_text = response_text.replace("NA: ", "(Uncategorized): ")
#         response_text = response_text.replace("<NA>", "(Uncategorized)")
        
#         # Debug output to see what was received
#         #print(f"\nRaw response text:\n{response_text[:500]}...")
        
#         # Check if the response appears to be a list rather than tabular data
#         is_list_response_result = is_list_response(response_text)
#         #print(f"Is list response: {is_list_response_result}")
        
#         # First check if there's a table in the response
#         has_table = '|' in response_text and '\n' in response_text and '-' in response_text
#         #print(f"Has table markers: {has_table}")
        
#         # Check if the response is short
#         is_short_response = len(response_text.split('\n')) < 3 and len(response_text) < 300 and not has_table
        
#         # Always attempt to extract DataFrame even if it looks like a list
#         result_df = None
#         if not is_short_response:
#             # Try to extract DataFrame - this uses our improved function
#             result_df = extract_dataframe_from_text(response_text)
#             #raw_text = remove_newlines_replace(response_text)
            
         

#             # Debug output
#             if result_df is not None:
#                 print(f"Successfully extracted DataFrame with shape: {result_df.shape}")
#             else:
#                 print("Failed to extract DataFrame")
        
#         # If we found a DataFrame, format it as HTML table
#         if result_df is not None and not result_df.empty:
#             # Standardize the output format
#             result_df = standardize_output_format(result_df)

#             print("\nresult_df: \n", result_df, "\n")
#             # Print the exact same DataFrame to terminal for consistency
#             #print("\nResult DataFrame (Terminal Output):")
#             print(result_df.to_string(index=False))
            
#             # Get just the text summary without table formatting
#             text_summary = ensure_text_summary(response_text, result_df, query, is_time_comparison)
            
#             # Use our improved HTML table function
#             html_table = dataframe_to_html_table(result_df)
#             # chart_html = generate_plotly_chart(result_df, query)
#             chart_html = generate_plotly_chart(result_df, response_text)
#             final_table = remove_newlines_replace(html_table)
#             # chart_htm = generate_plotly_chart(result_df, response_text)
#             final_result = replace_between_pipe_and_I(response_text,"\n" + final_table + "\n")
#             #final_result = replace_between_pipe_and_I(final_result1,"\n" + chart_html  + "\n")
#             # final_result = final_result + "\n" + chart_html
            

#             # print("\n\nfinal_result1: ", final_result1)
#             # print("\n\nfinal_result: ", final_result)
#             # print("\n\nchart_html: ",chart_html)

            
#             print("\nHTML chart content: ", chart_html, "\n")
#             # print("\ntext_summary: ", text_summary)
#             # print("\nhtml_table: ", html_table)
#             print("\nfinal_table: ", final_table, "\n")
            
#             # Store chat history with user information - using just the text summary
#             CHAT_HISTORY.append({
#                 "query": query,
#                 "response": text_summary,
#                 "user": current_user["username"]
#             })
            
#             # Trim chat history if it exceeds max length
#             if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#                 CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            
#             # Only return the summary text in the response
#             return {
#                     "response": final_result,
#                     "chart_html": chart_html # Only include the summary text
#                    }
#         else:
#             # Force a fallback attempt for responses that contain pipe characters but weren't properly parsed
#             if has_table and '|' in response_text:
#                 print("Attempting fallback table parsing for response with pipe characters")
                
#                 # Clean up the text to make it more parseable
#                 cleaned_text = re.sub(r'\n\s*\n', '\n', response_text)  # Remove extra blank lines
                
#                 lines = [line.strip() for line in cleaned_text.split('\n') if '|' in line.strip()]
                
#                 if len(lines) >= 2:  # Need at least header and one data row
#                     # Try to find the header line
#                     header_line = lines[0]
                    
#                     # Extract header cells
#                     header_cells = [cell.strip() for cell in header_line.split('|') if cell.strip()]
                    
#                     if header_cells:
#                         data_rows = []
#                         for line in lines[1:]:
#                             # Skip separator rows
#                             if re.match(r'^[\s\-\+\|:]*$', line):
#                                 continue
                                
#                             # Extract cells
#                             cells = [cell.strip() for cell in line.split('|') if cell]
                            
#                             if cells:
#                                 # Adjust length to match headers
#                                 while len(cells) < len(header_cells):
#                                     cells.append("(Uncategorized)")
                                    
#                                 if len(cells) > len(header_cells):
#                                     cells = cells[:len(header_cells)]
                                    
#                                 data_rows.append(cells)
                        
#                         if data_rows:
#                             # Create dataframe
#                             manual_df = pd.DataFrame(data_rows, columns=header_cells)
#                             manual_df = standardize_output_format(manual_df)
                            
#                             # Extract only the text summary
#                             text_summary = ensure_text_summary(response_text, manual_df, query, is_time_comparison)
                            
#                             # Generate HTML
#                             html_table = dataframe_to_html_table(manual_df)
                            
#                             print("Generated HTML table content (fallback method)")
                            
#                             # Store in chat history - only the text summary
#                             CHAT_HISTORY.append({
#                                 "query": query,
#                                 "response": text_summary,
#                                 "user": current_user["username"]
#                             })
                            
#                             # Trim if needed
#                             if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#                                 CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
                            
#                             # Return only the text summary in the response
#                             return {
#                                 "response": text_summary,  # Only include the summary text
#                                 "html_content": html_table,
#                                 "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
#                             }
            
#             # If still no DataFrame, just return the text response
#             print("\nText Response (Terminal Output):")
#             print(response_text)
#             print("Final Result Response (Terminal Output): "+ final_result)
            
            
#             # Store chat history with user information
#             CHAT_HISTORY.append({
#                 "query": query,
#                 "response": response_text,
#                 "user": current_user["username"]
#             })
            
#             # Trim chat history if it exceeds max length
#             if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#                 CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            
#             # final_result = final_result or response_text
#             final_result = final_result if final_result != "" else response_text

#             return {
#                 "response": final_result,
#                 "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
#             }
    
#     except Exception as e:
#         print(f"Query processing error: {e}")
#         return {
#             "response": f"An error occurred during query processing: {str(e)}",
#             "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
#         }

# def replace_between_pipe_and_I(text, replacement):
#     start = text.find('|')
#     end = text.rfind('|')
#     if start != -1 and end != -1 and start < end:
#         return text[:start] + replacement + text[end+1:]
#     return text  # Return original if conditions not met

# def remove_newlines_replace(text):
#     return text.replace('\n', '')

# # Also update the extract_dataframe_from_text function for better table detection
# def extract_dataframe_from_text(text):
#     """
#     Enhanced function to extract table-like data from text response and convert to DataFrame
#     With improved detection to handle various table formats
#     """
#     try:
#         # Check if the response contains structured table data
#         if '|' in text and '\n' in text:
#             # Try to parse markdown table with more lenient approach
#             lines = [line.strip() for line in text.split('\n') if line.strip()]
            
#             # Look for lines with pipe characters (potential table rows)
#             table_lines = [line for line in lines if '|' in line]
            
#             if len(table_lines) >= 2:  # Need at least header and one data row
#                 # Find the most common pipe count to handle inconsistent formatting
#                 pipe_counts = [line.count('|') for line in table_lines]
#                 most_common_count = max(set(pipe_counts), key=pipe_counts.count)
                
#                 # Filter lines to those with the most common pipe count (± 1 to allow minor variations)
#                 consistent_lines = [line for line, count in zip(table_lines, pipe_counts) 
#                                    if abs(count - most_common_count) <= 1]
                
#                 if len(consistent_lines) >= 2:  # Still need at least header and one data row
#                     # Skip separator rows (those with mostly dashes)
#                     data_lines = [line for line in consistent_lines 
#                                  if not (line.replace('|', '').replace('-', '').replace(':', '').strip() == '')]
                    
#                     if len(data_lines) >= 2:
#                         # Parse headers from first line
#                         headers = [h.strip() for h in data_lines[0].split('|') if h.strip()]
                        
#                         # If we have reasonable headers, proceed with data extraction
#                         if len(headers) >= 2:
#                             data = []
#                             for line in data_lines[1:]:
#                                 # Split by pipe and clean up each cell
#                                 cells = [cell.strip() for cell in line.split('|')]
#                                 # Remove empty elements at start/end if they exist (from leading/trailing pipes)
#                                 if cells and not cells[0]: cells = cells[1:]
#                                 if cells and not cells[-1]: cells = cells[:-1]
                                
#                                 if cells:
#                                     # Ensure rows match header length
#                                     while len(cells) < len(headers):
#                                         cells.append("(Uncategorized)")
#                                     # Truncate if too long
#                                     cells = cells[:len(headers)]
#                                     data.append(cells)
                            
#                             if data:
#                                 df = pd.DataFrame(data, columns=headers)
#                                 return standardize_output_format(df)
        
#         # Check for HTML tables
#         if '<table' in text and '</table>' in text:
#             try:
#                 # Use pandas to parse HTML tables
#                 dfs = pd.read_html(text)
#                # print("gfdddff: ",dfs)
#                 if dfs and len(dfs) > 0:
#                     return standardize_output_format(dfs[0])
#             except Exception as html_err:
#                 print(f"HTML table parsing error: {html_err}")
        
#         # Fall back to checking for tabular patterns in plain text
#         if '\n' in text:
#             lines = [line.strip() for line in text.split('\n') if line.strip()]
#             if len(lines) >= 3:  # Need header, separator, and at least one data row
#                 # Check if there's a consistent pattern of data alignment
#                 # First look for spaces or common separators
#                 potential_delimiters = ['\t', '  ', ',', ';']
                
#                 for delimiter in potential_delimiters:
#                     if any(delimiter in line for line in lines[:3]):
#                         try:
#                             # Try parsing with this delimiter
#                             headers = [h.strip() for h in re.split(r'\s{2,}|\t|,|;', lines[0]) if h.strip()]
#                             if len(headers) >= 2:
#                                 data = []
#                                 for line in lines[1:]:
#                                     # Skip separator lines
#                                     if re.match(r'^[-+:|\s]+$', line):
#                                         continue
                                    
#                                     cells = [c.strip() for c in re.split(r'\s{2,}|\t|,|;', line) if c.strip()]
#                                     if len(cells) >= len(headers) * 0.7:  # Allow some flexibility
#                                         # Pad or truncate as needed
#                                         while len(cells) < len(headers):
#                                             cells.append("(Uncategorized)")
#                                         cells = cells[:len(headers)]
#                                         data.append(cells)
                                
#                                 if data:
#                                     df = pd.DataFrame(data, columns=headers)
#                                     return standardize_output_format(df)
#                         except Exception as delim_err:
#                             print(f"Delimiter parsing error: {delim_err}")
#                             continue
        
#         return None
#     except Exception as e:
#         print(f"Error extracting DataFrame: {e}")
#         return None

# @data_router.post("/clear_chat/")
# async def clear_chat(current_user: dict = Depends(get_current_user)):
#     """Clear entire chat history"""
#     global CHAT_HISTORY
    
#     # Check if user is admin for additional permissions
#     if current_user["role"] == "admin":
#         CHAT_HISTORY = []
#         return {"message": "Chat history cleared successfully."}
#     else:
#         # For non-admin users, only clear their own chat history
#         CHAT_HISTORY = [entry for entry in CHAT_HISTORY if entry.get("user") != current_user["username"]]
#         return {"message": f"Chat history for user {current_user['username']} cleared successfully."}

# # Include both routers in the main app
# app.include_router(auth_router)
# app.include_router(data_router)

# if __name__ == "__main__":
#     # uvicorn.run(app, host="localhost", port=8000)
#     # uvicorn.run(app, host="10.61.24.68", port=8000)
#     uvicorn.run(app, host="localhost", port=8000)



#########################################################################################################################
#Azure uploaded main.py file


# from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
# from pydantic import BaseModel
# from typing import List, Dict
# from datetime import datetime, timedelta
# import jwt
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# import pandas as pd
# import os
# from dotenv import load_dotenv
# from openai import OpenAI
# from langchain_community.chat_models import ChatOpenAI
# from langchain.agents.agent_types import AgentType
# from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
# from fastapi.middleware.cors import CORSMiddleware
# import warnings
# import data_schema_1
# import uvicorn
# import json
# import io
# import re
# import promptGuide
# import instructions

# # Suppress specific warnings
# warnings.filterwarnings('ignore', category=UserWarning)
# warnings.filterwarnings('ignore', category=DeprecationWarning)

# # Load environment variables
# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# app = FastAPI(title="Data Analysis API")
# DATA_SCHEMA = data_schema_1.DATA_SCHEMA
# DATA = None  # Global variable to store the dataset
# CHAT_HISTORY = []  # Global variable to store chat history
# MAX_HISTORY_LENGTH = 5  # Limit chat history length

# # Authentication configuration
# SECRET_KEY = "your_secret_key_here"
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 60

# # Dummy users database
# dummy_users = [
#     {"username": "testadmin", "password": "Admin@777", "role": "admin"},
#     {"username": "testuser", "password": "User@777", "role": "user"},
#     {"username": "testuser1", "password": "User@111", "role": "user"},
#     {"username": "testuser2", "password": "User@222", "role": "user"},
#     {"username": "testuser3", "password": "User@333", "role": "user"},
# ]

# # OAuth2 scheme for token authentication
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# # CORS middleware setup
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Change this to the actual path of your CSV file
# # BASE_DIR = os.getenv("APP_STORAGE_PATH", "/home/site/wwwroot")
 
# # Set the CSV file path dynamically
# # CSV_FILE_PATH = os.path.join(BASE_DIR, "COPQ_ANALYTICS", "data.csv")
# CSV_FILE_PATH = r"Warranty-Aperture for After 2025.csv"  #latest may6

# # User Schema
# class User(BaseModel):
#     username: str
#     password: str
#     role: str

# # Token Schema
# class Token(BaseModel):
#     access_token: str
#     token_type: str

# # Query Request Schema
# class QueryRequest(BaseModel):
#     query: str

# # Helper Function: Authenticate User
# def authenticate_user(username: str, password: str):
#     for user in dummy_users:
#         if user["username"] == username and user["password"] == password:
#             return user
#     return None

# # Helper Function: Create JWT Token
# def create_access_token(data: dict, expires_delta: timedelta = None):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# # Helper Function: Get Current User
# def get_current_user(token: str = Depends(oauth2_scheme)):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username = payload.get("sub")
#         role = payload.get("role")
#         if username is None:
#             raise HTTPException(status_code=401, detail="Invalid token")
#         return {"username": username, "role": role}
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token expired")
#     except jwt.InvalidTokenError:
#         raise HTTPException(status_code=401, detail="Invalid token")

# def robust_dataframe_conversion(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Enhanced robust DataFrame type conversion with consistent null handling
#     """
#     df = df.copy()
    
#     for col in df.columns:
#         try:
#             # Try to convert to numeric first, coercing errors
#             df[col] = pd.to_numeric(df[col], errors='ignore')
#         except:
#             pass
    
#     # Specific schema-based conversions
#     for schema_field in DATA_SCHEMA:
#         col_name = schema_field['field']
#         expected_type = schema_field['type']

#         if col_name in df.columns:
#             try:
#                 if expected_type == 'string':
#                     # Convert to string, handling NaN values with "(uncategorized)"
#                     df[col_name] = df[col_name].astype(str)
#                     df[col_name] = df[col_name].replace(['nan', 'None', '', 'NaN', 'null'], '(Uncategorized)')
                
#                 elif expected_type == 'integer':
#                     # More robust integer conversion - use 0 for nulls
#                     df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
#                     df[col_name] = df[col_name].fillna(0).astype('int64')
                
#                 elif expected_type == 'float':
#                     # Convert to float, coercing errors
#                     df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
#                     df[col_name] = df[col_name].fillna(0.0)
                
#                 elif expected_type == 'date':
#                     # More flexible date parsing
#                     df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
            
#             except Exception as e:
#                 print(f"Warning: Could not convert column {col_name}. Error: {e}")
#                 continue

#     return df

# def load_data():
#     """
#     Enhanced data loading with more robust error handling
#     """
#     global DATA
#     if os.path.exists(CSV_FILE_PATH):
#         try:
#             # Use more flexible CSV reading
#             df = pd.read_csv(
#                 CSV_FILE_PATH, 
#                 encoding="ISO-8859-1", 
#                 low_memory=False,
#                 dtype_backend='pyarrow'
#             )
            
#             # Robust conversion
#             DATA = robust_dataframe_conversion(df)
            
#             # Additional data validation
#             print(f"Dataset loaded successfully. Shape: {DATA.shape}")
#             print("Available columns:", list(DATA.columns))
            
#             # Print unique years if Date column exists
#             if 'Date' in DATA.columns:
#                 years = DATA['Date'].dt.year.unique()
#                 print("Years in dataset:", sorted(years))
            
#             return True
#         except Exception as e:
#             print(f"Error loading dataset: {e}")
#             return False
#     else:
#         print("Error: CSV file not found at the specified path.")
#         return False

# def dataframe_to_html_table(df):
#     """
#     Convert a pandas DataFrame to a styled HTML table with consistent null handling
#     """
#     if df is None or df.empty:
#         return "<p>No data available</p>"
    
#     try:
#         # Apply standardized formatting
#         df = standardize_output_format(df)
        
#         # Apply styling to the HTML table
#         table_html = df.to_html(
#             index=False, 
#             classes="table table-striped table-hover table-bordered", 
#             border=1,
#             escape=False,
#             na_rep="0"
#         )
        
#         # Add custom styling
#         styled_table = f"""
#         <div class="table-responsive">
#         \n\n\n{table_html}\n\n
#         </div>
#         """
#         return styled_table
#     except Exception as e:
#         print(f"Error creating HTML table: {e}")
#         return f"<p>Error generating table: {str(e)}</p>"

# def combine_table_html(table_html, title="Data Analysis Results"):
#     """
#     Format table HTML into a single HTML page
#     """
#     combined_html = f"""
#     <div class="analysis-container">
#         <h2>{title}</h2>
#         <div class="table-container">
#             <h3>Data Table</h3>
#             {table_html}
#         </div>
#     </div>
#     """
#     return combined_html

# def extract_dataframe_from_text(text):
#     """
#     Enhanced function to extract table-like data from text response and convert to DataFrame
#     With improved detection to handle various table formats
#     """
#     try:
#         # Check if the response contains structured table data
#         if '|' in text and '\n' in text:
#             # Try to parse markdown table with more lenient approach
#             lines = [line.strip() for line in text.split('\n') if line.strip()]
            
#             # Look for lines with pipe characters (potential table rows)
#             table_lines = [line for line in lines if '|' in line]
            
#             if len(table_lines) >= 2:  # Need at least header and one data row
#                 # Find the most common pipe count to handle inconsistent formatting
#                 pipe_counts = [line.count('|') for line in table_lines]
#                 most_common_count = max(set(pipe_counts), key=pipe_counts.count)
                
#                 # Filter lines to those with the most common pipe count (Â± 1 to allow minor variations)
#                 consistent_lines = [line for line, count in zip(table_lines, pipe_counts) 
#                                    if abs(count - most_common_count) <= 1]
                
#                 if len(consistent_lines) >= 2:  # Still need at least header and one data row
#                     # Skip separator rows (those with mostly dashes)
#                     data_lines = [line for line in consistent_lines 
#                                  if not (line.replace('|', '').replace('-', '').replace(':', '').strip() == '')]
                    
#                     if len(data_lines) >= 2:
#                         # Parse headers from first line
#                         headers = [h.strip() for h in data_lines[0].split('|') if h.strip()]
                        
#                         # If we have reasonable headers, proceed with data extraction
#                         if len(headers) >= 2:
#                             data = []
#                             for line in data_lines[1:]:
#                                 # Split by pipe and clean up each cell
#                                 cells = [cell.strip() for cell in line.split('|')]
#                                 # Remove empty elements at start/end if they exist
#                                 if cells and not cells[0]: cells = cells[1:]
#                                 if cells and not cells[-1]: cells = cells[:-1]
                                
#                                 if cells:
#                                     # Ensure rows match header length
#                                     while len(cells) < len(headers):
#                                         cells.append("(Uncategorized)")
#                                     # Truncate if too long
#                                     cells = cells[:len(headers)]
#                                     data.append(cells)
                            
#                             if data:
#                                 df = pd.DataFrame(data, columns=headers)
#                                 return standardize_output_format(df)
        
#         # Check for HTML tables
#         if '<table' in text and '</table>' in text:
#             try:
#                 # Use pandas to parse HTML tables
#                 dfs = pd.read_html(text)
#                 if dfs and len(dfs) > 0:
#                     return standardize_output_format(dfs[0])
#             except Exception as html_err:
#                 print(f"HTML table parsing error: {html_err}")
        
#         # Fall back to checking for tabular patterns in plain text
#         if '\n' in text:
#             lines =  [line.strip() for line in text.split('\n') if line.strip()]
#             if len(lines) >= 3:  # Need header, separator, and at least one data row
#                 # Check for consistent pattern of data alignment
#                 potential_delimiters = ['\t', '  ', ',', ';']
                
#                 for delimiter in potential_delimiters:
#                     if any(delimiter in line for line in lines[:3]):
#                         try:
#                             # Try parsing with this delimiter
#                             headers = [h.strip() for h in re.split(r'\s{2,}|\t|,|;', lines[0]) if h.strip()]
#                             if len(headers) >= 2:
#                                 data = []
#                                 for line in lines[1:]:
#                                     # Skip separator lines
#                                     if re.match(r'^[-+:|\s]+$', line):
#                                         continue
                                    
#                                     cells = [c.strip() for c in re.split(r'\s{2,}|\t|,|;', line) if c.strip()]
#                                     if len(cells) >= len(headers) * 0.7:  # Allow some flexibility
#                                         # Pad or truncate as needed
#                                         while len(cells) < len(headers):
#                                             cells.append("(Uncategorized)")
#                                         cells = cells[:len(headers)]
#                                         data.append(cells)
                                
#                                 if data:
#                                     df = pd.DataFrame(data, columns=headers)
#                                     return standardize_output_format(df)
#                         except Exception as delim_err:
#                             print(f"Delimiter parsing error: {delim_err}")
#                             continue
        
#         return None
#     except Exception as e:
#         print(f"Error extracting DataFrame: {e}")
#         return None

# def standardize_output_format(df):
#     """
#     Standardize DataFrame output formatting with consistent null handling
#     """
#     formatted_df = df.copy()
    
#     for col in formatted_df.columns:
#         is_numeric = pd.api.types.is_numeric_dtype(formatted_df[col])
        
#         if is_numeric:
#             formatted_df[col] = formatted_df[col].fillna(0)
#         else:
#             formatted_df[col] = formatted_df[col].fillna("(Uncategorized)")
#             formatted_df[col] = formatted_df[col].astype(str)
#             formatted_df[col] = formatted_df[col].replace(['nan', 'None', '', 'NaN', 'null', '<NA>'], '(Uncategorized)')
    
#     return formatted_df

# def is_list_response(text):
#     """
#     Determine if the response appears to be a list of items rather than tabular data
#     """
#     list_indicators = [
#         text.count("\n1.") > 0,
#         text.count("\n- ") > 1,
#         text.count("\n* ") > 1,
#         text.count("\nâ€¢") > 1,
#         bool(re.search(r'\n\d+\.\s+', text)),
#         bool(re.search(r'Top \d+ ', text)) and text.count("\n") > 2,
#         bool(re.search(r'(\n\s*([A-Za-z0-9][\)\.:]|\d+[\)\.:])\s+)', text))
#     ]
    
#     list_keywords = [
#         'list', 'top', 'questions', 'reasons', 'factors', 'steps',
#         'best', 'worst', 'highest', 'lowest', 'most common',
#         'frequently', 'commonly', 'popular', 'tips', 'advice', 'suggestions'
#     ]
    
#     contains_list_keywords = any(keyword in text.lower() for keyword in list_keywords)
    
#     return any(list_indicators) or (contains_list_keywords and text.count("\n") > 2)

# # Call load_data during startup
# load_data()

# # Create routers for each group
# auth_router = APIRouter(tags=["Auth"])
# data_router = APIRouter(tags=["data-analysis"])

# # Authentication Endpoints
# @auth_router.post("/login", response_model=Token)
# async def login(form_data: OAuth2PasswordRequestForm = Depends()):
#     user = authenticate_user(form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token = create_access_token({"sub": user["username"], "role": user["role"]})
#     return {"access_token": access_token, "token_type": "bearer"}

# @auth_router.get("/me")
# async def read_current_user(current_user: dict = Depends(get_current_user)):
#     return current_user

# @auth_router.post("/register", response_model=User)
# async def register(user: User):
#     for existing_user in dummy_users:
#         if existing_user["username"] == user.username:
#             raise HTTPException(status_code=400, detail="Username already exists")
#     new_user = {"username": user.username, "password": user.password, "role": user.role}
#     dummy_users.append(new_user)
#     return new_user

# @auth_router.post("/logout")
# async def logout():
#     return {"message": "Logout successful. Remove token on frontend."}

# @data_router.post("/query/")
# async def query_data(request: QueryRequest, current_user: dict = Depends(get_current_user)):
#     global DATA, CHAT_HISTORY
#     if DATA is None:
#         if not load_data():
#             raise HTTPException(status_code=400, detail="No data loaded.")
    
#     query = request.query
    
#     is_list_request = any(keyword in query.lower() for keyword in [
#         'list', 'top', 'questions', 'reasons', 'factors', 'steps',
#         'best', 'worst', 'highest', 'lowest', 'most common',
#         'frequently', 'commonly', 'popular', 'tips', 'advice', 'suggestions'
#     ])
    
#     is_time_comparison = any(term in query.lower() for term in [
#         'yoy', 'mom', 'year over year', 'month over month', 'yearly', 'monthly',
#         'compared to last', 'previous year', 'previous month', 'comparison',
#         'trend', 'performance over time', 'change since', 'growth'
#     ])
    
#     print(f"Query received from user: {current_user['username']} with role: {current_user['role']}")
#     print(f"Is this likely a list request? {is_list_request}")
#     print(f"Is this likely a time comparison? {is_time_comparison}")

#     if not OPENAI_API_KEY:
#         raise HTTPException(status_code=500, detail="OpenAI API key is missing")

#     final_result = ""
#     html_table = ""

#     def ensure_text_summary(response_text, result_df, query, is_time_comparison=False):
#         """Ensures that a proper text summary exists without table formatting"""
#         lines = response_text.strip().split('\n')
        
#         summary_lines = []
#         for line in lines:
#             if '|' in line and '-' in line:
#                 break
#             if not line.strip().startswith('|'):
#                 summary_lines.append(line)
        
#         summary_text = '\n'.join(summary_lines).strip()
        
#         if (not summary_text or len(summary_text) < 40) and result_df is not None and not result_df.empty:
#             try:
#                 time_cols = [col for col in result_df.columns if col.lower() in [
#                     'year', 'month', 'date', 'period', 'quarter', 'time', 'week'
#                 ]]
                
#                 summary_parts = []
                
#                 if is_time_comparison and time_cols:
#                     time_col = time_cols[0]
#                     time_periods = sorted(result_df[time_col].unique())
                    
#                     if len(time_periods) >= 2:
#                         numeric_cols = [col for col in result_df.columns 
#                                       if col not in time_cols and 
#                                       col.lower() not in ['difference in %', '% change', 'percent', 'percentage'] and
#                                       pd.api.types.is_numeric_dtype(result_df[col])]
                        
#                         for col in numeric_cols[:3]:
#                             try:
#                                 if len(time_periods) == 2:
#                                     val1 = result_df[result_df[time_col] == time_periods[0]][col].iloc[0]
#                                     val2 = result_df[result_df[time_col] == time_periods[1]][col].iloc[0]
                                    
#                                     if val1 != 0:
#                                         pct_change = ((val2 - val1) / val1) * 100
#                                         direction = "increased" if pct_change > 0 else "decreased"
#                                         summary_parts.append(f"{col} {direction} by {abs(pct_change):.1f}% from {time_periods[0]} to {time_periods[1]}")
#                             except:
#                                 continue
                
#                 if not summary_parts:
#                     try:
#                         numeric_cols = [col for col in result_df.columns 
#                                        if pd.api.types.is_numeric_dtype(result_df[col])]
                        
#                         if numeric_cols:
#                             max_col = max(numeric_cols, key=lambda col: result_df[max_col].max())
#                             max_row_idx = result_df[max_col].idxmax()
#                             max_row = result_df.iloc[max_row_idx]
                            
#                             max_value = max_row[max_col]
#                             id_col = next((col for col in result_df.columns 
#                                           if col.lower() in ['name', 'id', 'category', 'type', 'description']), 
#                                           result_df.columns[0])
                            
#                             id_value = max_row[id_col]
#                             summary_parts.append(f"The highest {max_col} is {max_value:,.2f} for {id_value}.")
#                     except:
#                         pass
                
#                 if summary_parts:
#                     if len(summary_parts) > 1:
#                         summary = f"{summary_parts[0]} {summary_parts[1]}"
#                     else:
#                         summary = summary_parts[0]
                        
#                     summary += f" This analysis is based on {len(result_df)} data points."
#                 else:
#                     summary = f"Analysis of {query} based on {len(result_df)} data points. "
                    
#                     if is_time_comparison and time_cols:
#                         time_col = time_cols[0]
#                         time_periods = sorted(result_df[time_col].unique())
#                         if len(time_periods) >= 2:
#                             summary += f"Comparing {time_periods[0]} to {time_periods[-1]}, "
                    
#                     if len(result_df.columns) > 1:
#                         main_cols = [col for col in result_df.columns if col not in ['% Change_Cost', '% Change_Units']][:3]
#                         summary += f"The data shows values for {', '.join(main_cols)}."
                
#                 return summary
                    
#             except Exception as e:
#                 print(f"Error generating summary: {e}")
        
#         return summary_text if summary_text else "Analysis of the requested data:"

#     try:
#         agent = create_pandas_dataframe_agent(
#             ChatOpenAI(
#                 temperature=0, 
#                 model="gpt-4o-mini", 
#                 api_key=OPENAI_API_KEY
#             ),
#             DATA,
#             verbose=True,
#             agent_type=AgentType.OPENAI_FUNCTIONS,
#             allow_dangerous_code=True
#         )
        
#         context = "\n".join([f"Previous User Query: {entry['query']}\nPrevious Bot Response: {entry['response']}" for entry in CHAT_HISTORY[-MAX_HISTORY_LENGTH:]])
        
#         if is_list_request:
#             query_format = "Your response should be formatted as a concise numbered list preceded by a brief introduction, NOT as a table."
#         elif is_time_comparison:
#             query_format = "This is a time comparison query. Begin with a 2-4 sentence text summary highlighting the key changes, THEN show a properly formatted markdown table with a percentage change column."
#         else:
#             query_format = "If showing complex data, include a 2-4 sentence description followed by a properly formatted markdown table with proper header and separator rows."
        
#         refined_query = f"""Considering previous conversation context:
# {context}

# Important instructions: {instructions.formatting_instruction}
# Format note: {query_format}

# New Query: {query}

# Please follow these steps in your analysis :
#         1. First, understand what specific aspects of complaints data are relevant to the question
#         2. Identify which fields from the data schema would be most useful for this analysis
#         3. Consider any data quality issues that might affect the analysis (missing values, date format inconsistencies, etc.)
#         4. Determine appropriate analytical techniques (time series analysis, clustering, correlation, etc.)
#         5. Think through how you would calculate or estimate key metrics needed
#         6. Interpret what the results would mean in the context of customer complaints and business impact
#         7. Provide a clear final answer with actionable insights
       
# Remember: For tables, ALWAYS START with a 2-4 sentence text summary BEFORE the table explaining key findings.
# For time-based comparisons (YoY, MoM), ALWAYS include percentage changes with + or - prefixes.
# For lists of items (like "top N" questions), use a simple numbered list format, not a table.
# For tabular data, use proper markdown table format with | separators, header row, and separator row with dashes.
# """
        
#         res = agent.invoke(refined_query)
        
#         response_text = (
#             res.get("output") if isinstance(res, dict) else 
#             str(res) if res else 
#             "Could not find a definitive answer to your question."
#         )
        
#         response_text = response_text.replace(" (blank)", " (Uncategorized)")
#         response_text = response_text.replace(" (null)", " (Uncategorized)")
#         response_text = response_text.replace(" (empty)", " (Uncategorized)")
#         response_text = response_text.replace("Blank: ", "(Uncategorized): ")
#         response_text = response_text.replace("Empty: ", "(Uncategorized): ")
#         response_text = response_text.replace("Null: ", "(Uncategorized): ")
#         response_text = response_text.replace("NA: ", "(Uncategorized): ")
#         response_text = response_text.replace("<NA>", "(Uncategorized)")
        
#         is_list_response_result = is_list_response(response_text)
        
#         has_table = '|' in response_text and '\n' in response_text and '-' in response_text
        
#         is_short_response = len(response_text.split('\n')) < 3 and len(response_text) < 300 and not has_table
        
#         result_df = None
#         if not is_short_response:
#             result_df = extract_dataframe_from_text(response_text)
            
#             if result_df is not None:
#                 print(f"Successfully extracted DataFrame with shape: {result_df.shape}")
#             else:
#                 print("Failed to extract DataFrame")
        
#         if result_df is not None and not result_df.empty:
#             result_df = standardize_output_format(result_df)
            
#             print(result_df.to_string(index=False))
            
#             text_summary = ensure_text_summary(response_text, result_df, query, is_time_comparison)
            
#             html_table = dataframe_to_html_table(result_df)
#             final_table = remove_newlines_replace(html_table)
#             final_result = replace_between_pipe_and_I(response_text, "\n" + final_table + "\n")
            
#             CHAT_HISTORY.append({
#                 "query": query,
#                 "response": text_summary,
#                 "user": current_user["username"]
#             })
            
#             if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#                 CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            
#             # return {
#             #     "response": final_result,
#             #     "html_content": combine_table_html(html_table, text_summary)
#             # }
#             return {
#                 "response": final_result
#             }
#         else:
#             if has_table and '|' in response_text:
#                 print("Attempting fallback table parsing for response with pipe characters")
                
#                 cleaned_text = re.sub(r'\n\s*\n', '\n', response_text)
                
#                 lines = [line.strip() for line in cleaned_text.split('\n') if '|' in line.strip()]
                
#                 if len(lines) >= 2:
#                     header_line = lines[0]
#                     header_cells = [cell.strip() for cell in header_line.split('|') if cell.strip()]
                    
#                     if header_cells:
#                         data_rows = []
#                         for line in lines[1:]:
#                             if re.match(r'^[\s\-\+\|:]*$', line):
#                                 continue
                            
#                             cells = [cell.strip() for cell in line.split('|') if cell]
                            
#                             if cells:
#                                 while len(cells) < len(header_cells):
#                                     cells.append("(Uncategorized)")
                                    
#                                 if len(cells) > len(header_cells):
#                                     cells = cells[:len(header_cells)]
                                    
#                                 data_rows.append(cells)
                        
#                         if data_rows:
#                             manual_df = pd.DataFrame(data_rows, columns=header_cells)
#                             manual_df = standardize_output_format(manual_df)
                            
#                             text_summary = ensure_text_summary(response_text, manual_df, query, is_time_comparison)
                            
#                             html_table = dataframe_to_html_table(manual_df)
                            
#                             print("Generated HTML table content (fallback method)")
                            
#                             CHAT_HISTORY.append({
#                                 "query": query,
#                                 "response": text_summary,
#                                 "user": current_user["username"]
#                             })
                            
#                             if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#                                 CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
                            
#                             return {
#                                 "response": text_summary,
#                                 "html_content": combine_table_html(html_table, text_summary)
#                             }
            
#             CHAT_HISTORY.append({
#                 "query": query,
#                 "response": response_text,
#                 "user": current_user["username"]
#             })
            
#             if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
#                 CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            
#             final_result = final_result if final_result != "" else response_text

#             return {
#                 "response": final_result,
#                 # "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
#             }
    
#     except Exception as e:
#         print(f"Query processing error: {e}")
#         return {
#             "response": f"An error occurred during query processing: {str(e)}",
#             # "prompt_guide": promptGuide.QUERY_PROMPT_GUIDE
#         }

# def replace_between_pipe_and_I(text, replacement):
#     start = text.find('|')
#     end = text.rfind('|')
#     if start != -1 and end != -1 and start < end:
#         return text[:start] + replacement + text[end+1:]
#     return text

# def remove_newlines_replace(text):
#     return text.replace('\n', '')

# @data_router.post("/clear_chat/")
# async def clear_chat(current_user: dict = Depends(get_current_user)):
#     """Clear entire chat history"""
#     global CHAT_HISTORY
    
#     if current_user["role"] == "admin":
#         CHAT_HISTORY = []
#         return {"message": "Chat history cleared successfully."}
#     else:
#         CHAT_HISTORY = [entry for entry in CHAT_HISTORY if entry.get("user") != current_user["username"]]
#         return {"message": f"Chat history for user {current_user['username']} cleared successfully."}

# # Include both routers in the main app
# app.include_router(auth_router)
# app.include_router(data_router)

# if __name__ == "__main__":
#     uvicorn.run(app, host="localhost", port=8000)
