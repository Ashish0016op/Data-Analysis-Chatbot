import pandas as pd
import plotly.express as px
from typing import Optional, Tuple

def check_uncategorized_percentage(df: pd.DataFrame, threshold: float = 50.0) -> Tuple[float, bool]:
    """Check percentage of uncategorized values in DataFrame."""
    total_rows = len(df)
    uncategorized_count = sum(
        df[col].astype(str).str.contains('(Uncategorized)', case=False, na=False).sum()
        for col in df.columns
    )
    percentage = (uncategorized_count / (total_rows * len(df.columns))) * 100
    return percentage, percentage > threshold

def extract_columns_from_query(query: str, df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """Extract x and y columns from query or DataFrame structure."""
    query_lower = query.lower().strip()
    x_col, y_col = None, None
    
    # Simple keyword-based column extraction
    for col in df.columns:
        col_lower = col.lower()
        if any(k in col_lower for k in ['date', 'year', 'month', 'quarter', 'week', 'category', 'group', 'type']):
            x_col = col
        if any(k in col_lower for k in ['count', 'value', 'amount', 'total', 'sum']):
            y_col = col
    
    # Fallback to first suitable columns
    if not x_col:
        categorical_cols = [col for col in df.columns if df[col].nunique() <= 50]
        date_cols = [col for col in df.columns if any(k in col.lower() for k in ['date', 'year', 'month'])]
        x_col = next((col for col in date_cols + categorical_cols), df.columns[0] if len(df.columns) > 0 else None)
    
    if not y_col:
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        y_col = next((col for col in numeric_cols), None)
    
    return x_col, y_col

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
        line_chart_keywords = ['trend', 'over time', 'line', 'series']
        pie_chart_keywords = ['distribution', 'share', 'proportion', 'pie']
        scatter_chart_keywords = ['scatter', 'point', 'correlation']
        histogram_chart_keywords = ['histogram', 'frequency', 'dist']
        bar_chart_keywords = ['bar', 'column', 'count', 'group']
        
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
                chart_type = "line"
            elif categorical_cols and numeric_cols and len(df) <= 50:
                chart_type = "bar"
            elif len(numeric_cols) >= 1 and len(df) > 50:
                chart_type = "histogram"
            else:
                chart_type = "bar"
        
        # Extract x and y columns
        x_col, y_col = extract_columns_from_query(query, df)
        
        # Fallback for y_col: Create a count column if no numeric column is found
        if not y_col or y_col not in df.columns:
            df['Count'] = 1
            y_col = 'Count'
        
        # Validate column selection
        if not x_col or x_col not in df.columns or not y_col or y_col not in df.columns:
            return "<p>Invalid column selection for visualization.</p>"
        
        # Aggregate data for bar chart to ensure all categories are counted
        if chart_type == "bar":
            df_agg = df.groupby(x_col, as_index=False)[y_col].sum()
            x_col_agg, y_col_agg = x_col, y_col
        else:
            df_agg = df
            x_col_agg, y_col_agg = x_col, y_col
        
        # Handle time series for line chart
        if chart_type == "line" and any(k in x_col_agg.lower() for k in ['date', 'year', 'month', 'quarter', 'week']):
            try:
                if not pd.api.types.is_datetime64_any_dtype(df_agg[x_col_agg]):
                    df_agg[x_col_agg] = pd.to_datetime(df_agg[x_col_agg], errors='coerce')
                df_agg = df_agg.sort_values(by=x_col_agg)
            except:
                pass
        
        # Create chart
        chart_title = f"{y_col_agg} by {x_col_agg}"
        
        if chart_type == "bar":
            fig = px.bar(df_agg, x=x_col_agg, y=y_col_agg, title=chart_title)
            if any(k in x_col_agg.lower() for k in ['date', 'year', 'month']):
                fig.update_xaxes(tickangle=45)
        
        elif chart_type == "line":
            fig = px.line(df_agg, x=x_col_agg, y=y_col_agg, title=chart_title)
            fig.update_traces(mode='lines+markers', marker=dict(size=8))
        
        elif chart_type == "pie":
            if df_agg[x_col_agg].nunique() > 10:
                top_values = df_agg.groupby(x_col_agg)[y_col_agg].sum().nlargest(10).index
                df_pie = df_agg[df_agg[x_col_agg].isin(top_values)].copy()
                if len(df_pie) < len(df_agg):
                    other_sum = df_agg[~df_agg[x_col_agg].isin(top_values)][y_col_agg].sum()
                    other_row = pd.DataFrame({x_col_agg: ['Other'], y_col_agg: [other_sum]})
                    df_pie = pd.concat([df_pie, other_row], ignore_index=True)
                fig = px.pie(df_pie, names=x_col_agg, values=y_col_agg, title=chart_title)
            else:
                fig = px.pie(df_agg, names=x_col_agg, values=y_col_agg, title=chart_title)
        
        elif chart_type == "scatter":
            fig = px.scatter(df_agg, x=x_col_agg, y=y_col_agg, title=chart_title)
            fig.update_traces(marker=dict(size=8))
        
        elif chart_type == "histogram":
            fig = px.histogram(df_agg, x=y_col_agg, title=f"Distribution of {y_col_agg}")
            fig.update_traces(marker_line_width=1, marker_line_color="white")
        
        else:
            return "<p>Unsupported chart type.</p>"
        
        # Update layout
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=50, r=50, t=80, b=80),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_title=x_col_agg,
            yaxis_title=y_col_agg,
            showlegend=True
        )
        
        # Format axes
        if any(k in x_col_agg.lower() for k in ['date', 'year', 'month']):
            fig.update_xaxes(tickangle=45, tickformat="%b %Y" if 'date' in x_col_agg.lower() else None)
        if pd.api.types.is_numeric_dtype(df_agg[y_col_agg]):
            fig.update_yaxes(tickformat=",.0f")
        
        # Convert to HTML
        chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        
        return f"""
        <div class="chart-container">
            <h4>Visualization Type: {chart_type.capitalize()} Chart</h4>
            {chart_html}
        </div>
        """
    
    except Exception as e:
        print(f"Error generating chart: {e}")
        return "<p>Error generating visualization. Please check the data and query.</p>"
    



