from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
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
from fastapi.middleware.cors import CORSMiddleware
import warnings
import data_schema_1
import uvicorn
import json
import io
import re
import promptGuide
import instructions




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

# OAuth2 scheme for token authentication
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
# CSV_FILE_PATH = r"Warranty_Apertures_After2023 Latest Data.csv"
CSV_FILE_PATH = r"Warranty-Aperture for After 2025.csv"  #latest may6
# CSV_FILE_PATH = r"anonymized_sampled_data.csv"

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

def check_single_image(folder_path):
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    
    files = os.listdir(folder_path)
    images = [f for f in files if os.path.splitext(f)[1].lower() in image_extensions]

    return len(images) == 1

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
                    df[col_name] = df[col_name].replace(['nan', 'None', '', 'NaN', 'null'], '(Uncategorized)')
                
                elif expected_type == 'integer':
                    # More robust integer conversion - use 0 for nulls
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                    df[col_name] = df[col_name].fillna(0).astype('int64')
                
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
                dtype_backend='pyarrow'
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
        # Apply standardized formatting
        df = standardize_output_format(df)
        
        # Apply styling to the HTML table
        table_html = df.to_html(
            index=False, 
            classes="table table-striped table-hover table-bordered", 
            border=1,
            escape=False,
            na_rep="0"
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

def combine_table_html(table_html, title="Data Analysis Results"):
    """
    Format table HTML into a single HTML page
    """
    combined_html = f"""
    <div class="analysis-container">
        <h2>{title}</h2>
        <div class="table-container">
            <h3>Data Table</h3>
            {table_html}
        </div>
    </div>
    """
    return combined_html

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

def standardize_output_format(df):
    """
    Standardize DataFrame output formatting with consistent null handling
    """
    formatted_df = df.copy()
    
    for col in formatted_df.columns:
        is_numeric = pd.api.types.is_numeric_dtype(formatted_df[col])
        
        if is_numeric:
            formatted_df[col] = formatted_df[col].fillna(0)
        else:
            formatted_df[col] = formatted_df[col].fillna("(Uncategorized)")
            formatted_df[col] = formatted_df[col].astype(str)
            formatted_df[col] = formatted_df[col].replace(['nan', 'None', '', 'NaN', 'null', '<NA>'], '(Uncategorized)')
    
    return formatted_df

import os
import base64

def get_single_image_base64(folder_path):
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    
    files = os.listdir(folder_path)
    images = [f for f in files if os.path.splitext(f)[1].lower() in image_extensions]

    if len(images) == 1:
        image_path = os.path.join(folder_path, images[0])
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        
        # html = '<div><image src ="data:image/png;base64,{encoded}</div>'
        
        return True,encoded
    else:
        return False,None
    
def empty_folder(folder_path):
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"{folder_path} is not a valid directory")

    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)

    print(f"✅ Emptied folder: {folder_path}")

def is_list_response(text):
    """
    Determine if the response appears to be a list of items rather than tabular data
    """
    list_indicators = [
        text.count("\n1.") > 0,
        text.count("\n- ") > 1,
        text.count("\n* ") > 1,
        text.count("\n•") > 1,
        bool(re.search(r'\n\d+\.\s+', text)),
        bool(re.search(r'Top \d+ ', text)) and text.count("\n") > 2,
        bool(re.search(r'(\n\s*([A-Za-z0-9][\)\.:]|\d+[\)\.:])\s+)', text))
    ]
    
    list_keywords = [
        'list', 'top', 'questions', 'reasons', 'factors', 'steps',
        'best', 'worst', 'highest', 'lowest', 'most common',
        'frequently', 'commonly', 'popular', 'tips', 'advice', 'suggestions'
    ]
    
    contains_list_keywords = any(keyword in text.lower() for keyword in list_keywords)
    
    return any(list_indicators) or (contains_list_keywords and text.count("\n") > 2)

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

