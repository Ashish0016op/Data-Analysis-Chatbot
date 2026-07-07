# # Read the CSV file
# import pandas as pd 

# df = pd.read_csv(r"Warranty_Apertures_After2023 Latest Data.csv", encoding='ISO-8859-1', low_memory=False)
 
# # Select first 100 rows
# df_sample = df.head(50000)
 
# # Alternatively, if you want a random sample of 100 rows
# # df_sample = df.sample(n=100, random_state=42)
 
# # Save the sampled data to a new CSV file (optional)
# df_sample.to_csv('sampled_data_200000.csv', index=False)
 
# # Print the number of rows to verify
# print(f"Number of rows in sampled data: {len(df_sample)}")

###############################################################################################################################


# import csv
# import random
# from datetime import datetime, timedelta
# from faker import Faker
# import uuid

# # Initialize Faker for generating fake data
# fake = Faker()

# # Define static lists for consistent data generation
# business_units = ["VisionTech Solutions"]
# business_unit_dwh = ["VTX"]
# brands = ["StarFrame"]
# invoicing_plant = ["Dayton, OH"]
# mfg_plants = ["Dayton, OH"]
# uom = ["EA"]
# code_types = ["Complaint"]
# copq_includes = ["Yes", "No"]
# ffr_includes = ["Yes", "No"]
# copq_categories = ["Warranty", "Not Included"]
# dw_load_date = "9/20/2024"

# # Define problem types and their associated codes and descriptions
# problem_types = [
#     {"type_code": "", "type_desc": "SEAL FAILURE-LIFETIME/ORIG HOMEOWN", "prob_code": "SF1", "prob_desc": "SEAL FAILURE-LIFETIME/ORIG HOMEOWN", "sub_code": "SL1", "sub_desc": "SEAL FAILURE-LIFETIME/ORIG HOMEOWN", "sub_cat_1": "Insulated Glass Unit", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Seal Failure"},
#     {"type_code": "", "type_desc": "SEAL FAILURE", "prob_code": "SF2", "prob_desc": "SEAL FAILURE", "sub_code": "SF3", "sub_desc": "SEAL FAILURE", "sub_cat_1": "Insulated Glass Unit", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Seal Failure"},
#     {"type_code": "", "type_desc": "DIRT/PRINTS BETWEEN THE PANES", "prob_code": "DP1", "prob_desc": "DIRT/PRINTS BETWEEN THE PANES", "sub_code": "DP2", "sub_desc": "DIRT/PRINTS BETWEEN THE PANES", "sub_cat_1": "Insulated Glass Unit", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Debris - Smudge - Interior"},
#     {"type_code": "", "type_desc": "LOWE - POOR QUALITY/DEFECTIVE", "prob_code": "LQ1", "prob_desc": "LOWE - POOR QUALITY/DEFECTIVE", "sub_code": "LQ2", "sub_desc": "LOWE - POOR QUALITY/DEFECTIVE", "sub_cat_1": "Insulated Glass Unit", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Low E Defects or Low-E on the wrong surface"},
#     {"type_code": "", "type_desc": "BOWED SASH", "prob_code": "BS1", "prob_desc": "BOWED SASH", "sub_code": "BS2", "sub_desc": "BOWED SASH", "sub_cat_1": "Sash", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Out of Square - Bowed"},
#     {"type_code": "", "type_desc": "CUSTOMER STANDARD PURCHASE", "prob_code": "CP1", "prob_desc": "CUSTOMER STANDARD PURCHASE", "sub_code": "CP2", "sub_desc": "CUSTOMER STANDARD PURCHASE", "sub_cat_1": "Complete Unit", "sub_cat_2": "Sales & Service", "sub_cat_3": "Samples and Displays"},
#     {"type_code": "", "type_desc": "CUSTOMER CONCESSION", "prob_code": "CC1", "prob_desc": "CUSTOMER CONCESSION", "sub_code": "CC2", "sub_desc": "CUSTOMER CONCESSION", "sub_cat_1": "Complete Unit", "sub_cat_2": "Sales & Service", "sub_cat_3": "Customer Concession"},
#     {"type_code": "", "type_desc": "OFFICE ERROR", "prob_code": "OE1", "prob_desc": "OFFICE ERROR", "sub_code": "OE2", "sub_desc": "OFFICE ERROR", "sub_cat_1": "Complete Unit", "sub_cat_2": "Sales & Service", "sub_cat_3": "Order Entry Error"},
#     {"type_code": "", "type_desc": "BROKEN OR DAMAGED LOCKS AND KEEPER", "prob_code": "LK1", "prob_desc": "BROKEN OR DAMAGED LOCKS AND KEEPER", "sub_code": "LK2", "sub_desc": "BROKEN OR DAMAGED LOCKS AND KEEPER", "sub_cat_1": "Sash", "sub_cat_2": "Damage", "sub_cat_3": "During Delivery"},
#     {"type_code": "", "type_desc": "PAINTED PRODUCT POOR QUALITY", "prob_code": "PP1", "prob_desc": "PAINTED PRODUCT POOR QUALITY", "sub_code": "PP2", "sub_desc": "PAINTED PRODUCT POOR QUALITY", "sub_cat_1": "Complete Unit", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Defective Paint"},
#     {"type_code": "", "type_desc": "SCANNED ON TRUCK BUT NOT DELIVERED", "prob_code": "ND1", "prob_desc": "SCANNED ON TRUCK BUT NOT DELIVERED", "sub_code": "ND2", "sub_desc": "SCANNED ON TRUCK BUT NOT DELIVERED", "sub_cat_1": "Complete Unit", "sub_cat_2": "Missing", "sub_cat_3": "Complete Unit Not Delivered"},
#     {"type_code": "", "type_desc": "HOLE IN SCREEN MATERIAL", "prob_code": "HS1", "prob_desc": "HOLE IN SCREEN MATERIAL", "sub_code": "HS2", "sub_desc": "HOLE IN SCREEN MATERIAL", "sub_cat_1": "Screen", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Torn"}
# ]