import pandas as pd
df = pd.DataFrame({
    'Business Unit': ['Apertures Solution - US', 'Tech Division - EU', 'Apertures Solution - US', 'Global Services'],
    'Value': [10, 20, 15, 30]
})
# query = "bar chart of Value by Business Unit"
# chart_html = generate_plotly_chart(df, query)
# print(chart_html)


########################################################################################################

# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns
# import numpy as np
# import os
# from datetime import datetime

# def plot_charts_from_dataframe(df, output_dir="charts"):
#     """
#     Analyze a DataFrame and generate appropriate charts based on data types.
    
#     Parameters:
#     df (pandas.DataFrame): Input DataFrame
#     output_dir (str): Directory to save the charts
    
#     Returns:
#     list: List of generated chart file paths
#     """
#     # Create output directory if it doesn't exist
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)
    
#     # Initialize list to store chart file paths
#     chart_files = []
    
#     # Get data types and column names
#     numeric_cols = df.select_dtypes(include=[np.number]).columns
#     categorical_cols = df.select_dtypes(include=['object', 'category']).columns
#     datetime_cols = df.select_dtypes(include=['datetime64']).columns
    
#     # Set seaborn style for better visuals
#     sns.set_style('whitegrid')
    
#     # 1. Histogram for numerical columns
#     for col in numeric_cols:
#         plt.figure(figsize=(8, 6))
#         plt.hist(df[col].dropna(), bins=30, edgecolor='black')
#         plt.title(f'Histogram of {col}\n(Shows distribution of numerical data)')
#         plt.xlabel(col)
#         plt.ylabel('Frequency')
#         filename = f'{output_dir}/histogram_{col}.png'
#         plt.savefig(filename, bbox_inches='tight')
#         chart_files.append(filename)
#         plt.close()
    
#     # 2. Bar plot for categorical columns
#     for col in categorical_cols:
#         if df[col].nunique() <= 20:  # Limit to avoid cluttered plots
#             plt.figure(figsize=(8, 6))
#             df[col].value_counts().plot(kind='bar')
#             plt.title(f'Bar Plot of {col}\n(Shows frequency of categorical data)')
#             plt.xlabel(col)
#             plt.ylabel('Count')
#             plt.xticks(rotation=45)
#             filename = f'{output_dir}/bar_{col}.png'
#             plt.savefig(filename, bbox_inches='tight')
#             chart_files.append(filename)
#             plt.close()
    
#     # 3. Line plot for datetime vs numerical
#     if len(datetime_cols) > 0 and len(numeric_cols) > 0:
#         for num_col in numeric_cols:
#             for dt_col in datetime_cols:
#                 plt.figure(figsize=(10, 6))
#                 plt.plot(df[dt_col], df[num_col])
#                 plt.title(f'Line Plot: {num_col} vs {dt_col}\n(Shows trends over time)')
#                 plt.xlabel(dt_col)
#                 plt.ylabel(num_col)
#                 plt.xticks(rotation=45)
#                 filename = f'{output_dir}/line_{num_col}_vs_{dt_col}.png'
#                 plt.savefig(filename, bbox_inches='tight')
#                 chart_files.append(filename)
#                 plt.close()
    
#     # 4. Scatter plot for pairs of numerical columns
#     if len(numeric_cols) >= 2:
#         for i, col1 in enumerate(numeric_cols):
#             for col2 in numeric_cols[i+1:]:
#                 plt.figure(figsize=(8, 6))
#                 plt.scatter(df[col1], df[col2], alpha=0.5)
#                 plt.title(f'Scatter Plot: {col1} vs {col2}\n(Shows relationship between two numerical variables)')
#                 plt.xlabel(col1)
#                 plt.ylabel(col2)
#                 filename = f'{output_dir}/scatter_{col1}_vs_{col2}.png'
#                 plt.savefig(filename, bbox_inches='tight')
#                 chart_files.append(filename)
#                 plt.close()
    
#     # 5. Box plot for numerical columns by categorical columns
#     if len(categorical_cols) > 0 and len(numeric_cols) > 0:
#         for cat_col in categorical_cols:
#             if df[cat_col].nunique() <= 10:  # Limit to avoid cluttered plots
#                 for num_col in numeric_cols:
#                     plt.figure(figsize=(8, 6))
#                     sns.boxplot(x=cat_col, y=num_col, data=df)
#                     plt.title(f'Box Plot: {num_col} by {cat_col}\n(Shows distribution across categories)')
#                     plt.xticks(rotation=45)
#                     filename = f'{output_dir}/box_{num_col}_by_{cat_col}.png'
#                     plt.savefig(filename, bbox_inches='tight')
#                     chart_files.append(filename)
#                     plt.close()
    
#     return chart_files

# # Example usage:
# if __name__ == "__main__":
#     # Create sample DataFrame
#     np.random.seed(42)
#     dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
#     sample_data = {
#         'date': dates,
#         'sales': np.random.normal(100, 20, len(dates)),
#         'price': np.random.uniform(10, 50, len(dates)),
#         'category': np.random.choice(['A', 'B', 'C'], len(dates)),
#         'region': np.random.choice(['North', 'South', 'East', 'West'], len(dates))
#     }
#     df = pd.DataFrame(sample_data)
    
#     # Generate charts
#     charts = plot_charts_from_dataframe(df)
#     print("Generated charts:", charts)



####################################################################################################

# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns
# import numpy as np
# import os
# from datetime import datetime
# import plotly.express as px
# import plotly.graph_objects as go
# import squarify
# import warnings

# def plot_charts_from_dataframe(df, output_dir="charts"):
#     """
#     Analyze a DataFrame and generate various charts based on data types.
    