@data_router.post("/query/")
async def query_data(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    global DATA, CHAT_HISTORY
    if DATA is None:
        if not load_data():
            raise HTTPException(status_code=400, detail="No data loaded.")
    
    query = request.query
    
    is_list_request = any(keyword in query.lower() for keyword in [
        'list', 'top', 'questions', 'reasons', 'factors', 'steps',
        'best', 'worst', 'highest', 'lowest', 'most common',
        'frequently', 'commonly', 'popular', 'tips', 'advice', 'suggestions'
    ])
    
    is_time_comparison = any(term in query.lower() for term in [
        'yoy', 'mom', 'year over year', 'month over month', 'yearly', 'monthly',
        'compared to last', 'previous year', 'previous month', 'comparison',
        'trend', 'performance over time', 'change since', 'growth'
    ])
    
    print(f"Query received from user: {current_user['username']} with role: {current_user['role']}")
    print(f"Is this likely a list request? {is_list_request}")
    print(f"Is this likely a time comparison? {is_time_comparison}")

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key is missing")

    final_result = ""
    html_table = ""

    def ensure_text_summary(response_text, result_df, query, is_time_comparison=False):
        """Ensures that a proper text summary exists without table formatting"""
        lines = response_text.strip().split('\n')
        
        summary_lines = []
        for line in lines:
            if '|' in line and '-' in line:
                break
            if not line.strip().startswith('|'):
                summary_lines.append(line)
        
        summary_text = '\n'.join(summary_lines).strip()
        
        if (not summary_text or len(summary_text) < 40) and result_df is not None and not result_df.empty:
            try:
                time_cols = [col for col in result_df.columns if col.lower() in [
                    'year', 'month', 'date', 'period', 'quarter', 'time', 'week'
                ]]
                
                summary_parts = []
                
                if is_time_comparison and time_cols:
                    time_col = time_cols[0]
                    time_periods = sorted(result_df[time_col].unique())
                    
                    if len(time_periods) >= 2:
                        numeric_cols = [col for col in result_df.columns 
                                      if col not in time_cols and 
                                      col.lower() not in ['difference in %', '% change', 'percent', 'percentage'] and
                                      pd.api.types.is_numeric_dtype(result_df[col])]
                        
                        for col in numeric_cols[:3]:
                            try:
                                if len(time_periods) == 2:
                                    val1 = result_df[result_df[time_col] == time_periods[0]][col].iloc[0]
                                    val2 = result_df[result_df[time_col] == time_periods[1]][col].iloc[0]
                                    
                                    if val1 != 0:
                                        pct_change = ((val2 - val1) / val1) * 100
                                        direction = "increased" if pct_change > 0 else "decreased"
                                        summary_parts.append(f"{col} {direction} by {abs(pct_change):.1f}% from {time_periods[0]} to {time_periods[1]}")
                            except:
                                continue
                
                if not summary_parts:
                    try:
                        numeric_cols = [col for col in result_df.columns 
                                       if pd.api.types.is_numeric_dtype(result_df[col])]
                        
                        if numeric_cols:
                            max_col = max(numeric_cols, key=lambda col: result_df[max_col].max())
                            max_row_idx = result_df[max_col].idxmax()
                            max_row = result_df.iloc[max_row_idx]
                            
                            max_value = max_row[max_col]
                            id_col = next((col for col in result_df.columns 
                                          if col.lower() in ['name', 'id', 'category', 'type', 'description']), 
                                          result_df.columns[0])
                            
                            id_value = max_row[id_col]
                            summary_parts.append(f"The highest {max_col} is {max_value:,.2f} for {id_value}.")
                    except:
                        pass
                
                if summary_parts:
                    if len(summary_parts) > 1:
                        summary = f"{summary_parts[0]} {summary_parts[1]}"
                    else:
                        summary = summary_parts[0]
                        
                    summary += f" This analysis is based on {len(result_df)} data points."
                else:
                    summary = f"Analysis of {query} based on {len(result_df)} data points. "
                    
                    if is_time_comparison and time_cols:
                        time_col = time_cols[0]
                        time_periods = sorted(result_df[time_col].unique())
                        if len(time_periods) >= 2:
                            summary += f"Comparing {time_periods[0]} to {time_periods[-1]}, "
                    
                    if len(result_df.columns) > 1:
                        main_cols = [col for col in result_df.columns if col not in ['% Change_Cost', '% Change_Units']][:3]
                        summary += f"The data shows values for {', '.join(main_cols)}."
                
                return summary
                    
            except Exception as e:
                print(f"Error generating summary: {e}")
        
        return summary_text if summary_text else "Analysis of the requested data:"

    try:
        agent = create_pandas_dataframe_agent(
            ChatOpenAI(
                temperature=0, 
                model="gpt-4o-mini", 
                api_key=OPENAI_API_KEY
            ),
            DATA,
            verbose=True,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            allow_dangerous_code=True
        )
        
        context = "\n".join([f"Previous User Query: {entry['query']}\nPrevious Bot Response: {entry['response']}" for entry in CHAT_HISTORY[-MAX_HISTORY_LENGTH:]])
        
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

Please follow these steps in your analysis :
        1. First, understand what specific aspects of complaints data are relevant to the question
        2. Identify which fields from the data schema would be most useful for this analysis
        3. Consider any data quality issues that might affect the analysis (missing values, date format inconsistencies, etc.)
        4. Determine appropriate analytical techniques (time series analysis, clustering, correlation, etc.)
        5. Think through how you would calculate or estimate key metrics needed
        6. Interpret what the results would mean in the context of customer complaints and business impact
        7. Provide a clear final answer with actionable insights
       
Remember: For tables, ALWAYS START with a 2-4 sentence text summary BEFORE the table explaining key findings.
For time-based comparisons (YoY, MoM), ALWAYS include percentage changes with + or - prefixes.
For lists of items (like "top N" questions), use a simple numbered list format, not a table.
For tabular data, use proper markdown table format with | separators, header row, and separator row with dashes.

IMPORTANT NOTE:
"IF YOU ARE GENERATING ANY CHART PLEASE STORE IN images directory"
"DO NOT SHOW THE GENERATED GRAPH"
"""
        
        res = agent.invoke(refined_query)
        print("Type of graph :",type(res))
        response_text = (
            res.get("output") if isinstance(res, dict) else 
            str(res) if res else 
            "Could not find a definitive answer to your question."
        )
        
        response_text = response_text.replace(" (blank)", " (Uncategorized)")
        response_text = response_text.replace(" (null)", " (Uncategorized)")
        response_text = response_text.replace(" (empty)", " (Uncategorized)")
        response_text = response_text.replace("Blank: ", "(Uncategorized): ")
        response_text = response_text.replace("Empty: ", "(Uncategorized): ")
        response_text = response_text.replace("Null: ", "(Uncategorized): ")
        response_text = response_text.replace("NA: ", "(Uncategorized): ")
        response_text = response_text.replace("<NA>", "(Uncategorized)")
        
        is_list_response_result = is_list_response(response_text)
        
        has_table = '|' in response_text and '\n' in response_text and '-' in response_text
        
        is_short_response = len(response_text.split('\n')) < 3 and len(response_text) < 300 and not has_table
        
        result_df = None
        if not is_short_response:
            result_df = extract_dataframe_from_text(response_text)
            
            if result_df is not None:
                print(f"Successfully extracted DataFrame with shape: {result_df.shape}")
            else:
                print("Failed to extract DataFrame")
        
        if result_df is not None and not result_df.empty:
            result_df = standardize_output_format(result_df)
            
            print(result_df.to_string(index=False))
            
            text_summary = ensure_text_summary(response_text, result_df, query, is_time_comparison)
            
            html_table = dataframe_to_html_table(result_df)
            final_table = remove_newlines_replace(html_table)
            final_result = replace_between_pipe_and_I(response_text, "\n" + final_table + "\n")
            
            CHAT_HISTORY.append({
                "query": query,
                "response": text_summary,
                "user": current_user["username"]
            })
            
            if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
                CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            
            # return {
            #     "response": final_result,
            #     "html_content": combine_table_html(html_table, text_summary)
            # }
            is_image,image_file=get_single_image_base64("images")
            empty_folder("images")    ###khali krne ka def
            # final_result = final_result + image_file 
            return {
                "response": final_result,
                "is_images":is_image,
                "image_file":image_file
            }
        else:
            if has_table and '|' in response_text:
                print("Attempting fallback table parsing for response with pipe characters")
                
                cleaned_text = re.sub(r'\n\s*\n', '\n', response_text)
                
                lines = [line.strip() for line in cleaned_text.split('\n') if '|' in line.strip()]
                
                if len(lines) >= 2:
                    header_line = lines[0]
                    header_cells = [cell.strip() for cell in header_line.split('|') if cell.strip()]
                    
                    if header_cells:
                        data_rows = []
                        for line in lines[1:]:
                            if re.match(r'^[\s\-\+\|:]*$', line):
                                continue
                            
                            cells = [cell.strip() for cell in line.split('|') if cell]
                            
                            if cells:
                                while len(cells) < len(header_cells):
                                    cells.append("(Uncategorized)")
                                    
                                if len(cells) > len(header_cells):
                                    cells = cells[:len(header_cells)]
                                    
                                data_rows.append(cells)
                        
                        if data_rows:
                            manual_df = pd.DataFrame(data_rows, columns=header_cells)
                            manual_df = standardize_output_format(manual_df)
                            
                            text_summary = ensure_text_summary(response_text, manual_df, query, is_time_comparison)
                            
                            html_table = dataframe_to_html_table(manual_df)
                            
                            print("Generated HTML table content (fallback method)")
                            
                            CHAT_HISTORY.append({
                                "query": query,
                                "response": text_summary,
                                "user": current_user["username"]
                            })
                            
                            if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
                                CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
                            
                            return {
                                "response": text_summary,
                                "html_content": combine_table_html(html_table, text_summary)
                            }
            
            CHAT_HISTORY.append({
                "query": query,
                "response": response_text,
                "user": current_user["username"]
            })
            
            if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
                CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            
            final_result = final_result if final_result != "" else response_text
            is_image,image_file=get_single_image_base64("images")
            empty_folder("images")

            return {
                "response": final_result,
                "is_images":is_image,
                "image_file":image_file
            }

           
    
    except Exception as e:
        print(f"Query processing error: {e}")
        return {
            "response": f"An error occurred during query processing: {str(e)}"
        }

def replace_between_pipe_and_I(text, replacement):
    start = text.find('|')
    end = text.rfind('|')
    if start != -1 and end != -1 and start < end:
        return text[:start] + replacement + text[end+1:]
    return text

def remove_newlines_replace(text):
    return text.replace('\n', '')

@data_router.post("/clear_chat/")
async def clear_chat(current_user: dict = Depends(get_current_user)):
    """Clear entire chat history"""
    global CHAT_HISTORY
    
    if current_user["role"] == "admin":
        CHAT_HISTORY = []
        return {"message": "Chat history cleared successfully."}
    else:
        CHAT_HISTORY = [entry for entry in CHAT_HISTORY if entry.get("user") != current_user["username"]]
        return {"message": f"Chat history for user {current_user['username']} cleared successfully."}

# Include both routers in the main app
app.include_router(auth_router)
app.include_router(data_router)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)