import matplotlib
matplotlib.use('Agg')  # CRITICAL: Must be before any other matplotlib/pyplot import
import matplotlib.pyplot as plt
import seaborn as sns

from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Literal
from datetime import datetime, timedelta
import jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import pandas as pd
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from fastapi.middleware.cors import CORSMiddleware
import warnings
import data_schema_1
import uvicorn
import json
import io
import re
import hashlib
import hmac
import promptGuide
import instructions
import base64
import secrets
import time
import threading
from collections import deque
from pymongo.errors import DuplicateKeyError, PyMongoError
from db import (
    close_mongo_connection,
    ensure_mongo_schema,
    get_mongo_status,
    ping_mongo,
    users_collection,
)


# Suppress specific warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Load environment variables
load_dotenv()

# ─────────────────────────────────────────────
# Gemini Configuration (Native endpoint)
# Model : gemma-2-27b-it  (Gemma 4 31B)
# Limits: RPM=15 | TPM=Unlimited | RPD=1500
# ─────────────────────────────────────────────
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

ACTIVE_API_KEY  = GEMINI_API_KEY
ACTIVE_MODEL    = GEMINI_MODEL

print(f"Using native Gemini endpoint | model: {ACTIVE_MODEL}")

# ─────────────────────────────────────────────
# Rate-Limit Guard
# Hard limits : RPM=15  | RPD=1500
# Safe targets: RPM=14  | RPD=1400  (buffer of 1 / 100)
#
# Strategy
#   • Sliding 60-second deque tracks per-minute usage
#   • Date-stamped counter tracks daily usage
#   • If RPM limit hit  → sleep until oldest entry
#     in the window is >60 s old, then proceed
#   • If RPD limit hit  → raise HTTP 429 immediately
# ─────────────────────────────────────────────

RATE_LIMIT_RPM = 14     # stay 1 below hard cap
RATE_LIMIT_RPD = 1400   # stay 100 below hard cap

_rate_lock        = threading.Lock()
_minute_window    = deque()           # monotonic timestamps of last N requests
_daily_count      = 0
_daily_reset_date = datetime.utcnow().date()


def _rate_limit_check():
    """
    Call BEFORE every LLM invocation.
    Blocks (sleeps) if RPM limit is reached.
    Raises HTTP 429 if RPD limit is reached.
    """
    global _daily_count, _daily_reset_date

    with _rate_lock:
        now   = time.monotonic()
        today = datetime.utcnow().date()

        # ── Reset daily counter at UTC midnight ──
        if today != _daily_reset_date:
            _daily_count      = 0
            _daily_reset_date = today
            _minute_window.clear()
            print("[RateLimit] Daily counter reset.")

        # ── RPD hard stop ──
        if _daily_count >= RATE_LIMIT_RPD:
            print(f"[RateLimit] Daily limit reached ({_daily_count}/{RATE_LIMIT_RPD})")
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily request limit reached ({RATE_LIMIT_RPD} requests). "
                    "Resets at UTC midnight."
                )
            )

        # ── Evict stale entries from the sliding window ──
        while _minute_window and now - _minute_window[0] > 60.0:
            _minute_window.popleft()

        # ── RPM throttle: sleep until window clears ──
        if len(_minute_window) >= RATE_LIMIT_RPM:
            oldest    = _minute_window[0]
            sleep_for = 60.0 - (now - oldest) + 0.5   # +0.5 s safety buffer
            print(f"[RateLimit] RPM limit hit — sleeping {sleep_for:.1f}s ...")
            _rate_lock.release()
            time.sleep(sleep_for)
            _rate_lock.acquire()
            # Re-evict after waking
            now = time.monotonic()
            while _minute_window and now - _minute_window[0] > 60.0:
                _minute_window.popleft()

        # ── Register this request ──
        _minute_window.append(time.monotonic())
        _daily_count += 1
        print(
            f"[RateLimit] OK — "
            f"RPM window: {len(_minute_window)}/{RATE_LIMIT_RPM} | "
            f"RPD: {_daily_count}/{RATE_LIMIT_RPD}"
        )


def _get_llm(temperature: float = 0) -> ChatGoogleGenerativeAI:
    """
    Central factory for all LLM instances.
    Always calls _rate_limit_check() before returning the client
    so every invocation is guarded automatically.
    """
    _rate_limit_check()
    return ChatGoogleGenerativeAI(
        temperature=temperature,
        model=ACTIVE_MODEL,
        google_api_key=ACTIVE_API_KEY,
    )


app = FastAPI(title="Data Analysis API")
DATA_SCHEMA = data_schema_1.DATA_SCHEMA
DATA = None           # global dataset
CHAT_HISTORY = []     # global chat history
MAX_HISTORY_LENGTH = 5