#     Parameters:
#     df (pandas.DataFrame): Input DataFrame
#     output_dir (str): Directory to save the charts
    
#     Returns:
#     list: List of generated chart file paths
#     """
#     # Create output directory if it doesn't exist
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)
    
#     # Initialize list to store chart file paths
#     chart_files = []
    
#     # Get data types and column names
#     numeric_cols = df.select_dtypes(include=[np.number]).columns
#     categorical_cols = df.select_dtypes(include=['object', 'category']).columns
#     datetime_cols = df.select_dtypes(include=['datetime64']).columns
    
#     # Set seaborn style for matplotlib-based charts
#     sns.set_style('whitegrid')
    
#     # 1. Histogram for numerical columns
#     for col in numeric_cols:
#         plt.figure(figsize=(8, 6))
#         plt.hist(df[col].dropna(), bins=30, edgecolor='black')
#         plt.title(f'Histogram of {col}\n(Shows distribution of numerical data)')
#         plt.xlabel(col)
#         plt.ylabel('Frequency')
#         filename = f'{output_dir}/histogram_{col}.png'
#         plt.savefig(filename, bbox_inches='tight')
#         chart_files.append(filename)
#         plt.close()
    
#     # 2. Bar/Column Plot for categorical columns
#     for col in categorical_cols:
#         if df[col].nunique() <= 20:  # Limit to avoid cluttered plots
#             plt.figure(figsize=(8, 6))
#             df[col].value_counts().plot(kind='bar')
#             plt.title(f'Bar Plot of {col}\n(Shows frequency of categorical data)')
#             plt.xlabel(col)
#             plt.ylabel('Count')
#             plt.xticks(rotation=45)
#             filename = f'{output_dir}/bar_{col}.png'
#             plt.savefig(filename, bbox_inches='tight')
#             chart_files.append(filename)
#             plt.close()
    
#     # 3. Line Plot for datetime vs numerical
#     if len(datetime_cols) > 0 and len(numeric_cols) > 0:
#         for num_col in numeric_cols:
#             for dt_col in datetime_cols:
#                 plt.figure(figsize=(10, 6))
#                 plt.plot(df[dt_col], df[num_col])
#                 plt.title(f'Line Plot: {num_col} vs {dt_col}\n(Shows trends over time)')
#                 plt.xlabel(dt_col)
#                 plt.ylabel(num_col)
#                 plt.xticks(rotation=45)
#                 filename = f'{output_dir}/line_{num_col}_vs_{dt_col}.png'
#                 plt.savefig(filename, bbox_inches='tight')
#                 chart_files.append(filename)
#                 plt.close()
    
#     # 4. Scatter Plot for pairs of numerical columns
#     if len(numeric_cols) >= 2:
#         for i, col1 in enumerate(numeric_cols):
#             for col2 in numeric_cols[i+1:]:
#                 plt.figure(figsize=(8, 6))
#                 plt.scatter(df[col1], df[col2], alpha=0.5)
#                 plt.title(f'Scatter Plot: {col1} vs {col2}\n(Shows relationship between two numerical variables)')
#                 plt.xlabel(col1)
#                 plt.ylabel(col2)
#                 filename = f'{output_dir}/scatter_{col1}_vs_{col2}.png'
#                 plt.savefig(filename, bbox_inches='tight')
#                 chart_files.append(filename)
#                 plt.close()
    
#     # 5. Box Plot for numerical columns by categorical columns
#     # if len(categorical_cols) > 0 and len(numeric_cols) > 0:
#     #     for cat_col in categorical_cols:
#     #         if df[cat_col].nunique() <= 10:  # Limit to avoid cluttered plots
#     #             for num_col in numeric_cols:
#     #                 plt.figure(figsize=(8, 6))
#     #                 sns.boxplot(x=cat_col, y=num_col, data=df)
#     #                 plt.title(f'Box Plot: {num_col} by {cat_col}\n(Shows distribution across categories)')
#     #                 plt.xticks(rotation=45)
#     #                 filename = f'{output_dir}/box_{num_col}_by_{cat_col airy.py}.png'
#     #                 plt.savefig(filename, bbox_inches='tight')
#     #                 chart_files.append(filename)
#     #                 plt.close()
#      # 5. Box Plot for numerical columns by categorical columns
#     if len(categorical_cols) > 0 and len(numeric_cols) > 0:
#         for cat_col in categorical_cols:
#             if df[cat_col].nunique() <= 10:  # Limit to avoid cluttered plots
#                 for num_col in numeric_cols:
#                     plt.figure(figsize=(8, 6))
#                     sns.boxplot(x=cat_col, y=num_col, data=df)
#                     plt.title(f'Box Plot: {num_col} by {cat_col}\n(Shows distribution across categories)')
#                     plt.xticks(rotation=45)
#                     filename = f'{output_dir}/box_{num_col}_by_{cat_col}.png'  # Corrected line
#                     plt.savefig(filename, bbox_inches='tight')
#                     chart_files.append(filename)
#                     plt.close()
    
#     # 6. Pie Chart for categorical columns
#     for col in categorical_cols:
#         if df[col].nunique() <= 10:  # Limit for clarity
#             plt.figure(figsize=(8, 8))
#             df[col].value_counts().plot(kind='pie', autopct='%1.1f%%')
#             plt.title(f'Pie Chart of {col}\n(Shows proportion of categories)')
#             plt.ylabel('')
#             filename = f'{output_dir}/pie_{col}.png'
#             plt.savefig(filename, bbox_inches='tight')
#             chart_files.append(filename)
#             plt.close()
    
#     # 7. Donut Chart (similar to pie but with a hole)
#     for col in categorical_cols:
#         if df[col].nunique() <= 10:
#             plt.figure(figsize=(8, 8))
#             df[col].value_counts().plot(kind='pie', autopct='%1.1f%%', wedgeprops=dict(width=0.4))
#             plt.title(f'Donut Chart of {col}\n(Shows proportion of categories)')
#             plt.ylabel('')
#             filename = f'{output_dir}/donut_{col}.png'
#             plt.savefig(filename, bbox_inches='tight')
#             chart_files.append(filename)
#             plt.close()
    
