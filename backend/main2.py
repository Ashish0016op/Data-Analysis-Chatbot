from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Dict
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
import instructions
import promptGuide


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
CSV_FILE_PATH = r"Warranty_Apertures_After2023 Latest Data.csv"  # Change this to the actual path of your CSV file
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



def check_uncategorized_percentage(df):
    """
    Check what percentage of the DataFrame contains uncategorized values
    Returns the percentage and a boolean indicating if it's too high for visualization
    """
    total_cells = df.size
    uncategorized_count = 0
    
    for col in df.columns:
        # Count uncategorized values based on column type
        if pd.api.types.is_numeric_dtype(df[col]):
            # For numeric columns, count NaN values (we will replace these with 0)
            uncategorized_count += df[col].isna().sum()
        else:
            # For non-numeric columns, check for various empty/null representations
            uncategorized_count += df[col].apply(lambda x: 
                1 if pd.isna(x) or str(x).lower() in ['nan', 'none', '', 'uncategorized', '(uncategorized)', 'null'] 
                else 0).sum()
    
    percentage = (uncategorized_count / total_cells) * 100 if total_cells > 0 else 0
    # If more than 30% of data is uncategorized, avoid visualization
    return percentage, percentage > 30


def generate_plotly_chart(df, query):
    """
    Generate a Plotly chart based on the DataFrame and query content
    """
    try:
        # Check for too many uncategorized values
        uncategorized_percentage, too_many_uncategorized = check_uncategorized_percentage(df)
        
        if too_many_uncategorized:
            return f"""
            <div class="alert alert-warning">
                <h4>Visualization Not Recommended</h4>
                <p>The data contains {uncategorized_percentage:.1f}% uncategorized values, which would result in a misleading chart. 
                Please refer to the table for details.</p>
            </div>
            """
      

        bar_chart_keywords = [
            "bar", "bar chart", "compare", "trend", "comparison", "highest", "lowest",
            "top", "bottom", "ranking", "grouped", "by category",
            "categorical distribution", "side by side","over time",
             "time series", "progression",
            "monthly", "yearly", "daily", "weekly", "timeline",
            "growth", "decline", "pattern", "change", "evolution"
        ]

        line_chart_keywords =["line", "line chart"]
        # line_chart_keywords=[]

        pie_chart_keywords = [
            "pie", "pie chart", "proportion", "percentage", "percent", "share",
            "distribution", "contribution", "part of whole", "split"
        ]

        histogram_keywords = [
            "histogram", "distribution", "frequency", "bins", "intervals",
            "range", "spread", "count", "how often"
        ]

        scatter_plot_keywords = [
            "scatter", "scatter plot", "correlation", "relationship", "association",
            "x vs y", "two variables", "points", "distribution of points", "dependency"
        ]

        # --- Determine chart type based on keywords ---
        query_lower = query.lower()
        chart_type = "unknown"

        
        if any(term in query_lower for term in pie_chart_keywords):
            chart_type = "pie"
        elif any(term in query_lower for term in scatter_plot_keywords):
            chart_type = "scatter"
        elif any(term in query_lower for term in histogram_keywords):
            chart_type = "histogram"
        elif any(term in query_lower for term in bar_chart_keywords):
            chart_type = "bar"
        elif any(term in query_lower for term in line_chart_keywords):
            chart_type = "line"
        else:
            # Default to bar for categorical data, line for time series, or bar as general fallback
            categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower() or 'year' in col.lower() or 'month' in col.lower()]
            
            if date_cols and numeric_cols:
                chart_type = "line"  # Time-series data
            elif categorical_cols and numeric_cols:
                chart_type = "bar"   # Categorical data
            else:
                chart_type = "bar"   # Default fallback

        # --- Identify X and Y columns ---
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()

        if len(df.columns) >= 2:
            x_col = categorical_cols[0] if categorical_cols else df.columns[0]
            y_col = numeric_cols[0] if numeric_cols else df.columns[1]

            # --- Create chart based on type ---
            chart_title = f"{chart_type.capitalize()} Chart: {y_col} by {x_col}"
            
            if chart_type == "bar":
                fig = px.bar(df, x=x_col, y=y_col, title=chart_title)
            elif chart_type == "line":
                fig = px.line(df, x=x_col, y=y_col, title=chart_title)
            elif chart_type == "pie":
                fig = px.pie(df, names=x_col, values=y_col, title=chart_title)
            elif chart_type == "scatter":
                fig = px.scatter(df, x=x_col, y=y_col, title=chart_title)
            elif chart_type == "histogram":
                fig = px.histogram(df, x=y_col, title=f"Histogram of {y_col}")
            else:
                return "<p>Could not determine a suitable chart type from the query.</p>"

            # --- Update layout ---
            fig.update_layout(
                template="plotly_white",
                margin=dict(l=40, r=40, t=40, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            # --- Convert to HTML ---
            chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
            # Update chart formatting
         
            
            # Add a header to clearly identify the chart type
            chart_with_header = f"""
            <div class="chart-container">
                <h4>Visualization Type: {chart_type.capitalize()} Chart</h4>
                {chart_html}
            </div>
            """
            return chart_with_header
        else:
            return "<p>Insufficient data for visualization</p>"
    except Exception as e:
        print(f"Error generating chart: {e}")
        return f"<p>Error generating visualization: {str(e)}</p>"


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
                                # Remove empty elements at start/end if they exist
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
                if dfs and len(dfs) > 0:
                    return standardize_output_format(dfs[0])
            except Exception as html_err:
                print(f"HTML table parsing error: {html_err}")
        
        # Fall back to checking for tabular patterns in plain text
        if '\n' in text:
            lines =  [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) >= 3:  # Need header, separator, and at least one data row
                # Check for consistent pattern of data alignment
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
    # Create a deep copy to avoid modifying the original
    formatted_df = df.copy()
    
    # Ensure consistent handling of null/NA values
    for col in formatted_df.columns:
        # Check if the column is numeric
        is_numeric = pd.api.types.is_numeric_dtype(formatted_df[col])
        
        if is_numeric:
            # For numeric columns, replace nulls with 0 (not -1)
            formatted_df[col] = formatted_df[col].fillna(0)
        else:
            # For non-numeric columns, replace nulls with "(Uncategorized)"
            formatted_df[col] = formatted_df[col].fillna("(Uncategorized)")
            # Convert objects like pandas NA to string "(Uncategorized)"
            formatted_df[col] = formatted_df[col].astype(str)
            formatted_df[col] = formatted_df[col].replace(['nan', 'None', '', 'NaN', 'null', '<NA>'], '(Uncategorized)')
    
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
    
    # Special case for greetings or simple queries
    greeting_keywords = ["hi", "hello", "hey", "greetings", "howdy", "good morning", "good afternoon", "good evening"]
    
    if query.lower() in greeting_keywords or len(query.split()) <= 3:
        greeting_response = f"Hello {current_user['username']}! I'm your data analysis assistant. You can ask me questions about your warranty data, such as 'What are the top problem codes by cost?' or 'Show me warranty trends by business unit'. How can I help you analyze your data today?"
        
        # Store in chat history
        CHAT_HISTORY.append({
            "query": query,
            "response": greeting_response,
            "user": current_user["username"]
        })
        
        # Trim if needed
        if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
            CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
        
        return {
            "response": greeting_response
        }
    
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

    # Enhanced Prompt Guide
    QUERY_PROMPT_GUIDE=promptGuide.QUERY_PROMPT_GUIDE
#     QUERY_PROMPT_GUIDE = """# 📊 DATA-DRIVEN INSIGHTS ANALYSIS FRAMEWORK

# ## Cost of Poor Quality (COPQ) Analysis
# - Comprehensive metrics for quality issue tracking
# - Warranty claims tracking across business units
# - Root cause identification for recurring issues
# - Customer impact assessment and cost distribution analysis
# - Understand short names for BUSINESS_UNIT, BRAND, and PLANT
# - Detect anomalies in cost, defects, and data integrity
# - Standardize and clean input data for accurate analysis
# - Provide insights on patterns and recurring issues

# ## STRICT DATA ACCURACY REQUIREMENTS
# - ALL analysis MUST be grounded exclusively in the available dataset
# - NEVER make assumptions about data not present in the dataset
# - ALWAYS specify data limitations that affect the accuracy of analysis
# - When requested analysis requires unavailable data, clearly state "This analysis cannot be performed with the available data"
# - ALL metrics and conclusions MUST cite specific data points from the dataset

# ## MANDATORY HANDLING OF YEAR-OVER-YEAR (YoY) AND MONTH-OVER-MONTH (MoM) ANALYSES
# - For ANY query mentioning time comparisons or containing terms like "YoY", "MoM", "year over year", "month over month", "compared to last month/year", or similar:
#   * ALWAYS begin with a 2-4 sentence text summary highlighting key findings BEFORE presenting any table
#   * ALWAYS include a "% Change" column in every output table 
#   * Format positive changes with "+" prefix (e.g., "+15.2%") and negative changes with "-" prefix (e.g., "-8.7%")
#   * For minimal/no change, use "+0.0%" format
#   * For YoY: Calculate as ((Current Year Value - Previous Year Value) / Previous Year Value) * 100
#   * For MoM: Calculate as ((Current Month Value - Previous Month Value) / Previous Month Value) * 100
#   * Include the most significant positive and negative changes in your summary
#   * Handle cases with zero divisors (previous value = 0) by reporting as "N/A" or "New" rather than infinity

# ## RESPONSE CONSISTENCY REQUIREMENTS
# - Maintain consistent response format for similar query types across sessions
# - Use standardized numerical precision: 2 decimal places for percentages, whole numbers for counts
# - Standardize output format for similar query categories (e.g., cost analysis, frequency analysis)
# - For recurring query types, use the same column order and naming conventions
# - When reporting changes, consistently use the same calculation methodology

# ## TEXT SUMMARY REQUIREMENTS
# - For any table-based results, ALWAYS include a concise text summary (2-4 sentences) BEFORE the table
# - This summary is REQUIRED for all data presentations, especially YoY and MoM analyses
# - Highlight the most significant findings or patterns in the summary
# - Mention the largest positive and negative changes (for YoY/MoM analyses) with percentages
# - Address any data limitations or caveats in the summary
# - For YoY comparisons, always calculate and mention the percentage difference between years
# - For MoM comparisons, always calculate and mention the percentage difference between months
# - Explain the meaning of the data, not just state what the numbers are

# ## CALCULATION AND METHODOLOGY
# - Provide calculations or details after each result or response
# - Show formulas used for all calculated metrics
# - For statistical analyses, specify the exact methodology and parameters
# - Include sample sizes in all statistical reporting

# ## ADVANCED ANALYTICAL APPROACHES

# ## Time-Series Analysis
# - For "Month over Month" analysis:
#   * Compare ONLY months with complete data
#   * Calculate precise percentage changes between consecutive months
#   * Use weighted averages when appropriate for partial months
#   * Report exact counts/costs rather than approximations
#   * Show full data table with monthly progression
#   * Include statistical significance of observed changes
#   * Always include a text summary highlighting the key trends (min 2-3 sentences)

# ## BRAND SHORT NAME MAPPINGS
# - sim = Simonton
# - pg = PlyGem
# - eas = EAS
# - sl = Silverline
# - atr = Atrium

# ## PLANT SHORT NAME MAPPINGS
# - RC = Ritchie County
# - SLC = Salt Lake City
# - LS = Lithia Springs
# - NB = North Brunswick
# - TX = Dallas

# ## QUERY CAPABILITIES
# - Natural language processing for complex analytical questions
# - Multi-dimension filtering by business unit, problem code, and date
# - Trend analysis across time periods and issue categories
# - Statistical breakdowns of cost centers and problem frequencies

# ## IMPORTANT ACCURACY REQUIREMENTS
# - Match exact values from the dataset without approximations
# - Report precise figures without rounding unless specifically requested
# - When searching for specific terms, ensure EXACT matches (not partial or similar)
# - Treat all searches as case-sensitive by default
# - When a term isn't found, try alternative case variations (toLowerCase, toUpperCase, titleCase)
# - Report when case variations have been attempted if no match is found
# - Be precise with terminology - "Warranty Cost" is not the same as "Warranty Costs"
# - If a specific term isn't found, suggest the closest matching term from the dataset
# - For ambiguous queries, request clarification on exact terminology
# - Verify column names and values exist in the dataset before attempting analysis
# - When no data is found, clearly state this rather than providing approximate results
# - For multi-part queries, validate each component independently

# ## POWER QUERY EXAMPLES

# ### Business Intelligence
# - "Summarize total warranty costs by business unit"
# - "What are the top 5 most expensive problem types?"
# - "Compare warranty vs. non-warranty costs across business units"
# - "Which customers have the highest number of quality issues?"

# ## Issue Analysis
# - "Analyze frequency and cost of estimating errors"
# - "What percentage of issues are classified as production errors?"
# - "Find orders with multiple problem codes"
# - "Calculate average cost per issue type"

# ## Cost Analysis
# - "Total cost impact of shipping errors"
# - "What's the average cost of installation errors?"
# - "Rank problem codes by total cost"
# - "Identify the highest cost issues for Ryan Homes"

# ## Operational Insights
# - "Calculate the frequency of 'No RFM' complaints"
# - "Show issues by manufacturing plant location"
# - "Which product lines have the most quality issues?"
# - "What percentage of orders include warranty costs?"

# ## QUERY OPTIMIZATION TIPS
# - Be specific about time periods when relevant
# - Reference column names for more precise results
# - Combine filters for targeted analysis (e.g., "estimating errors for Ryan Homes")
# - Request calculations like averages, percentages, or totals
# - Use keywords like "analyze," "compare," "summarize," or "rank"

# ## PARAMETER MATCHING INTELLIGENCE
# - Case-insensitive recognition of all parameters (e.g., "WARRANTY", "warranty", or "Warranty" all match)
# - Common abbreviation support for frequently used terms:
#   - "BU" → "Business Unit"
#   - "WC" → "Warranty Costs"
#   - "NWC" → "Non-Warranty Costs"
#   - "PC" → "Problem Code"
#   - "COPQ" → "Cost of Poor Quality"
#   - "RFM" → "Request For Modification"
#   - "QI" → "Quality Issues"
#   - "CIP" → "Cost Impact"
#   - "RC" → "Root Cause"
#   - "AP" → "Apertures Solution, Apertures solution -US"
# - Mixed format detection for partial matches (e.g., "Bus Unit" will match "Business Unit")
# - Parameter aliases recognized across all queries (e.g., "errors", "issues", "problems" treated as related)

# ## INTELLIGENT DATE HANDLING
# - Multi-year dataset with flexible querying
# - Specify years, months, or use broad terms
# - Natural language date interpretation

# ## Performance Analysis
# - "Compare Aperture business performance June 2023 vs June 2024 using exact metrics"
# - "Show month-over-month quality metrics for Simonton brand with statistical significance"
# - "Which plants showed statistically significant improvement in defect rates based on 2023-2024 data?"

# ## ANALYTICAL METHOD REQUIREMENTS
# - Show your reasoning steps for all calculations
# - Cite specific data values from the dataset when making claims
# - Present analysis limitations based on data quality or availability
# - Provide statistical context when appropriate (variance, confidence)
# - Report sample sizes used in all calculations
# - Use appropriate statistical tests for comparisons
# - Always present numerical evidence alongside conclusions

# ## CODE EXECUTION REQUIREMENTS
# - Always define variables before using them in a function or lambda expression
# - When performing calculations, ensure all variables are defined in the same execution context
# - Use complete code blocks that handle all necessary variable definitions
# - Avoid referencing undefined variables or functions

# IMPORTANT NOTES:
# - Empty or null values in categorical fields are labeled as "(Uncategorized)"
# """
    
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
        
        # Enhanced formatting instruction with improved table guidance
        formatting_instruction=instructions.formatting_instruction
#         formatting_instruction = """
# Important: When formatting your response:

# 1. For tables and complex data:
#    - Format tables as proper markdown tables with | separators
#    - ALWAYS include the header row
#    - For ANY data presentation, especially YoY/MoM comparisons, START with a 2-4 sentence text summary BEFORE the table
#    - Align columns properly for readability
#    - Make sure every cell has some value (use "(Uncategorized)" for empty values)
#    - For YoY/MoM analyses, ALWAYS include a "% Change" column with + or - prefix

# 2. For lists (top N items, questions, suggestions, etc.):
#    - Format as a regular numbered or bulleted list
#    - DO NOT use table format for lists of items
#    - Include a brief introduction before the list
#    - For "Top N" types of queries, use a numbered list format (1., 2., 3., etc.)

# 3. For simple answers:
#    - Respond in plain text with 1-2 sentences
#    - Do not use table formatting for simple answers

# 4. For time-based comparisons (YoY, MoM):
#    - ALWAYS start with a 2-4 sentence summary highlighting key findings
#    - ALWAYS include percentage changes with + or - prefixes
#    - Format positive changes as "+XX.X%" and negative changes as "-XX.X%"
#    - Mention the most significant changes in your summary
   
# 5. Data handling:
#    - Always report empty or null values as "(Uncategorized)" in results
#    - Include "(Uncategorized)" entries in counts, summaries, and statistics
#    - Do not exclude empty/null values from analysis unless specifically requested
   
# 6. Output consistency:
#    - Format must be identical in both terminal logs and API responses
#    - Replace <NA> values with "(Uncategorized)" in output
#    - When the response includes a mathematical calculation, mark it as 0 instead of 'Uncategorized'
#    - If NaN appears in the numerical calculations of the response, or if any new columns are created with NaN values, replace them with 0.
#    - If the percentage change calculation results in NaN or undefined, replace it with 0% instead of labeling it as 'Uncategorized'
# """
        
        # Customize the query format based on the request type
        if is_list_request:
            query_format = "Your response should be formatted as a concise numbered list preceded by a brief introduction, NOT as a table."
        elif is_time_comparison:
            query_format = "This is a time comparison query. Begin with a 2-4 sentence text summary highlighting the key changes, THEN show a properly formatted markdown table with a percentage change column."
        else:
            query_format = "If showing complex data, include a 2-4 sentence description followed by a properly formatted markdown table with proper header and separator rows."
        
        refined_query = f"""Considering previous conversation context:
{context}

Important formatting instructions: {formatting_instruction}
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
                    print("\nVisualization DataFrame (Terminal Output):")
                    print(visualization_df.to_string(index=False))
                    
                    # Generate chart HTML
                    print("visualization_df ************** > >",visualization_df)
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
                        "prompt_guide": QUERY_PROMPT_GUIDE
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
            # print("\n\nfinal_result: ", final_result)
            # print("\n\nchart_html: ",chart_html)

            print("Generated HTML table content")
            
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
                                "prompt_guide": QUERY_PROMPT_GUIDE
                            }
            
            # If still no DataFrame, just return the text response
            print("\nText Response (Terminal Output):")
            print(response_text)
            
            # Store chat history with user information
            CHAT_HISTORY.append({
                "query": query,
                "response": response_text,
                "user": current_user["username"]
            })
            
            # Trim chat history if it exceeds max length
            if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
                CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            
            return {
                "response": final_result,
                "prompt_guide": QUERY_PROMPT_GUIDE
            }
    
    except Exception as e:
        print(f"Query processing error: {e}")
        return {
            "response": f"An error occurred during query processing: {str(e)}",
            "prompt_guide": QUERY_PROMPT_GUIDE
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
    uvicorn.run(app, host="localhost", port=8000)