@app.on_event("startup")
async def startup_event():
    if await ping_mongo(raise_on_error=False):
        await ensure_mongo_schema()


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()


@app.get("/mongo-health")
async def mongo_health():
    connected = await ping_mongo(raise_on_error=False)
    status_code = "connected" if connected else "unavailable"
    return {"status": status_code, **get_mongo_status()}

# Authentication
SECRET_KEY               = "your_secret_key_here"
ALGORITHM                = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
PASSWORD_HASH_ITERATIONS = 260_000

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_FILE_PATH  = r"Warranty-Aperture for After 2025.csv"
IMAGES_FOLDER  = "images"
os.makedirs(IMAGES_FOLDER, exist_ok=True)


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────

class UserRegister(BaseModel):
    email: str = Field(..., min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=4, max_length=128)
    role: Literal["user"] = "user"

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value

class UserResponse(BaseModel):
    email: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str

class QueryRequest(BaseModel):
    query: str


# ─────────────────────────────────────────────
# Auth Helpers
# ─────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_digest = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(actual_digest, expected_digest)
    except (TypeError, ValueError):
        return False


async def authenticate_user(email: str, password: str):
    user = await users_collection.find_one({"email": email.strip().lower()})
    if not user:
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload   = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email     = payload.get("sub")
        role      = payload.get("role")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await users_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="User no longer exists")
        return {"email": user["email"], "role": user.get("role", role or "user")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except PyMongoError:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable")


# ─────────────────────────────────────────────
# Image Helpers
# ─────────────────────────────────────────────

def get_single_image_base64(folder_path: str):
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    try:
        files = os.listdir(folder_path)
    except FileNotFoundError:
        return False, None

    images = [f for f in files if os.path.splitext(f)[1].lower() in image_extensions]
    if images:
        image_path = os.path.join(folder_path, images[0])
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        return True, encoded
    return False, None


def get_all_images_base64(folder_path: str) -> list:
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    try:
        files = os.listdir(folder_path)
    except FileNotFoundError:
        return []

    images = sorted([f for f in files if os.path.splitext(f)[1].lower() in image_extensions])
    encoded_images = []
    for img in images:
        image_path = os.path.join(folder_path, img)
        try:
            with open(image_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                encoded_images.append(encoded)
        except Exception as e:
            print(f"Error reading image {img}: {e}")
    return encoded_images



def empty_folder(folder_path: str):
    if not os.path.isdir(folder_path):
        return
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)
    print(f"Emptied folder: {folder_path}")


# ─────────────────────────────────────────────
# Data Loading & Conversion
# ─────────────────────────────────────────────

def robust_dataframe_conversion(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col], errors='ignore')
        except Exception:
            pass

    for schema_field in DATA_SCHEMA:
        col_name      = schema_field['field']
        expected_type = schema_field['type']
        if col_name not in df.columns:
            continue
        try:
            if expected_type == 'string':
                df[col_name] = df[col_name].astype(str).replace(
                    ['nan', 'None', '', 'NaN', 'null'], '(Uncategorized)'
                )
            elif expected_type == 'integer':
                df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(0).astype('int64')
            elif expected_type == 'float':
                df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(0.0)
            elif expected_type == 'date':
                df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
        except Exception as e:
            print(f"Warning: Could not convert column {col_name}. Error: {e}")
    return df


def load_data():
    global DATA
    if os.path.exists(CSV_FILE_PATH):
        try:
            df   = pd.read_csv(CSV_FILE_PATH, encoding="ISO-8859-1", low_memory=False, dtype_backend='pyarrow')
            DATA = robust_dataframe_conversion(df)
            print(f"Dataset loaded. Shape: {DATA.shape}")
            print("Columns:", list(DATA.columns))
            if 'Date' in DATA.columns:
                print("Years:", sorted(DATA['Date'].dt.year.unique()))
            return True
        except Exception as e:
            print(f"Error loading dataset: {e}")
            return False
    else:
        print("Error: CSV file not found.")
        return False


# ─────────────────────────────────────────────
# Output Formatting Helpers
# ─────────────────────────────────────────────

def standardize_output_format(df: pd.DataFrame) -> pd.DataFrame:
    formatted_df = df.copy()
    for col in formatted_df.columns:
        if pd.api.types.is_numeric_dtype(formatted_df[col]):
            formatted_df[col] = formatted_df[col].fillna(0)
        else:
            formatted_df[col] = (
                formatted_df[col]
                .fillna("(Uncategorized)")
                .astype(str)
                .replace(['nan', 'None', '', 'NaN', 'null', '<NA>'], '(Uncategorized)')
            )
    return formatted_df