# product_lines = ["EcoTech", "ClearView", "StarFrame Elite", "ProStyle", "ComfortPro", "Builder 3000", "VistaPro", "EliteView", "PremiumView", "OceanLight", "SeaView"]
# product_styles = ["Double Hung", "Fixed Casement", "Operating Casement", "Euroglide Patio Door", "Three Lite Slider", "Single Frame Twin Casement", "Two Lite Slider", "Miscellaneous Parts"]
# replaced_parts = ["Insulated Glass Unit", "Sash", "Screen", "Hardware", "Balance", "Complete Unit"]

# # Generate random date within a range
# def random_date(start_year, end_year):
#     start_date = datetime(start_year, 1, 1)
#     end_date = datetime(end_year, 12, 31)
#     delta = end_date - start_date
#     random_days = random.randint(0, delta.days)
#     return (start_date + timedelta(days=random_days)).strftime("%m/%d/%Y")

# # Generate the CSV data
# def generate_anonymized_data(num_rows=100):
#     headers = [
#         "BUSINESS_UNIT", "BUSINESS_UNIT_DWH", "BRAND", "TYPE_CODE", "TYPE_DESCRIPTION", 
#         "PROBLEM_CODE", "PROBLEM_CODE_DESCRIPTION", "SUB_CODE", "SUB_CODE_DESCRIPTION", 
#         "DATE1", "CUSTOMER_NUMBER", "CUSTOMER_NAME", "ORDER_NUMBER", "ORDER_LINE", 
#         "ORDER_SUB_LINE", "PARENT_ORDER_NUMBER", "PARENT_ORDER_LINE", "PARENT_ORDER_SUB_LINE", 
#         "INVOICING_PLANT_NAME", "COST", "MFG_DATE", "MFG_PLANT", "UNITS", "UOM", 
#         "PRODUCT_LINE", "PRODUCT_STYLE", "REPLACED_PART", "PO_NUMBER", "CODE_TYPE", 
#         "COPQ_INCLUDE", "FFR_INCLUDE", "COPQ_CATEGORY", "SUB_CATEGORY_1", "SUB_CATEGORY_2", 
#         "SUB_CATEGORY_3", "DW_LOAD_DATE", "PG_NAME", "INVOICE_DATE"
#     ]
    
#     rows = []
#     for i in range(num_rows):
#         problem = random.choice(problem_types)
#         order_number = random.randint(800000, 900000)
#         parent_order_number = random.randint(1000, 2000)
#         customer_number = random.randint(9000, 12000)
#         order_line = random.randint(1, 10)
#         units = random.randint(1, 3)
#         cost = round(random.uniform(0.1, 200.0), 2)
        
