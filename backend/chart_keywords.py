# # chart_keywords.py

# # 🟦 Bar Chart
# bar_chart_keywords = [
#     "bar chart", "bar graph", "compare", "comparison", "grouped", "category wise",
#     "by category", "per category", "segment wise", "group-wise", "column chart",
#     "side by side", "discrete values", "subcategories", "bar visualization"
# ]

# # 📈 Line Chart
# line_chart_keywords = [
#     "line chart", "trend", "over time", "time series", "change over time",
#     "growth", "progress", "evolution", "yoy", "year over year", "year-on-year",
#     "mom", "month over month", "month-on-month", "monthly growth", "daily trend",
#     "weekly change", "time-based", "continuous trend"
# ]

# # 🥧 Pie / Donut Chart
# pie_chart_keywords = [
#     "pie chart", "donut chart", "percentage", "proportion", "share",
#     "contribution", "composition", "part of whole", "how much each contributes",
#     "segment contribution", "circular chart", "percent split"
# ]

# # 📊 Histogram
# histogram_keywords = [
#     "histogram", "frequency", "distribution", "spread", "how often", "bin",
#     "buckets", "value ranges", "value count", "frequency chart", "continuous distribution"
# ]

# # ⚪ Scatter Plot
# scatter_plot_keywords = [
#     "scatter plot", "scatter graph", "relationship", "correlation",
#     "association", "between variables", "x vs y", "bivariate", "two-variable",
#     "distribution between", "outliers", "clusters", "scatter diagram"
# ]

# # 📦 Box Plot
# box_plot_keywords = [
#     "box plot", "box and whisker", "quartile", "median", "iqr", "outlier",
#     "distribution comparison", "range", "spread", "box summary", "summary statistics"
# ]

# # 🟪 Area Chart
# area_chart_keywords = [
#     "area chart", "stacked area", "cumulative trend", "total over time",
#     "volume over time", "area under curve", "layered trend", "stacked growth",
#     "filled line chart"
# ]

# # 🔥 Heatmap
# heatmap_keywords = [
#     "heatmap", "matrix", "correlation heatmap", "intensity", "density",
#     "color intensity", "value grid", "co-occurrence", "pair correlation",
#     "cell value", "two-dimensional pattern", "visual matrix"
# ]

# # 🧩 Treemap
# treemap_keywords = [
#     "treemap", "hierarchy", "nested chart", "nested categories",
#     "part of whole", "sub-segments", "proportional size", "tree structure",
#     "grouping by size"
# ]

# # 🧭 Unified Dictionary
# chart_keywords = {
#     "bar": bar_chart_keywords,
#     "line": line_chart_keywords,
#     "pie": pie_chart_keywords,
#     "histogram": histogram_keywords,
#     "scatter": scatter_plot_keywords,
#     "box": box_plot_keywords,
#     "area": area_chart_keywords,
#     "heatmap": heatmap_keywords,
#     "treemap": treemap_keywords
# }


# chart_keywords.py

# 🟦 Bar Chart
bar_chart_keywords = [
    "bar chart", "bar graph", "compare", "comparison", "grouped",
    "category", "segment wise", "group-wise", "column chart",
    "side by side", "discrete values", "subcategories", "bar visualization","yoy", "year over year", "year on year",
    "mom", "month over month", "month on month",
]

# 📈 Line Chart
line_chart_keywords = [
    "line chart", "trend", "over time", "time series", "change over time",
    "growth", "progress", "evolution",  "monthly growth", "daily trend",
    "weekly change", "time-based", "continuous trend"
]

# 🥧 Pie / Donut Chart
pie_chart_keywords = [
    "pie chart", "donut chart", "percentage", "proportion", "share",
    "contribution", "composition", "part of whole", "how much each contributes",
    "segment contribution", "circular chart", "percent split",
]

# 📊 Histogram
histogram_chart_keywords = [
    "histogram", "frequency", "distribution", "spread", "how often", "bin",
    "buckets", "value ranges", "value count", "frequency chart", "continuous distribution"
]