def dataframe_to_html_table(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "<p>No data available</p>"
    try:
        df = standardize_output_format(df)
        table_html = df.to_html(
            index=False,
            classes="table table-striped table-hover table-bordered",
            border=1, escape=False, na_rep="0"
        )
        return f'<div class="table-responsive">\n\n\n{table_html}\n\n</div>'
    except Exception as e:
        return f"<p>Error generating table: {str(e)}</p>"


def combine_table_html(table_html: str, title: str = "Data Analysis Results") -> str:
    return f"""
    <div class="analysis-container">
        <h2>{title}</h2>
        <div class="table-container">
            <h3>Data Table</h3>
            {table_html}
        </div>
    </div>
    """


def remove_newlines_replace(text: str) -> str:
    return text.replace('\n', '')


def replace_between_pipe_and_I(text: str, replacement: str) -> str:
    start = text.find('|')
    end   = text.rfind('|')
    if start != -1 and end != -1 and start < end:
        return text[:start] + replacement + text[end + 1:]
    return text


# ─────────────────────────────────────────────
# DataFrame Extraction from Text
# ─────────────────────────────────────────────

def extract_dataframe_from_text(text: str):
    try:
        if '|' in text and '\n' in text:
            lines      = [line.strip() for line in text.split('\n') if line.strip()]
            table_lines = [line for line in lines if '|' in line]
            if len(table_lines) >= 2:
                pipe_counts       = [line.count('|') for line in table_lines]
                most_common_count = max(set(pipe_counts), key=pipe_counts.count)
                consistent_lines  = [
                    line for line, count in zip(table_lines, pipe_counts)
                    if abs(count - most_common_count) <= 1
                ]
                if len(consistent_lines) >= 2:
                    data_lines = [
                        line for line in consistent_lines
                        if line.replace('|', '').replace('-', '').replace(':', '').strip()
                    ]
                    if len(data_lines) >= 2:
                        headers = [h.strip() for h in data_lines[0].split('|') if h.strip()]
                        if len(headers) >= 2:
                            data = []
                            for line in data_lines[1:]:
                                cells = [cell.strip() for cell in line.split('|')]
                                if cells and not cells[0]:  cells = cells[1:]
                                if cells and not cells[-1]: cells = cells[:-1]
                                if cells:
                                    while len(cells) < len(headers): cells.append("(Uncategorized)")
                                    data.append(cells[:len(headers)])
                            if data:
                                return standardize_output_format(pd.DataFrame(data, columns=headers))

        if '<table' in text and '</table>' in text:
            try:
                dfs = pd.read_html(text)
                if dfs: return standardize_output_format(dfs[0])
            except Exception: pass

        if '\n' in text:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) >= 3:
                for delimiter in ['\t', '  ', ',', ';']:
                    if any(delimiter in line for line in lines[:3]):
                        try:
                            headers = [h.strip() for h in re.split(r'\s{2,}|\t|,|;', lines[0]) if h.strip()]
                            if len(headers) >= 2:
                                data = []
                                for line in lines[1:]:
                                    if re.match(r'^[-+:|\s]+$', line): continue
                                    cells = [c.strip() for c in re.split(r'\s{2,}|\t|,|;', line) if c.strip()]
                                    if len(cells) >= len(headers) * 0.7:
                                        while len(cells) < len(headers): cells.append("(Uncategorized)")
                                        data.append(cells[:len(headers)])
                                if data:
                                    return standardize_output_format(pd.DataFrame(data, columns=headers))
                        except Exception: continue
        return None
    except Exception as e:
        print(f"Error extracting DataFrame: {e}")
        return None


# ─────────────────────────────────────────────
# List Detection
# ─────────────────────────────────────────────

def is_list_response(text: str) -> bool:
    list_indicators = [
        text.count("\n1.") > 0, text.count("\n- ") > 1,
        text.count("\n* ") > 1, text.count("\n•") > 1,
        bool(re.search(r'\n\d+\.\s+', text)),
        bool(re.search(r'Top \d+ ', text)) and text.count("\n") > 2,
        bool(re.search(r'(\n\s*([A-Za-z0-9][\)\.:]|\d+[\)\.:])\s+)', text))
    ]
    list_keywords = [
        'list', 'top', 'questions', 'reasons', 'factors', 'steps',
        'best', 'worst', 'highest', 'lowest', 'most common',
        'frequently', 'commonly', 'popular', 'tips', 'advice', 'suggestions'
    ]
    return any(list_indicators) or (
        any(k in text.lower() for k in list_keywords) and text.count("\n") > 2
    )


# ─────────────────────────────────────────────
# Text Summary Helpers
# ─────────────────────────────────────────────