#     # 8. Treemap Chart for categorical counts
#     for col in categorical_cols:
#         if df[col].nunique() <= 20:
#             counts = df[col].value_counts()
#             plt.figure(figsize=(10, 6))
#             squarify.plot(sizes=counts, label=counts.index, alpha=0.8)
#             plt.title(f'Treemap of {col}\n(Shows hierarchical proportion of categories)')
#             plt.axis('off')
#             filename = f'{output_dir}/treemap_{col}.png'
#             plt.savefig(filename, bbox_inches='tight')
#             chart_files.append(filename)
#             plt.close()
    
#     # 9. Heatmap for numerical correlations
#     if len(numeric_cols) >= 2:
#         plt.figure(figsize=(10, 8))
#         corr = df[numeric_cols].corr()
#         sns.heatmap(corr, annot=True, cmap='coolwarm', center=0)
#         plt.title('Heatmap of Numerical Correlations\n(Shows correlation between numerical variables)')
#         filename = f'{output_dir}/heatmap_correlation.png'
#         plt.savefig(filename, bbox_inches='tight')
#         chart_files.append(filename)
#         plt.close()
    
#     # 10. Pareto Chart for categorical counts
#     for col in categorical_cols:
#         if df[col].nunique() <= 20:
#             counts = df[col].value_counts().sort_values(ascending=False)
#             cum_percentage = counts.cumsum() / counts.sum() * 100
#             fig, ax1 = plt.subplots(figsize=(10, 6))
#             ax1.bar(counts.index, counts, color='C0')
#             ax1.set_xlabel(col)
#             ax1.set_ylabel('Count', color='C0')
#             ax2 = ax1.twinx()
#             ax2.plot(counts.index, cum_percentage, color='C1', marker='o')
#             ax2.set_ylabel('Cumulative Percentage', color='C1')
#             ax2.set_ylim(0, 100)
#             plt.title(f'Pareto Chart of {col}\n(Shows cumulative contribution of categories)')
#             plt.xticks(rotation=45)
#             filename = f'{output_dir}/pareto_{col}.png'
#             plt.savefig(filename, bbox_inches='tight')
#             chart_files.append(filename)
#             plt.close()
    
#     # 11. Geo Chart (requires lat/lon or location data)
#     location_cols = [col for col in df.columns if 'lat' in col.lower() or 'lon' in col.lower() or 'city' in col.lower() or 'country' in col.lower()]
#     if len(location_cols) >= 1:
#         for col in location_cols:
#             try:
#                 fig = px.scatter_geo(df, locations=col, locationmode='country names', size=numeric_cols[0] if numeric_cols else None)
#                 fig.update_layout(title=f'Geo Chart of {col}\n(Shows data on a map)')
#                 filename = f'{output_dir}/geo_{col}.html'
#                 fig.write_html(filename)
#                 chart_files.append(filename)
#             except:
#                 warnings.warn(f"Could not generate Geo Chart for {col}: Invalid or missing geospatial data")
    
#     # 12. Scatter Map (similar to Geo but with lat/lon)
#     if any('lat' in col.lower() for col in df.columns) and any('lon' in col.lower() for col in df.columns):
#         lat_col = next(col for col in df.columns if 'lat' in col.lower())
#         lon_col = next(col for col in df.columns if 'lon' in col.lower())
#         try:
#             fig = px.scatter_mapbox(df, lat=lat_col, lon=lon_col, size=numeric_cols[0] if numeric_cols else None, zoom=2)
#             fig.update_layout(mapbox_style="open-street-map", title=f'Scatter Map\n(Shows data points on a map)')
#             filename = f'{output_dir}/scatter_map.html'
#             fig.write_html(filename)
#             chart_files.append(filename)
#         except:
#             warnings.warn("Could not generate Scatter Map: Invalid or missing lat/lon data")
    
#     # 13. Waterfall Chart for numerical changes
#     if len(numeric_cols) >= 1 and len(datetime_cols) >= 1:
#         for num_col in numeric_cols:
#             for dt_col in datetime_cols:
#                 temp_df = df[[dt_col, num_col]].dropna()
#                 temp_df = temp_df.sort_values(dt_col)
#                 changes = temp_df[num_col].diff().fillna(temp_df[num_col].iloc[0])
#                 fig = go.Figure(go.Waterfall(
#                     x=temp_df[dt_col], y=changes,
#                     textposition="auto", text=[f"{x:.2f}" for x in changes]
#                 ))
#                 fig.update_layout(title=f'Waterfall Chart: {num_col} Changes\n(Shows incremental changes over time)')
#                 filename = f'{output_dir}/waterfall_{num_col}_vs_{dt_col}.html'
#                 fig.write_html(filename)
#                 chart_files.append(filename)
    
#     # 14. Funnel Chart for categorical stages
#     for col in categorical_cols:
#         if df[col].nunique() <= 10:
#             counts = df[col].value_counts().sort_values(ascending=False)
#             fig = go.Figure(go.Funnel(
#                 y=counts.index, x=counts.values
#             ))
#             fig.update_layout(title=f'Funnel Chart of {col}\n(Shows sequential stages)')
#             filename = f'{output_dir}/funnel_{col}.html'
#             fig.write_html(filename)
#             chart_files.append(filename)
    
#     # 15. Bubble Chart (extension of scatter with size)
#     if len(numeric_cols) >= 3:
#         col1, col2, col3 = numeric_cols[:3]
#         plt.figure(figsize=(8, 6))
#         plt.scatter(df[col1], df[col2], s=df[col3]*10, alpha=0.5)
#         plt.title(f'Bubble Chart: {col1} vs {col2} (Size: {col3})\n(Shows three numerical variables)')
#         plt.xlabel(col1)
#         plt.ylabel(col2)
#         filename = f'{output_dir}/bubble_{col1}_vs_{col2}.png'
#         plt.savefig(filename, bbox_inches='tight')
#         chart_files.append(filename)
#         plt.close()
    