#         row = {
#             "BUSINESS_UNIT": random.choice(business_units),
#             "BUSINESS_UNIT_DWH": random.choice(business_unit_dwh),
#             "BRAND": random.choice(brands),
#             "TYPE_CODE": problem["type_code"],
#             "TYPE_DESCRIPTION": problem["type_desc"],
#             "PROBLEM_CODE": problem["prob_code"],
#             "PROBLEM_CODE_DESCRIPTION": problem["prob_desc"],
#             "SUB_CODE": problem["sub_code"],
#             "SUB_CODE_DESCRIPTION": problem["sub_desc"],
#             "DATE1": random_date(2024, 2025),
#             "CUSTOMER_NUMBER": customer_number,
#             "CUSTOMER_NAME": fake.company().upper(),
#             "ORDER_NUMBER": order_number,
#             "ORDER_LINE": float(order_line),
#             "ORDER_SUB_LINE": 0,
#             "PARENT_ORDER_NUMBER": parent_order_number,
#             "PARENT_ORDER_LINE": order_line,
#             "PARENT_ORDER_SUB_LINE": 0,
#             "INVOICING_PLANT_NAME": random.choice(invoicing_plant),
#             "COST": cost,
#             "MFG_DATE": random_date(1999, 2024),
#             "MFG_PLANT": random.choice(mfg_plants),
#             "UNITS": float(units),
#             "UOM": random.choice(uom),
#             "PRODUCT_LINE": random.choice(product_lines),
#             "PRODUCT_STYLE": random.choice(product_styles),
#             "REPLACED_PART": random.choice(replaced_parts),
#             "PO_NUMBER": f"PO{random.randint(1000, 9999)}",
#             "CODE_TYPE": random.choice(code_types),
#             "COPQ_INCLUDE": "No" if problem["type_desc"] in ["CUSTOMER STANDARD PURCHASE", "CUSTOMER CONCESSION", "OFFICE ERROR"] else "Yes",
#             "FFR_INCLUDE": "No" if problem["type_desc"] in ["CUSTOMER STANDARD PURCHASE", "CUSTOMER CONCESSION", "OFFICE ERROR"] else "Yes",
#             "COPQ_CATEGORY": "Not Included" if problem["type_desc"] in ["CUSTOMER STANDARD PURCHASE", "CUSTOMER CONCESSION", "OFFICE ERROR"] else "Warranty",
#             "SUB_CATEGORY_1": problem["sub_cat_1"],
#             "SUB_CATEGORY_2": problem["sub_cat_2"],
#             "SUB_CATEGORY_3": problem["sub_cat_3"],
#             "DW_LOAD_DATE": dw_load_date,
#             "PG_NAME": f"PG{random.randint(1, 30)}",
#             "INVOICE_DATE": random_date(2024, 2025)
#         }
#         rows.append(row)
    
#     # Write to CSV
#     with open("anonymized_sampled_data.csv", "w", newline="") as f:
#         writer = csv.DictWriter(f, fieldnames=headers)
#         writer.writeheader()
#         writer.writerows(rows)

# if __name__ == "__main__":
#     generate_anonymized_data(50000)
#     print("Anonymized CSV file 'anonymized_sampled_data.csv' generated successfully.")


###################################################################################################

import csv
import random
from datetime import datetime, timedelta
from faker import Faker
import uuid

# Initialize Faker for generating fake data
fake = Faker()

# Define static lists for consistent data generation
business_units = ["VisionTech Solutions"]
business_unit_dwh = ["VTX"]
brands = ["StarFrame"]
invoicing_plant = ["Dayton, OH"]
mfg_plants = ["Dayton, OH"]
uom = ["EA"]
code_types = ["Complaint"]
copq_includes = ["Yes", "No"]
ffr_includes = ["Yes", "No"]
copq_categories = ["Warranty", "Not Included"]