def ensure_text_summary(response_text: str, result_df, query: str, is_time_comparison: bool = False) -> str:
    lines         = response_text.strip().split('\n')
    summary_lines = []
    for line in lines:
        if '|' in line and '-' in line: break
        if not line.strip().startswith('|'):
            summary_lines.append(line)
    summary_text = '\n'.join(summary_lines).strip()

    if (not summary_text or len(summary_text) < 40) and result_df is not None and not result_df.empty:
        try:
            time_cols     = [c for c in result_df.columns if c.lower() in ['year','month','date','period','quarter','time','week']]
            summary_parts = []

            if is_time_comparison and time_cols:
                time_col     = time_cols[0]
                time_periods = sorted(result_df[time_col].unique())
                if len(time_periods) >= 2:
                    numeric_cols = [
                        c for c in result_df.columns
                        if c not in time_cols
                        and c.lower() not in ['difference in %', '% change', 'percent', 'percentage']
                        and pd.api.types.is_numeric_dtype(result_df[c])
                    ]
                    for col in numeric_cols[:3]:
                        try:
                            if len(time_periods) == 2:
                                v1 = result_df[result_df[time_col] == time_periods[0]][col].iloc[0]
                                v2 = result_df[result_df[time_col] == time_periods[1]][col].iloc[0]
                                if v1 != 0:
                                    pct   = ((v2 - v1) / v1) * 100
                                    dirn  = "increased" if pct > 0 else "decreased"
                                    summary_parts.append(
                                        f"{col} {dirn} by {abs(pct):.1f}% from {time_periods[0]} to {time_periods[1]}"
                                    )
                        except Exception: continue

            if not summary_parts:
                numeric_cols = [c for c in result_df.columns if pd.api.types.is_numeric_dtype(result_df[c])]
                if numeric_cols:
                    max_col     = max(numeric_cols, key=lambda c: result_df[c].max())
                    max_row     = result_df.iloc[result_df[max_col].idxmax()]
                    id_col      = next((c for c in result_df.columns if c.lower() in ['name','id','category','type','description']), result_df.columns[0])
                    summary_parts.append(f"The highest {max_col} is {max_row[max_col]:,.2f} for {max_row[id_col]}.")

            if summary_parts:
                summary = summary_parts[0]
                if len(summary_parts) > 1: summary += f" {summary_parts[1]}"
                summary += f" This analysis is based on {len(result_df)} data points."
            else:
                summary = f"Analysis of {query} based on {len(result_df)} data points. "
                if is_time_comparison and time_cols:
                    tp = sorted(result_df[time_cols[0]].unique())
                    if len(tp) >= 2: summary += f"Comparing {tp[0]} to {tp[-1]}, "
                main_cols = [c for c in result_df.columns if c not in ['% Change_Cost','% Change_Units']][:3]
                summary += f"The data shows values for {', '.join(main_cols)}."
            return summary
        except Exception as e:
            print(f"Error generating summary: {e}")

    return summary_text if summary_text else "Analysis of the requested data:"