# ⚪ Scatter Plot
scatter_chart_keywords = [
    "scatter plot", "scatter graph", "relationship", "correlation",
    "association", "between variables", "x vs y", "bivariate", "two-variable",
    "distribution between", "outliers", "clusters", "scatter diagram"
]

# 📦 Box Plot
box_chart_keywords = [
    "box plot", "box and whisker", "quartile", "median", "iqr", "outlier",
    "distribution comparison", "range", "spread", "box summary", "summary statistics"
]

# 🟪 Area Chart
area_chart_keywords = [
    "area chart", "stacked area", "cumulative trend", "total over time",
    "volume over time", "area under curve", "layered trend", "stacked growth",
    "filled line chart"
]

# 🔥 Heatmap
heatmap_chart_keywords = [
    "heatmap", "matrix", "correlation heatmap", "intensity", "density",
    "color intensity", "value grid", "co-occurrence", "pair correlation",
    "cell value", "two-dimensional pattern", "visual matrix"
]

# 🧩 Treemap
tree_chart_keywords = [
    "treemap", "hierarchy", "nested chart", "nested categories",
    "part of whole", "sub-segments", "proportional size", "tree structure",
    "grouping by size"
]

# 🧭 Unified Metadata Dictionary
# 🧭 Unified Metadata Dictionary with axis selection guidance
chart_keywords = {
    "bar": {
        "keywords": bar_chart_keywords,
        "min_rows": 1,
        "min_categories": 2,
        "max_categories": 30,
        "requires_date": True,
        "axes_selection": {
            "x_prefer": ["categorical", "date"],
            "y_prefer": ["numeric"],
            "groupby_prefer": ["categorical"]
        }
    },
    "line": {
        "keywords": line_chart_keywords,
        "min_rows": 4,
        "requires_date": True,
        "axes_selection": {
            "x_prefer": ["date", "time"],
            "y_prefer": ["numeric"],
            "groupby_prefer": ["categorical"]
        }
    },
    "pie": {
        "keywords": pie_chart_keywords,
        "min_categories": 2,
        "max_categories": 10,
        "requires_date": False,
        "axes_selection": {
            "value_prefer": ["numeric"],
            "label_prefer": ["categorical"]
        }
    },
    "histogram": {
        "keywords": histogram_chart_keywords,
        "min_rows": 3,
        "requires_date": False,
        "axes_selection": {
            "x_prefer": ["numeric"],
            "bins_prefer": ["auto", "sturges", "scott"]
        }
    },
    "scatter": {
        "keywords": scatter_chart_keywords,
        "min_numeric": 2,
        "min_rows": 5,
        "requires_date": False,
        "axes_selection": {
            "x_prefer": ["numeric"],
            "y_prefer": ["numeric"],
            "color_prefer": ["categorical"]
        }
    },
    "box": {
        "keywords": box_chart_keywords,
        "min_rows": 5,
        "requires_date": False,
        "axes_selection": {
            "x_prefer": ["categorical"],
            "y_prefer": ["numeric"],
            "groupby_prefer": ["categorical"]
        }
    },
    "area": {
        "keywords": area_chart_keywords,
        "min_rows": 4,
        "requires_date": True,
        "axes_selection": {
            "x_prefer": ["date", "time"],
            "y_prefer": ["numeric"],
            "stack_prefer": ["categorical"]
        }
    },
    "heatmap": {
        "keywords": heatmap_chart_keywords,
        "min_rows": 4,
        "min_numeric": 2,
        "requires_date": False,
        "axes_selection": {
            "x_prefer": ["categorical", "date"],
            "y_prefer": ["categorical"],
            "value_prefer": ["numeric"]
        }
    },
    "treemap": {
        "keywords": tree_chart_keywords,
        "min_categories": 2,
        "requires_date": False,
        "axes_selection": {
            "hierarchy_prefer": ["categorical"],
            "size_prefer": ["numeric"],
            "color_prefer": ["numeric", "categorical"]
        }
    }
}