#     # 16. Candlestick Chart (requires OHLC data)
#     ohlc_cols = [col for col in df.columns if col.lower() in ['open', 'high', 'low', 'close']]
#     if len(ohlc_cols) >= 4 and len(datetime_cols) >= 1:
#         temp_df = df[ohlc_cols + [datetime_cols[0]]].dropna()
#         fig = go.Figure(data=[go.Candlestick(
#             x=temp_df[datetime_cols[0]],
#             open=temp_df['open'], high=temp_df['high'],
#             low=temp_df['low'], close=temp_df['close']
#         )])
#         fig.update_layout(title=f'Candlestick Chart\n(Shows stock price movements)')
#         filename = f'{output_dir}/candlestick.html'
#         fig.write_html(filename)
#         chart_files.append(filename)
#     else:
#         warnings.warn("Could not generate Candlestick Chart: Missing OHLC data")
    
#     # 17. Area Chart for datetime vs numerical
#     if len(datetime_cols) > 0 and len(numeric_cols) > 0:
#         for num_col in numeric_cols:
#             for dt_col in datetime_cols:
#                 plt.figure(figsize=(10, 6))
#                 plt.fill_between(df[dt_col], df[num_col], alpha=0.5)
#                 plt.plot(df[dt_col], df[num_col], color='black')
#                 plt.title(f'Area Chart: {num_col} vs {dt_col}\n(Shows cumulative trends over time)')
#                 plt.xlabel(dt_col)
#                 plt.ylabel(num_col)
#                 plt.xticks(rotation=45)
#                 filename = f'{output_dir}/area_{num_col}_vs_{dt_col}.png'
#                 plt.savefig(filename, bbox_inches='tight')
#                 chart_files.append(filename)
#                 plt.close()
    
#     # 18. KPI Chart (simple metric display)
#     for col in numeric_cols:
#         plt.figure(figsize=(6, 4))
#         plt.text(0.5, 0.5, f'{col}\nMean: {df[col].mean():.2f}\nMedian: {df[col].median():.2f}',
#                  ha='center', va='center', fontsize=12)
#         plt.axis('off')
#         plt.title(f'KPI Chart for {col}\n(Shows key metrics)')
#         filename = f'{output_dir}/kpi_{col}.png'
#         plt.savefig(filename, bbox_inches='tight')
#         chart_files.append(filename)
#         plt.close()
    
#     # 19. Sankey Chart (requires source-target data)
#     if len(categorical_cols) >= 2:
#         src_col, tgt_col = categorical_cols[:2]
#         flow = df.groupby([src_col, tgt_col]).size().reset_index(name='value')
#         if not flow.empty:
#             labels = list(set(flow[src_col]).union(set(flow[tgt_col])))
#             src = [labels.index(s) for s in flow[src_col]]
#             tgt = [labels.index(t) for t in flow[tgt_col]]
#             fig = go.Figure(data=[go.Sankey(
#                 node=dict(label=labels),
#                 link=dict(source=src, target=tgt, value=flow['value'])
#             )])
#             fig.update_layout(title=f'Sankey Chart: {src_col} to {tgt_col}\n(Shows flow between categories)')
#             filename = f'{output_dir}/sankey_{src_col}_to_{tgt_col}.html'
#             fig.write_html(filename)
#             chart_files.append(filename)
#         else:
#             warnings.warn(f"Could not generate Sankey Chart: No valid flow data between {src_col} and {tgt_col}")
    
#     # 20. Radar Chart for numerical columns
#     if len(numeric_cols) >= 3:
#         means = df[numeric_cols].mean()
#         angles = np.linspace(0, 2*np.pi, len(means), endpoint=False).tolist()
#         means = means.tolist() + [means[0]]  # Close the loop
#         angles += [angles[0]]
#         fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
#         ax.fill(angles, means, alpha=0.25)
#         ax.plot(angles, means)
#         ax.set_xticks(angles[:-1])
#         ax.set_xticklabels(numeric_cols)
#         plt.title('Radar Chart of Numerical Means\n(Shows comparison across variables)')
#         filename = f'{output_dir}/radar_numerical.png'
#         plt.savefig(filename, bbox_inches='tight')
#         chart_files.append(filename)
#         plt.close()
    
#     return chart_files

# # Example usage:
# if __name__ == "__main__":
#     # Create sample DataFrame
#     np.random.seed(42)
#     dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
#     sample_data = {
#         'date': dates,
#         'sales': np.random.normal(100, 20, len(dates)),
#         'price': np.random.uniform(10, 50, len(dates)),
#         'volume': np.random.normal(50, 10, len(dates)),
#         'category': np.random.choice(['A', 'B', 'C'], len(dates)),
#         'region': np.random.choice(['North', 'South', 'East', 'West'], len(dates)),
#         'country': np.random.choice(['USA', 'Canada', 'Mexico'], len(dates))
#     }
#     df = pd.DataFrame(sample_data)
    
#     # Generate charts
#     charts = plot_charts_from_dataframe(df)
#     print("Generated charts:", charts)

import pandas as pd
import numpy as np
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings

def plot_interactive_charts_from_dataframe(df, output_dir="interactive_charts"):
    """
    Analyze a DataFrame and generate interactive HTML charts with hover effects.
    
    Parameters:
    df (pandas.DataFrame): Input DataFrame
    output_dir (str): Directory to save the HTML charts
    
    Returns:
    list: List of generated chart file paths
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Initialize list to store chart file paths
    chart_files = []
    
    # Get data types and column names
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
    
    # Set default template for all plots
    template = "plotly_white"
    
    # 1. Interactive Histogram for numerical columns
    for col in numeric_cols:
        fig = px.histogram(df, x=col, nbins=30, 
                          title=f'Interactive Histogram of {col}<br><sub>Shows distribution of numerical data (hover for details)</sub>',
                          template=template)
        fig.update_traces(hovertemplate='<b>Range:</b> %{x}<br><b>Count:</b> %{y}<extra></extra>')
        fig.update_layout(showlegend=False, height=600)
        filename = f'{output_dir}/histogram_{col}.html'
        fig.write_html(filename)
        chart_files.append(filename)
    
    # 2. Interactive Bar Chart for categorical columns
    for col in categorical_cols:
        if df[col].nunique() <= 20:
            value_counts = df[col].value_counts()
            fig = px.bar(x=value_counts.index, y=value_counts.values,
                        title=f'Interactive Bar Chart of {col}<br><sub>Shows frequency of categorical data (hover for details)</sub>',
                        labels={'x': col, 'y': 'Count'}, template=template)
            fig.update_traces(hovertemplate='<b>Category:</b> %{x}<br><b>Count:</b> %{y}<br><b>Percentage:</b> %{customdata}%<extra></extra>',
                            customdata=np.round((value_counts.values / value_counts.sum()) * 100, 1))
            fig.update_layout(showlegend=False, height=600)
            filename = f'{output_dir}/bar_{col}.html'
            fig.write_html(filename)
            chart_files.append(filename)
    
    # 3. Interactive Line Chart for datetime vs numerical
    if len(datetime_cols) > 0 and len(numeric_cols) > 0:
        for num_col in numeric_cols:
            for dt_col in datetime_cols:
                fig = px.line(df, x=dt_col, y=num_col,
                             title=f'Interactive Line Chart: {num_col} vs {dt_col}<br><sub>Shows trends over time (hover for details)</sub>',
                             template=template)
                fig.update_traces(hovertemplate='<b>Date:</b> %{x}<br><b>' + num_col + ':</b> %{y}<extra></extra>')
                fig.update_layout(height=600)
                filename = f'{output_dir}/line_{num_col}_vs_{dt_col}.html'
                fig.write_html(filename)
                chart_files.append(filename)
    
    # 4. Interactive Scatter Plot for pairs of numerical columns
    if len(numeric_cols) >= 2:
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                fig = px.scatter(df, x=col1, y=col2,
                               title=f'Interactive Scatter Plot: {col1} vs {col2}<br><sub>Shows relationship between numerical variables (hover for details)</sub>',
                               template=template)
                fig.update_traces(hovertemplate='<b>' + col1 + ':</b> %{x}<br><b>' + col2 + ':</b> %{y}<extra></extra>')
                fig.update_layout(height=600)
                filename = f'{output_dir}/scatter_{col1}_vs_{col2}.html'
                fig.write_html(filename)
                chart_files.append(filename)
    
    # 5. Interactive Box Plot for numerical columns by categorical columns
    # if len(categorical_cols) > 0 and len(numeric_cols) > 0:
    #     for cat_col in categorical_cols:
    #         if df[cat_col].nunique() <= 10:
    #             for num_col in numeric_cols:
    #                 fig = px.box(df, x=cat_col, y=num_col,
    #                             title=f'Interactive Box Plot: {num_col} by {cat_col}<br><sub>Shows distribution across categories (hover for details)</sub>',
    #                             template=template)
    #                 fig.update_traces(hovertemplate='<b>Category:</b> %{x}<br><b>Value:</b> %{y}<br><b>Q1:</b> %{q1}<br><b>Median:</b> %{median}<br><b>Q3:</b> %{q3}<extra></extra>')
    #                 fig.update_layout(height=600)
    #                 filename = f'{output_dir}/box_{num_col}_by_{cat_col}.html'
    #                 fig.write_html(filename)
    #                 chart_files.append(filename)
    
    # 6. Interactive Pie Chart for categorical columns
    for col in categorical_cols:
        if df[col].nunique() <= 10:
            value_counts = df[col].value_counts()
            fig = px.pie(values=value_counts.values, names=value_counts.index,
                        title=f'Interactive Pie Chart of {col}<br><sub>Shows proportion of categories (hover for details)</sub>',
                        template=template)
            fig.update_traces(hovertemplate='<b>Category:</b> %{label}<br><b>Count:</b> %{value}<br><b>Percentage:</b> %{percent}<extra></extra>')
            fig.update_layout(height=600)
            filename = f'{output_dir}/pie_{col}.html'
            fig.write_html(filename)
            chart_files.append(filename)
    
    # 7. Interactive Donut Chart
    for col in categorical_cols:
        if df[col].nunique() <= 10:
            value_counts = df[col].value_counts()
            fig = px.pie(values=value_counts.values, names=value_counts.index,
                        title=f'Interactive Donut Chart of {col}<br><sub>Shows proportion of categories (hover for details)</sub>',
                        template=template, hole=0.4)
            fig.update_traces(hovertemplate='<b>Category:</b> %{label}<br><b>Count:</b> %{value}<br><b>Percentage:</b> %{percent}<extra></extra>')
            fig.update_layout(height=600)
            filename = f'{output_dir}/donut_{col}.html'
            fig.write_html(filename)
            chart_files.append(filename)
    
    # 8. Interactive Treemap Chart
    for col in categorical_cols:
        if df[col].nunique() <= 20:
            value_counts = df[col].value_counts()
            fig = px.treemap(names=value_counts.index, values=value_counts.values,
                           title=f'Interactive Treemap of {col}<br><sub>Shows hierarchical proportion (hover for details)</sub>',
                           template=template)
            fig.update_traces(hovertemplate='<b>Category:</b> %{label}<br><b>Count:</b> %{value}<br><b>Percentage:</b> %{percentParent}<extra></extra>')
            fig.update_layout(height=600)
            filename = f'{output_dir}/treemap_{col}.html'
            fig.write_html(filename)
            chart_files.append(filename)
    
    # 9. Interactive Correlation Heatmap
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr()
        fig = px.imshow(corr, text_auto=True, aspect="auto",
                       title='Interactive Correlation Heatmap<br><sub>Shows correlation between numerical variables (hover for details)</sub>',
                       template=template, color_continuous_scale='RdBu_r')
        fig.update_traces(hovertemplate='<b>Variables:</b> %{x} vs %{y}<br><b>Correlation:</b> %{z:.3f}<extra></extra>')
        fig.update_layout(height=600)
        filename = f'{output_dir}/heatmap_correlation.html'
        fig.write_html(filename)
        chart_files.append(filename)
    
    # 10. Interactive Pareto Chart
    for col in categorical_cols:
        if df[col].nunique() <= 20:
            counts = df[col].value_counts().sort_values(ascending=False)
            cum_percentage = counts.cumsum() / counts.sum() * 100
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=counts.index, y=counts.values, name="Count",
                               hovertemplate='<b>Category:</b> %{x}<br><b>Count:</b> %{y}<extra></extra>'),
                         secondary_y=False)
            fig.add_trace(go.Scatter(x=counts.index, y=cum_percentage, mode='lines+markers', 
                                   name="Cumulative %", line=dict(color='red'),
                                   hovertemplate='<b>Category:</b> %{x}<br><b>Cumulative %:</b> %{y:.1f}%<extra></extra>'),
                         secondary_y=True)
            
            fig.update_xaxes(title_text=col)
            fig.update_yaxes(title_text="Count", secondary_y=False)
            fig.update_yaxes(title_text="Cumulative Percentage", secondary_y=True, range=[0, 100])
            fig.update_layout(title=f'Interactive Pareto Chart of {col}<br><sub>Shows cumulative contribution (hover for details)</sub>',
                            template=template, height=600)
            filename = f'{output_dir}/pareto_{col}.html'
            fig.write_html(filename)
            chart_files.append(filename)
    
    # 11. Interactive Geo Chart
    location_cols = [col for col in df.columns if 'country' in col.lower() or 'nation' in col.lower()]
    if len(location_cols) >= 1:
        for col in location_cols:
            try:
                location_counts = df[col].value_counts()
                fig = px.choropleth(locations=location_counts.index, 
                                  z=location_counts.values,
                                  locationmode='country names',
                                  title=f'Interactive Geo Chart of {col}<br><sub>Shows data on world map (hover for details)</sub>',
                                  template=template)
                fig.update_traces(hovertemplate='<b>Country:</b> %{location}<br><b>Count:</b> %{z}<extra></extra>')
                fig.update_layout(height=600)
                filename = f'{output_dir}/geo_{col}.html'
                fig.write_html(filename)
                chart_files.append(filename)
            except Exception as e:
                warnings.warn(f"Could not generate Geo Chart for {col}: {str(e)}")
    
    # 12. Interactive Scatter Map
    if any('lat' in col.lower() for col in df.columns) and any('lon' in col.lower() for col in df.columns):
        lat_col = next(col for col in df.columns if 'lat' in col.lower())
        lon_col = next(col for col in df.columns if 'lon' in col.lower())
        try:
            size_col = numeric_cols[0] if numeric_cols else None
            fig = px.scatter_mapbox(df, lat=lat_col, lon=lon_col, 
                                  size=size_col, zoom=2, mapbox_style="open-street-map",
                                  title='Interactive Scatter Map<br><sub>Shows data points on map (hover for details)</sub>',
                                  template=template)
            fig.update_traces(hovertemplate='<b>Lat:</b> %{lat}<br><b>Lon:</b> %{lon}<br>' + 
                            (f'<b>{size_col}:</b> %{{marker.size}}<extra></extra>' if size_col else '<extra></extra>'))
            fig.update_layout(height=600)
            filename = f'{output_dir}/scatter_map.html'
            fig.write_html(filename)
            chart_files.append(filename)
        except Exception as e:
            warnings.warn(f"Could not generate Scatter Map: {str(e)}")
    
    # 13. Interactive Waterfall Chart
    if len(numeric_cols) >= 1 and len(datetime_cols) >= 1:
        for num_col in numeric_cols:
            for dt_col in datetime_cols:
                temp_df = df[[dt_col, num_col]].dropna().sort_values(dt_col)
                changes = temp_df[num_col].diff().fillna(temp_df[num_col].iloc[0])
                
                fig = go.Figure(go.Waterfall(
                    x=temp_df[dt_col], 
                    y=changes,
                    textposition="auto", 
                    text=[f"{x:.2f}" for x in changes],
                    hovertemplate='<b>Date:</b> %{x}<br><b>Change:</b> %{y:.2f}<br><b>Text:</b> %{text}<extra></extra>'
                ))
                fig.update_layout(title=f'Interactive Waterfall Chart: {num_col} Changes<br><sub>Shows incremental changes over time (hover for details)</sub>',
                                template=template, height=600)
                filename = f'{output_dir}/waterfall_{num_col}_vs_{dt_col}.html'
                fig.write_html(filename)
                chart_files.append(filename)
    
    # 14. Interactive Funnel Chart
    for col in categorical_cols:
        if df[col].nunique() <= 10:
            counts = df[col].value_counts().sort_values(ascending=False)
            fig = go.Figure(go.Funnel(
                y=counts.index, 
                x=counts.values,
                hovertemplate='<b>Stage:</b> %{y}<br><b>Count:</b> %{x}<extra></extra>'
            ))
            fig.update_layout(title=f'Interactive Funnel Chart of {col}<br><sub>Shows sequential stages (hover for details)</sub>',
                            template=template, height=600)
            filename = f'{output_dir}/funnel_{col}.html'
            fig.write_html(filename)
            chart_files.append(filename)
    
    # 15. Interactive Bubble Chart
    if len(numeric_cols) >= 3:
        col1, col2, col3 = numeric_cols[:3]
        color_col = categorical_cols[0] if categorical_cols else None
        fig = px.scatter(df, x=col1, y=col2, size=col3, color=color_col,
                        title=f'Interactive Bubble Chart: {col1} vs {col2} (Size: {col3})<br><sub>Shows three+ variables (hover for details)</sub>',
                        template=template)
        fig.update_traces(hovertemplate='<b>' + col1 + ':</b> %{x}<br><b>' + col2 + ':</b> %{y}<br><b>' + col3 + ':</b> %{marker.size}<extra></extra>')
        fig.update_layout(height=600)
        filename = f'{output_dir}/bubble_{col1}_vs_{col2}.html'
        fig.write_html(filename)
        chart_files.append(filename)
    
    # 16. Interactive Candlestick Chart
    ohlc_cols = [col for col in df.columns if col.lower() in ['open', 'high', 'low', 'close']]
    if len(ohlc_cols) >= 4 and len(datetime_cols) >= 1:
        temp_df = df[ohlc_cols + [datetime_cols[0]]].dropna()
        fig = go.Figure(data=[go.Candlestick(
            x=temp_df[datetime_cols[0]],
            open=temp_df['open'], high=temp_df['high'],
            low=temp_df['low'], close=temp_df['close'],
            hoverinfo='x+y+text'
        )])
        fig.update_layout(title='Interactive Candlestick Chart<br><sub>Shows OHLC price movements (hover for details)</sub>',
                        template=template, height=600)
        filename = f'{output_dir}/candlestick.html'
        fig.write_html(filename)
        chart_files.append(filename)
    
    # 17. Interactive Area Chart
    if len(datetime_cols) > 0 and len(numeric_cols) > 0:
        for num_col in numeric_cols:
            for dt_col in datetime_cols:
                fig = px.area(df, x=dt_col, y=num_col,
                             title=f'Interactive Area Chart: {num_col} vs {dt_col}<br><sub>Shows cumulative trends over time (hover for details)</sub>',
                             template=template)
                fig.update_traces(hovertemplate='<b>Date:</b> %{x}<br><b>' + num_col + ':</b> %{y}<extra></extra>')
                fig.update_layout(height=600)
                filename = f'{output_dir}/area_{num_col}_vs_{dt_col}.html'
                fig.write_html(filename)
                chart_files.append(filename)
    
    # 18. Interactive KPI Dashboard
    if len(numeric_cols) > 0:
        fig = make_subplots(
            rows=2, cols=min(len(numeric_cols), 3),
            subplot_titles=[f'{col} Stats' for col in numeric_cols[:6]],
            specs=[[{"type": "indicator"}] * min(len(numeric_cols), 3)] * 2
        )
        
        for i, col in enumerate(numeric_cols[:6]):
            row = i // 3 + 1
            col_pos = i % 3 + 1
            fig.add_trace(go.Indicator(
                mode="number+gauge+delta",
                value=df[col].mean(),
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': f"Mean {col}"},
                gauge={'axis': {'range': [df[col].min(), df[col].max()]},
                      'bar': {'color': "darkblue"},
                      'steps': [{'range': [df[col].min(), df[col].median()], 'color': "lightgray"},
                               {'range': [df[col].median(), df[col].max()], 'color': "gray"}],
                      'threshold': {'line': {'color': "red", 'width': 4},
                                   'thickness': 0.75, 'value': df[col].median()}}
            ), row=row, col=col_pos)
        
        fig.update_layout(title='Interactive KPI Dashboard<br><sub>Shows key metrics (hover for details)</sub>',
                        template=template, height=600)
        filename = f'{output_dir}/kpi_dashboard.html'
        fig.write_html(filename)
        chart_files.append(filename)
    
    # 19. Interactive Sankey Chart
    if len(categorical_cols) >= 2:
        src_col, tgt_col = categorical_cols[:2]
        flow = df.groupby([src_col, tgt_col]).size().reset_index(name='value')
        if not flow.empty:
            labels = list(set(flow[src_col]).union(set(flow[tgt_col])))
            src = [labels.index(s) for s in flow[src_col]]
            tgt = [labels.index(t) for t in flow[tgt_col]]
            
            fig = go.Figure(data=[go.Sankey(
                node=dict(label=labels, pad=15, thickness=20),
                link=dict(source=src, target=tgt, value=flow['value'],
                         hovertemplate='<b>From:</b> %{source.label}<br><b>To:</b> %{target.label}<br><b>Flow:</b> %{value}<extra></extra>')
            )])
            fig.update_layout(title=f'Interactive Sankey Chart: {src_col} to {tgt_col}<br><sub>Shows flow between categories (hover for details)</sub>',
                            template=template, height=600)
            filename = f'{output_dir}/sankey_{src_col}_to_{tgt_col}.html'
            fig.write_html(filename)
            chart_files.append(filename)
    
    # 20. Interactive Radar Chart
    if len(numeric_cols) >= 3:
        means = df[numeric_cols].mean()
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=means.values,
            theta=means.index,
            fill='toself',
            name='Mean Values',
            hovertemplate='<b>Variable:</b> %{theta}<br><b>Mean Value:</b> %{r}<extra></extra>'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            title='Interactive Radar Chart of Numerical Means<br><sub>Shows comparison across variables (hover for details)</sub>',
            template=template, height=600
        )
        filename = f'{output_dir}/radar_numerical.html'
        fig.write_html(filename)
        chart_files.append(filename)
    
    return chart_files

# Example usage:
if __name__ == "__main__":
    # Create sample DataFrame
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    sample_data = {
        'date': dates,
        'sales': np.random.normal(100, 20, len(dates)),
        'price': np.random.uniform(10, 50, len(dates)),
        'volume': np.random.normal(50, 10, len(dates)),
        'category': np.random.choice(['A', 'B', 'C'], len(dates)),
        'region': np.random.choice(['North', 'South', 'East', 'West'], len(dates)),
        'country': np.random.choice(['USA', 'Canada', 'Mexico'], len(dates))
    }
    df = pd.DataFrame(sample_data)
    
    # Generate interactive charts
    charts = plot_interactive_charts_from_dataframe(df)
    print("Generated interactive charts:", charts)
    print(f"\nTotal charts generated: {len(charts)}")
    print("All charts are now interactive HTML files with hover effects!")

    