def sanitize_null_labels(text: str) -> str:
    replacements = {
        " (blank)": " (Uncategorized)",  " (null)": " (Uncategorized)",
        " (empty)": " (Uncategorized)",  "Blank: ": "(Uncategorized): ",
        "Empty: ":  "(Uncategorized): ", "Null: ":  "(Uncategorized): ",
        "NA: ":     "(Uncategorized): ", "<NA>":    "(Uncategorized)",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def build_top_complaints_by_cost_table(query: str, df: pd.DataFrame):
    query_lower = query.lower()
    if not all(term in query_lower for term in ["top", "complaint", "cost"]):
        return None
    if "COST" not in df.columns:
        return None

    limit_match = re.search(r"\btop\s+(\d+)\b", query_lower)
    limit = int(limit_match.group(1)) if limit_match else 20
    limit = max(1, min(limit, 100))

    complaint_candidates = [
        "SUB_CATEGORY_3",
        "SUB_CODE_DESCRIPTION",
        "PROBLEM_CODE_DESCRIPTION",
        "TYPE_DESCRIPTION",
        "COPQ_CATEGORY",
    ]
    complaint_col = next((col for col in complaint_candidates if col in df.columns), None)
    if not complaint_col:
        return None

    work = df.copy()
    if "CODE_TYPE" in work.columns:
        complaint_rows = work[
            work["CODE_TYPE"].astype(str).str.contains("complaint", case=False, na=False)
        ]
        if not complaint_rows.empty:
            work = complaint_rows

    work = work[[complaint_col, "COST"]].copy()
    work[complaint_col] = (
        work[complaint_col]
        .fillna("(Uncategorized)")
        .astype(str)
        .str.strip()
        .replace(["nan", "None", "", "NaN", "null", "<NA>"], "(Uncategorized)")
    )
    work["COST"] = pd.to_numeric(work["COST"], errors="coerce").fillna(0)

    grouped = (
        work.groupby(complaint_col, dropna=False)
        .agg(**{"Complaint Count": ("COST", "size"), "Total COST": ("COST", "sum")})
        .sort_values("Total COST", ascending=False)
        .head(limit)
        .reset_index()
        .rename(columns={complaint_col: "Complaint"})
    )
    if grouped.empty:
        return None

    grouped.insert(0, "Rank", range(1, len(grouped) + 1))
    top_row = grouped.iloc[0]
    top_total_cost = float(top_row["Total COST"])
    summary = (
        f"Here are the top {len(grouped)} complaint categories ranked by total COST. "
        f"{top_row['Complaint']} has the highest total COST at "
        f"{top_total_cost:,.2f} across {int(top_row['Complaint Count'])} complaint records."
    )
    grouped["Total COST"] = grouped["Total COST"].map(lambda value: f"{value:,.2f}")
    return summary, grouped


# ─────────────────────────────────────────────
# Direct Chart Generation (bypasses agent)
# ─────────────────────────────────────────────

def _build_chart_prompt(query: str, columns_str: str, images_folder: str, error_feedback: str = "") -> str:
    error_section = f"\nPREVIOUS ATTEMPT FAILED — fix this error:\n{error_feedback}\n" if error_feedback else ""
    return f"""You are a Python data analyst. Write ONLY executable Python code with zero explanation, zero markdown, zero comments.
{error_section}
Available variable: `df` — a pandas DataFrame.
DataFrame columns:
{columns_str}

Task: {query}

Strict rules:
1. matplotlib and numpy are pre-imported as `plt` and `np`. pandas is `pd`. Do NOT re-import them.
2. Save figure with: plt.savefig('{images_folder}/chart.png', bbox_inches='tight', dpi=150)
3. Call plt.close('all') after saving
4. Do NOT call plt.show()
5. Do NOT print anything
6. Handle NaN/missing values — call .dropna() before groupby/plot
7. Limit categorical axes to top 15 values to avoid clutter

CRITICAL MATPLOTLIB RULES (seaborn barplot causes errors — follow these exactly):
- For bar charts: use plt.bar(x_values, y_values) NOT sns.barplot()
- Always store groupby result in a variable FIRST, then extract .values:
    grouped = df.groupby('COL')['VAL'].sum().nlargest(15)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(grouped.index.astype(str), grouped.values)
- For pie charts  : use ax.pie(values, labels=labels)
- For line charts : use ax.plot(x, y)
- For histograms  : use ax.hist(df['COL'].dropna(), bins=20)
- Always call plt.xticks(rotation=45, ha='right') for categorical x-axis
- Always call plt.tight_layout() before savefig
- Add title: ax.set_title('...') and labels: ax.set_xlabel('...'), ax.set_ylabel('...')

Output ONLY the raw Python code — no backticks, no language tag, nothing else.
"""


def _strip_fences(code: str) -> str:
    code = re.sub(r'```python\s*', '', code)
    code = re.sub(r'```\s*', '', code)
    return code.strip()


def _get_clean_text_content(response) -> str:
    if not response:
        return ""
    content = response.content if hasattr(response, 'content') else response
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    return str(content)


def _build_query_prompt(query: str, columns_str: str, error_feedback: str = "") -> str:
    error_section = f"\nPREVIOUS ATTEMPT FAILED — fix this error:\n{error_feedback}\n" if error_feedback else ""
    return f"""You are a Python data analyst. Write ONLY executable Python code with zero explanation, zero markdown, zero comments.
{error_section}
Available variable: `df` — a pandas DataFrame.
DataFrame columns:
{columns_str}

Task: {query}

Strict rules:
1. pandas is imported as `pd`, numpy as `np`. Do NOT re-import them.
2. Store the final answer/result in the variable `result`.
3. The value of `result` can be a pandas DataFrame, Series, number, string, list, dict, or boolean.
4. Keep the code simple, efficient, and correct.
5. If the query asks for a table or list, compute the appropriate DataFrame/Series/list and store it in `result`.
6. Make sure to handle NaN/missing values.
7. Print nothing. Only store the result in the `result` variable.

Output ONLY the raw Python code — no backticks, no language tag, nothing else.
"""


def generate_query_directly(query: str, df: pd.DataFrame) -> tuple:
    """
    Execute a data query by asking the LLM for Python code, executing it,
    and capturing the result variable or stdout.
    Returns (success: bool, result_val: any, stdout_str: str)
    """
    import numpy as np
    from contextlib import redirect_stdout

    columns_info = []
    for col in df.columns:
        dtype  = str(df[col].dtype)
        sample = []
        try: sample = df[col].dropna().head(3).tolist()
        except Exception: pass
        columns_info.append(f"  - {col} ({dtype}): sample={sample}")
    columns_str = "\n".join(columns_info)

    exec_globals = {
        "df": df.copy(), "pd": pd, "np": np, "__builtins__": __builtins__,
    }
    last_error = ""

    for attempt in range(1, 3):
        try:
            llm = _get_llm(temperature=0)
            prompt = _build_query_prompt(query, columns_str, error_feedback=last_error)
            response = llm.invoke(prompt)
            raw_code = _get_clean_text_content(response)
            raw_code = _strip_fences(raw_code)

            print(f"[Query] Attempt {attempt} code:\n{raw_code}\n{'─'*60}")

            exec_globals["df"] = df.copy()
            exec_globals["result"] = None
            
            f = io.StringIO()
            with redirect_stdout(f):
                exec(raw_code, exec_globals)
            printed = f.getvalue().strip()
            
            result_val = exec_globals.get("result")
            if result_val is None and printed:
                result_val = printed

            if result_val is not None:
                return True, result_val, printed
            
            last_error = "The code executed successfully but neither stored a value in 'result' nor printed anything."
            print(f"[Query] Attempt {attempt}: no output, retrying...")
        except HTTPException:
            raise
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            print(f"[Query] Attempt {attempt} failed: {last_error}")

    return False, None, ""


def summarize_query_result(query: str, result_val: any) -> str:
    """
    Take the user's query and the Python execution result,
    and ask the LLM to format it into a friendly response.
    """
    if isinstance(result_val, pd.DataFrame):
        data_str = result_val.to_markdown(index=False)
    elif isinstance(result_val, pd.Series):
        data_str = result_val.to_frame().reset_index().to_markdown(index=False)
    else:
        data_str = str(result_val)

    prompt = f"""You are a helpful data analysis assistant.
User query: {query}
Result of python calculation:
{data_str}

Task:
Construct a clear, concise, and friendly answer to the user query based on the calculation result.
If the result is tabular data, you MUST include the markdown table in your response.
Your response should start with a 1-3 sentence summary of the findings, and then include any tables if appropriate.

Write ONLY the final response without any conversational filler or prefaces.
"""
    try:
        llm = _get_llm(temperature=0)
        resp = llm.invoke(prompt)
        return _get_clean_text_content(resp)
    except Exception as e:
        print(f"Error summarizing result: {e}")
        if isinstance(result_val, (pd.DataFrame, pd.Series)):
            return data_str
        return f"The result is: {result_val}"



def generate_chart_directly(query: str, df: pd.DataFrame, images_folder: str) -> tuple:
    """
    Generate a chart by asking the LLM for Python code, then exec()-ing it.
    Uses _get_llm() which enforces rate limits automatically.
    Retries once with error feedback on failure.
    Returns (success: bool, summary_text: str)
    """
    import numpy as np

    columns_info = []
    for col in df.columns:
        dtype  = str(df[col].dtype)
        sample = []
        try: sample = df[col].dropna().head(3).tolist()
        except Exception: pass
        columns_info.append(f"  - {col} ({dtype}): sample={sample}")
    columns_str = "\n".join(columns_info)

    exec_globals = {
        "df": df.copy(), "pd": pd, "plt": plt,
        "sns": sns, "np": np, "__builtins__": __builtins__,
    }
    last_error = ""

    for attempt in range(1, 3):
        try:
            # _get_llm() internally calls _rate_limit_check()
            llm      = _get_llm(temperature=0)
            prompt   = _build_chart_prompt(query, columns_str, images_folder, error_feedback=last_error)
            response = llm.invoke(prompt)
            raw_code = _get_clean_text_content(response)
            raw_code = _strip_fences(raw_code)

            print(f"[Chart] Attempt {attempt} code:\n{raw_code}\n{'─'*60}")

            plt.close('all')
            exec_globals["df"] = df.copy()
            exec(raw_code, exec_globals)

            chart_path = os.path.join(images_folder, "chart.png")
            if os.path.exists(chart_path):
                print(f"[Chart] Saved on attempt {attempt}")
                return True, f"Here is the chart for your query: {query}"

            is_image, _ = get_single_image_base64(images_folder)
            if is_image:
                return True, f"Here is the chart for your query: {query}"

            last_error = (
                f"Code ran without error but no file was saved to "
                f"'{images_folder}/chart.png'. Ensure plt.savefig(...) is called."
            )
            print(f"[Chart] Attempt {attempt}: no image saved, retrying...")

        except HTTPException:
            raise   # re-raise rate limit / auth errors immediately
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            print(f"[Chart] Attempt {attempt} failed: {last_error}")
            plt.close('all')

    print(f"[Chart] All attempts failed. Last error: {last_error}")
    return False, ""


# ─────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────

load_data()

auth_router = APIRouter(tags=["Auth"])
data_router = APIRouter(tags=["data-analysis"])


# ─────────────────────────────────────────────
# Auth Endpoints
# ─────────────────────────────────────────────

@auth_router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = await authenticate_user(form_data.username.strip(), form_data.password)
    except PyMongoError:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable")

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid email or password",
                            headers={"WWW-Authenticate": "Bearer"})
    token = create_access_token({"sub": user["email"], "role": user.get("role", "user")})
    return {"access_token": token, "token_type": "bearer"}