# Define problem types and their associated codes and descriptions
problem_types = [
    {"type_code": "", "type_desc": "SEAL FAILURE-LIFETIME/ORIG HOMEOWN", "prob_code": "SF1", "prob_desc": "SEAL FAILURE-LIFETIME/ORIG HOMEOWN", "sub_code": "SL1", "sub_desc": "SEAL FAILURE-LIFETIME/ORIG HOMEOWN", "sub_cat_1": "Insulated Glass Unit", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Seal Failure"},
    {"type_code": "", "type_desc": "SEAL FAILURE", "prob_code": "SF2", "prob_desc": "SEAL FAILURE", "sub_code": "SF3", "sub_desc": "SEAL FAILURE", "sub_cat_1": "Insulated Glass Unit", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Seal Failure"},
    {"type_code": "", "type_desc": "DIRT/PRINTS BETWEEN THE PANES", "prob_code": "DP1", "prob_desc": "DIRT/PRINTS BETWEEN THE PANES", "sub_code": "DP2", "sub_desc": "DIRT/PRINTS BETWEEN THE PANES", "sub_cat_1": "Insulated Glass Unit", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Debris - Smudge - Interior"},
    {"type_code": "", "type_desc": "LOWE - POOR QUALITY/DEFECTIVE", "prob_code": "LQ1", "prob_desc": "LOWE - POOR QUALITY/DEFECTIVE", "sub_code": "LQ2", "sub_desc": "LOWE - POOR QUALITY/DEFECTIVE", "sub_cat_1": "Insulated Glass Unit", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Low E Defects or Low-E on the wrong surface"},
    {"type_code": "", "type_desc": "BOWED SASH", "prob_code": "BS1", "prob_desc": "BOWED SASH", "sub_code": "BS2", "sub_desc": "BOWED SASH", "sub_cat_1": "Sash", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Out of Square - Bowed"},
    {"type_code": "", "type_desc": "CUSTOMER STANDARD PURCHASE", "prob_code": "CP1", "prob_desc": "CUSTOMER STANDARD PURCHASE", "sub_code": "CP2", "sub_desc": "CUSTOMER STANDARD PURCHASE", "sub_cat_1": "Complete Unit", "sub_cat_2": "Sales & Service", "sub_cat_3": "Samples and Displays"},
    {"type_code": "", "type_desc": "CUSTOMER CONCESSION", "prob_code": "CC1", "prob_desc": "CUSTOMER CONCESSION", "sub_code": "CC2", "sub_desc": "CUSTOMER CONCESSION", "sub_cat_1": "Complete Unit", "sub_cat_2": "Sales & Service", "sub_cat_3": "Customer Concession"},
    {"type_code": "", "type_desc": "OFFICE ERROR", "prob_code": "OE1", "prob_desc": "OFFICE ERROR", "sub_code": "OE2", "sub_desc": "OFFICE ERROR", "sub_cat_1": "Complete Unit", "sub_cat_2": "Sales & Service", "sub_cat_3": "Order Entry Error"},
    {"type_code": "", "type_desc": "BROKEN OR DAMAGED LOCKS AND KEEPER", "prob_code": "LK1", "prob_desc": "BROKEN OR DAMAGED LOCKS AND KEEPER", "sub_code": "LK2", "sub_desc": "BROKEN OR DAMAGED LOCKS AND KEEPER", "sub_cat_1": "Sash", "sub_cat_2": "Damage", "sub_cat_3": "During Delivery"},
    {"type_code": "", "type_desc": "PAINTED PRODUCT POOR QUALITY", "prob_code": "PP1", "prob_desc": "PAINTED PRODUCT POOR QUALITY", "sub_code": "PP2", "sub_desc": "PAINTED PRODUCT POOR QUALITY", "sub_cat_1": "Complete Unit", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Defective Paint"},
    {"type_code": "", "type_desc": "SCANNED ON TRUCK BUT NOT DELIVERED", "prob_code": "ND1", "prob_desc": "SCANNED ON TRUCK BUT NOT DELIVERED", "sub_code": "ND2", "sub_desc": "SCANNED ON TRUCK BUT NOT DELIVERED", "sub_cat_1": "Complete Unit", "sub_cat_2": "Missing", "sub_cat_3": "Complete Unit Not Delivered"},
    {"type_code": "", "type_desc": "HOLE IN SCREEN MATERIAL", "prob_code": "HS1", "prob_desc": "HOLE IN SCREEN MATERIAL", "sub_code": "HS2", "sub_desc": "HOLE IN SCREEN MATERIAL", "sub_cat_1": "Screen", "sub_cat_2": "Function - Aesthetics", "sub_cat_3": "Torn"}
]

product_lines = ["EcoTech", "ClearView", "StarFrame Elite", "ProStyle", "ComfortPro", "Builder 3000", "VistaPro", "EliteView", "PremiumView", "OceanLight", "SeaView"]
product_styles = ["Double Hung", "Fixed Casement", "Operating Casement", "Euroglide Patio Door", "Three Lite Slider", "Single Frame Twin Casement", "Two Lite Slider", "Miscellaneous Parts"]
replaced_parts = ["Insulated Glass Unit", "Sash", "Screen", "Hardware", "Balance", "Complete Unit"]

# Generate random date within a range in MM/DD/YYYY format
def random_date(start_year, end_year):
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return (start_date + timedelta(days=random_days)).strftime("%m/%d/%Y")

# Generate the CSV data
def generate_anonymized_data(num_rows=100):
    headers = [
        "BUSINESS_UNIT", "BUSINESS_UNIT_DWH", "BRAND", "TYPE_CODE", "TYPE_DESCRIPTION", 
        "PROBLEM_CODE", "PROBLEM_CODE_DESCRIPTION", "SUB_CODE", "SUB_CODE_DESCRIPTION", 
        "DATE1", "CUSTOMER_NUMBER", "CUSTOMER_NAME", "ORDER_NUMBER", "ORDER_LINE", 
        "ORDER_SUB_LINE", "PARENT_ORDER_NUMBER", "PARENT_ORDER_LINE", "PARENT_ORDER_SUB_LINE", 
        "INVOICING_PLANT_NAME", "COST", "MFG_DATE", "MFG_PLANT", "UNITS", "UOM", 
        "PRODUCT_LINE", "PRODUCT_STYLE", "REPLACED_PART", "PO_NUMBER", "CODE_TYPE", 
        "COPQ_INCLUDE", "FFR_INCLUDE", "COPQ_CATEGORY", "SUB_CATEGORY_1", "SUB_CATEGORY_2", 
        "SUB_CATEGORY_3", "DW_LOAD_DATE", "PG_NAME", "INVOICE_DATE"
    ]
    
    rows = []
    for i in range(num_rows):
        problem = random.choice(problem_types)
        order_number = random.randint(800000, 900000)
        parent_order_number = random.randint(1000, 2000)
        customer_number = random.randint(9000, 12000)
        order_line = random.randint(1, 10)
        units = random.randint(1, 3)
        cost = round(random.uniform(0.1, 200.0), 2)
        
        row = {
            "BUSINESS_UNIT": random.choice(business_units),
            "BUSINESS_UNIT_DWH": random.choice(business_unit_dwh),
            "BRAND": random.choice(brands),
            "TYPE_CODE": problem["type_code"],
            "TYPE_DESCRIPTION": problem["type_desc"],
            "PROBLEM_CODE": problem["prob_code"],
            "PROBLEM_CODE_DESCRIPTION": problem["prob_desc"],
            "SUB_CODE": problem["sub_code"],
            "SUB_CODE_DESCRIPTION": problem["sub_desc"],
            "DATE1": random_date(2024, 2025),
            "CUSTOMER_NUMBER": customer_number,
            "CUSTOMER_NAME": fake.company().upper(),
            "ORDER_NUMBER": order_number,
            "ORDER_LINE": float(order_line),
            "ORDER_SUB_LINE": 0,
            "PARENT_ORDER_NUMBER": parent_order_number,
            "PARENT_ORDER_LINE": order_line,
            "PARENT_ORDER_SUB_LINE": 0,
            "INVOICING_PLANT_NAME": random.choice(invoicing_plant),
            "COST": cost,
            "MFG_DATE": random_date(1999, 2024),
            "MFG_PLANT": random.choice(mfg_plants),
            "UNITS": float(units),
            "UOM": random.choice(uom),
            "PRODUCT_LINE": random.choice(product_lines),
            "PRODUCT_STYLE": random.choice(product_styles),
            "REPLACED_PART": random.choice(replaced_parts),
            "PO_NUMBER": f"PO{random.randint(1000, 9999)}",
            "CODE_TYPE": random.choice(code_types),
            "COPQ_INCLUDE": "No" if problem["type_desc"] in ["CUSTOMER STANDARD PURCHASE", "CUSTOMER CONCESSION", "OFFICE ERROR"] else "Yes",
            "FFR_INCLUDE": "No" if problem["type_desc"] in ["CUSTOMER STANDARD PURCHASE", "CUSTOMER CONCESSION", "OFFICE ERROR"] else "Yes",
            "COPQ_CATEGORY": "Not Included" if problem["type_desc"] in ["CUSTOMER STANDARD PURCHASE", "CUSTOMER CONCESSION", "OFFICE ERROR"] else "Warranty",
            "SUB_CATEGORY_1": problem["sub_cat_1"],
            "SUB_CATEGORY_2": problem["sub_cat_2"],
            "SUB_CATEGORY_3": problem["sub_cat_3"],
            "DW_LOAD_DATE": random_date(2024, 2025),
            "PG_NAME": f"PG{random.randint(1, 30)}",
            "INVOICE_DATE": random_date(2024, 2025)
        }
        rows.append(row)
    
    # Write to CSV
    with open("anonymized_sampled_data.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

# if __name__ == "__main__":
#     generate_anonymized_data(200000)
#     print("Anonymized CSV file 'anonymized_sampled_data.csv' generated successfully.")