@auth_router.get("/me")
async def read_current_user(current_user: dict = Depends(get_current_user)):
    return current_user


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):
    now = datetime.utcnow()
    new_user = {
        "email": user.email,
        "password_hash": hash_password(user.password),
        "role": user.role,
        "created_at": now,
        "updated_at": now,
    }

    try:
        existing_user = await users_collection.find_one({"email": user.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )
        await users_collection.insert_one(new_user)
    except HTTPException:
        raise
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )
    except PyMongoError:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable")

    return {"email": new_user["email"], "role": new_user["role"]}


@auth_router.post("/logout")
async def logout():
    return {"message": "Logout successful. Remove token on frontend."}


# ─────────────────────────────────────────────
# Rate Limit Status Endpoint  (admin only)
# ─────────────────────────────────────────────

@data_router.get("/rate_limit_status/")
async def rate_limit_status(current_user: dict = Depends(get_current_user)):
    """Returns current RPM window usage and daily usage — admin only."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    with _rate_lock:
        now = time.monotonic()
        active_in_window = sum(1 for t in _minute_window if now - t <= 60.0)
    return {
        "rpm_used":   active_in_window,
        "rpm_limit":  RATE_LIMIT_RPM,
        "rpd_used":   _daily_count,
        "rpd_limit":  RATE_LIMIT_RPD,
        "reset_date": str(_daily_reset_date),
    }


# ─────────────────────────────────────────────
# Query Endpoint
# ─────────────────────────────────────────────

@data_router.post("/query/")
async def query_data(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    global DATA, CHAT_HISTORY

    if DATA is None:
        if not load_data():
            raise HTTPException(status_code=400, detail="No data loaded.")

    query = request.query
    query_lower = query.lower()

    is_table_request = any(k in query_lower for k in [
        'table', 'tabular', 'columns', 'rows', 'dataframe'
    ])
    is_list_request = (not is_table_request) and any(k in query_lower for k in [
        'list', 'top', 'questions', 'reasons', 'factors', 'steps',
        'best', 'worst', 'highest', 'lowest', 'most common',
        'frequently', 'commonly', 'popular', 'tips', 'advice', 'suggestions'
    ])
    is_time_comparison = any(t in query_lower for t in [
        'yoy', 'mom', 'year over year', 'month over month', 'yearly', 'monthly',
        'compared to last', 'previous year', 'previous month', 'comparison',
        'trend', 'performance over time', 'change since', 'growth'
    ])
    is_chart_request = any(t in query_lower for t in [
        'chart', 'plot', 'graph', 'bar', 'pie', 'line chart', 'histogram',
        'scatter', 'visualize', 'visualise', 'show chart', 'draw'
    ])

    print(f"Query | user={current_user['email']} role={current_user['role']}")
    print(
        f"Flags | table={is_table_request} list={is_list_request} "
        f"time={is_time_comparison} chart={is_chart_request}"
    )

    if not ACTIVE_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set in .env")

    # ── Helper ──────────────────────────────────
    def build_response(text: str, html_content: str = None) -> dict:
        image_files = get_all_images_base64(IMAGES_FOLDER)
        is_image = len(image_files) > 0
        primary_image = image_files[0] if is_image else None
        if is_image and not text.strip():
            text = f"Here is the chart for your query: {query}"
        resp = {
            "response": text,
            "is_images": is_image,
            "image_file": primary_image,
            "image_files": image_files
        }
        if html_content and not is_image:
            resp["html_content"] = html_content
        return resp

    top_complaints_result = build_top_complaints_by_cost_table(query, DATA)
    if top_complaints_result is not None and not is_chart_request:
        text_summary, result_df = top_complaints_result
        html_table = dataframe_to_html_table(result_df)
        markdown_table = result_df.to_markdown(index=False)
        response_text = f"{text_summary}\n\n{markdown_table}"
        CHAT_HISTORY.append({"query": query, "response": text_summary, "user": current_user["email"]})
        if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
            CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
        return build_response(response_text, combine_table_html(html_table, text_summary))

    # ─────────────────────────────────────────────
    # CHART PATH — bypass agent, direct exec
    # ─────────────────────────────────────────────
    if is_chart_request:
        print("[Chart] Bypassing agent — direct code execution")
        # empty_folder(IMAGES_FOLDER)
        success, summary = generate_chart_directly(query, DATA, IMAGES_FOLDER)
        if success:
            CHAT_HISTORY.append({"query": query, "response": summary, "user": current_user["email"]})
            if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
                CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            return build_response(summary)
        print("[Chart] Direct generation failed — falling back to agent")

    # ─────────────────────────────────────────────
    # NON-CHART PATH — direct code execution
    # ─────────────────────────────────────────────
    try:
        success, result_val, stdout = generate_query_directly(query, DATA)
        if success:
            response_text = summarize_query_result(query, result_val)
        else:
            response_text = "I'm sorry, I could not complete that query. Please try rephrasing."
        response_text = sanitize_null_labels(response_text)

        # Immediate image check (agent may have saved a chart)
        is_image_present, _ = get_single_image_base64(IMAGES_FOLDER)
        if is_image_present:
            summary = response_text.strip() or f"Here is the chart for your query: {query}"
            CHAT_HISTORY.append({"query": query, "response": summary, "user": current_user["email"]})
            if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
                CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            return build_response(summary)

        is_short = len(response_text.split('\n')) < 3 and len(response_text) < 300 and '|' not in response_text
        result_df = None
        if not is_short:
            result_df = extract_dataframe_from_text(response_text)

        # DataFrame extracted → HTML table
        if result_df is not None and not result_df.empty:
            result_df    = standardize_output_format(result_df)
            text_summary = ensure_text_summary(response_text, result_df, query, is_time_comparison)
            html_table   = dataframe_to_html_table(result_df)
            final_table  = remove_newlines_replace(html_table)
            final_result = replace_between_pipe_and_I(response_text, "\n" + final_table + "\n")
            CHAT_HISTORY.append({"query": query, "response": text_summary, "user": current_user["email"]})
            if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
                CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
            return build_response(final_result, combine_table_html(html_table, text_summary))

        # Fallback pipe-table parser
        if '|' in response_text and '\n' in response_text and '-' in response_text:
            cleaned = re.sub(r'\n\s*\n', '\n', response_text)
            lines   = [l.strip() for l in cleaned.split('\n') if '|' in l.strip()]
            if len(lines) >= 2:
                header_cells = [c.strip() for c in lines[0].split('|') if c.strip()]
                if header_cells:
                    data_rows = []
                    for line in lines[1:]:
                        if re.match(r'^[\s\-\+\|:]*$', line): continue
                        cells = [c.strip() for c in line.split('|') if c]
                        if cells:
                            while len(cells) < len(header_cells): cells.append("(Uncategorized)")
                            data_rows.append(cells[:len(header_cells)])
                    if data_rows:
                        manual_df    = standardize_output_format(pd.DataFrame(data_rows, columns=header_cells))
                        text_summary = ensure_text_summary(response_text, manual_df, query, is_time_comparison)
                        html_table   = dataframe_to_html_table(manual_df)
                        CHAT_HISTORY.append({"query": query, "response": text_summary, "user": current_user["email"]})
                        if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
                            CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
                        return build_response(text_summary, combine_table_html(html_table, text_summary))

        # Plain text / list
        CHAT_HISTORY.append({"query": query, "response": response_text, "user": current_user["email"]})
        if len(CHAT_HISTORY) > MAX_HISTORY_LENGTH:
            CHAT_HISTORY = CHAT_HISTORY[-MAX_HISTORY_LENGTH:]
        return build_response(response_text)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Query processing error: {e}")
        # empty_folder(IMAGES_FOLDER)
        return {
            "response": f"An error occurred: {str(e)}",
            "is_images": False,
            "image_file": None,
        }


# ─────────────────────────────────────────────
# Clear Chat
# ─────────────────────────────────────────────

@data_router.post("/clear_chat/")
async def clear_chat(current_user: dict = Depends(get_current_user)):
    global CHAT_HISTORY
    if current_user["role"] == "admin":
        CHAT_HISTORY = []
        return {"message": "Chat history cleared."}
    else:
        CHAT_HISTORY = [e for e in CHAT_HISTORY if e.get("user") != current_user["email"]]
        return {"message": f"Chat history for {current_user['email']} cleared."}


# ─────────────────────────────────────────────
# Mount & Run
# ─────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(data_router)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
