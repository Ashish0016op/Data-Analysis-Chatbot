DATA_SCHEMA = [
    {
      "field": "BUSINESS_UNIT",
      "description": "The specific business unit or division within the company responsible for the product or service. This field helps in identifying which part of the organization is handling the issue.",
      "type": "string",
      "example": "Apertures Solution - US",
      "Importance":"HIGH"
    },
    {
      "field": "BUSINESS_UNIT_DWH",
      "description": "An internal classification code or data warehouse identifier for the business unit. This code is used to categorize and manage data related to different business units within the company's data systems.",
      "type": "string",
      "example": "ATRIUM",
      "Importance":"MEDIUM"
    },
    {
      "field": "BRAND",
      "description": "The brand name associated with the product. This field identifies the specific brand under which the product is marketed and sold.",
      "type": "string",
      "example": "PlyGem",
      "Importance":"LOW"
    },
    {
      "field": "TYPE_CODE",
      "description": "A classification code for the type of product or issue. This field is currently empty in the dataset but is intended to categorize products or issues based on predefined codes.",
      "type": "string",
      "example": "700",
      "Importance":"LOW"   
    },
    {
      "field": "TYPE_DESCRIPTION",
      "description": "A description of the type of product issue or complaint. This field provides more context about the nature of the problem, such as whether it is related to warranty or other issues.",
      "type": "string",
      "example": "COMPLETE UNIT WRONG",
      "Importance":"LOW"
    },
    {
      "field": "PROBLEM_CODE",
      "description": "it is just a code for specific code assigned to the reported problem. This field provides a unique identifier for different types of issues.",
      "type": "string",
      "example": "R23",
      "Importance":"LOW"
    },
    {
      "field": "PROBLEM_CODE_DESCRIPTION",
      "description": "Additional details about the specific problem reported. This field provides a more detailed explanation of the issue, such as the component or aspect of the product that is affected.",
      "type": "string",
      "example": "Order not received but Invoiced",
      "Importance":"LOW"
    },
    {
      "field": "SUB_CODE",
      "description": "A more granular classification of the issue. This field is currently empty in the dataset but This field  provides a sub-category for the problem, allowing for more detailed analysis.",
      "type": "Integer",
      "Importance":"LOW",
      "example": 20
    },
    {
      "field": "SUB_CODE_DESCRIPTION",
      "description": "A description of the sub-classification of the problem. This field provides additional context about the specific nature of the issue, such as defects in particular components.",
      "type": "string",
      "Importance":"LOW",
      "example": "Seal Failure"
    },
    {
      "field": "DATE1",
      "description": "The date when the complaint or issue was reported. This field helps in tracking the timeline of issues and understanding when they occurred In this field data having two date formats 07/18/23(mm/dd/yy) and 08-12-2024(dd-mm-yyyy).",
      "type": "date",
      "Importance":"HIGH",
      "example": "2/21/2025"
    },
    {
      "field": "CUSTOMER_NUMBER",
      "description": "A unique identifier for the customer who reported the issue. This field helps in tracking issues related to specific customers and managing customer relationships.",
      "type": "Integer",
      "Importance":"LOW",
      "example": 467526
    },
    {
      "field": "CUSTOMER_NAME",
      "description": "The name of the customer who reported the issue. This field provides the identity of the customer, which is useful for communication and follow-up purposes.",
      "type": "string",
      "Importance":"MEDIUM",
      "example": "BILTMORE HOMES"
    },
    {
      "field": "ORDER_NUMBER",
      "description": "A unique identifier for the specific order associated with the issue. This field helps in tracking which orders have reported problems and managing order-related data.",
      "type": "integer",
      "Importance":"MEDIUM",
      "example": 10420925
    },
    {
      "field": "ORDER_LINE",
      "description": "Specifies the line item within the order that is associated with the issue. This field helps in identifying the specific product or service within an order that has a problem.",
      "type": "integer",
      "Importance":"MEDIUM",
      "example": 1
    },
    {
      "field": "ORDER_SUB_LINE",
      "description": "A further subdivision of the order line. This field is currently empty in the dataset but is intended to provide more detailed information about the order line item.",
      "type": "string",
      "Importance":"LOW",
      "example": ""
    },
    {
      "field": "PARENT_ORDER_NUMBER",
      "description": "An identifier for a related parent order. This field is currently empty in the dataset but is intended to link the issue to a higher-level or related order.",
      "type": "string",
      "Importance":"LOW",
      "example": ""
    },
    {
      "field": "PARENT_ORDER_LINE",
      "description": "An identifier for the line item within a related parent order. This field is currently empty in the dataset but is intended to provide more context about the relationship between orders.",
      "type": "string",
      "Importance":"LOW",
      "example": ""
    },
    {
      "field": "PARENT_ORDER_SUB_LINE",
      "description": "A further subdivision of the line item within a related parent order. This field is currently empty in the dataset but is intended to provide detailed information about the parent order line item.",
      "type": "string",
      "Importance":"LOW",
      "example": ""
    },
    {
      "field": "INVOICING_PLANT_NAME",
      "description": "The location of the plant responsible for invoicing the order. This field helps in identifying which facility handled the financial aspects of the order.This field is prioritized over MFG_PLANT for plant-based analysis unless manufacturing data is specifically requested.",
      "type": "string",
      "Importance":"HIGH",
      "example": "Dallas, TX"
    },
    {
      "field": "COST",
      "description": "The cost associated with the complaint or replacement. This field tracks the financial impact of the issue, including costs for repairs, replacements, or other remedies.",
      "type": "float",
      "Importance":"HIGH",
      "example": 97.49
    },
    {
      "field": "MFG_DATE",
      "description": "The manufacturing date of the product associated with the issue. This field helps in identifying when the product was produced, which can be useful for quality control and warranty purposes In this field data having two date formats 07/18/23(mm/dd/yy) and 08-12-2024(dd-mm-yyyy).",
      "type": "date",
      "Importance":"HIGH",
      "example": "08-MAY-19"
    },
    {
      "field": "MFG_PLANT",
      "description": "The location where the product was manufactured. This field helps in identifying which facility produced the product, which can be useful for tracking quality issues.",
      "type": "string",
      "Importance":"LOW",
      "example": "Dallas, TX"
    },
    {
      "field": "UNITS",
      "description": "The number of units involved in the complaint. This field tracks the quantity of products affected by the issue, which is useful for understanding the scale of the problem.",
      "type": "integer",
      "Importance":"MEDIUM",
      "example": 2
    },
    {
      "field": "UOM",
      "description": "The unit of measure for the units involved in the complaint. This field specifies the measurement unit used to quantify the affected products, such as 'each' (EA).",
      "type": "string",
      "Importance":"MEDIUM",
      "example": "EA"
    },
    {
      "field": "PRODUCT_LINE",
      "description": "A specific product line identifier. This field categorizes the product within a specific line or family of products, which is useful for analyzing issues related to particular product lines.",
      "type": "string",
      "Importance":"MEDIUM",
      "example": "P1100"
    },
    {
      "field": "PRODUCT_STYLE",
      "description": "A style code representing different variations of the product. This field helps in identifying specific styles or models of the product that may be affected by the issue.",
      "type": "string",
      "Importance":"MEDIUM",
      "example": "PW"
    },
    {
      "field": "REPLACED_PART",
      "description": "Information about replacement parts used to address the issue. This field is currently empty in the dataset but is intended to track which parts were replaced as part of the resolution process.",
      "type": "string",
      "Importance":"LOW",
      "example": ""
    },
    {
      "field": "PO_NUMBER",
      "description": "The purchase order number associated with the issue. This field helps in tracking the original purchase order related to the complaint, which is useful for financial and logistical purposes.",
      "type": "string",
      "Importance":"LOW",
      "example": "14061444"
    },
    {
      "field": "CODE_TYPE",
      "description": "Indicates the type of record, such as a complaint. This field helps in categorizing the nature of the record within the dataset.",
      "type": "string",
      "Importance":"LOW",
      "example": "Complaint and Credit"
    },
    {
      "field": "COPQ_INCLUDE",
      "description": "Indicates whether the issue is included in Cost of Poor Quality (COPQ) calculations. This field helps in tracking the financial impact of quality issues on the organization.",
      "type": "string",
      "Importance":"MEDIUM",
      "example": "Yes"
    },
    {
      "field": "FFR_INCLUDE",
      "description": "Indicates whether the issue is related to First Failure Report (FFR) tracking. This field helps in identifying and analyzing the first occurrences of specific problems.",
      "type": "string",
      "Importance":"LOW",
      "example": "Yes"
    },
    {
      "field": "COPQ_CATEGORY",
      "description": "Categorizes the issue under specific quality-related categories, such as warranty claims. This field helps in organizing and analyzing issues based on their impact on quality.",
      "type": "string",
      "Importance":"HIGH",
      "example": "Customer Concession"
    },
    {
      "field": "SUB_CATEGORY_1",
      "description": "A more specific categorization of the issue. This field provides a detailed classification of the problem, such as the type of component or aspect of the product affected.",
      "type": "string",
      "Importance":"LOW",
      "example": "Insulated Glass Unit"
    },
    {
      "field": "SUB_CATEGORY_2",
      "description": "Further specifies the nature of the problem. This field provides additional context about the issue, such as whether it is related to function or aesthetics.",
      "type": "string",
      "Importance":"LOW",
      "example": "Function - Aesthetics"
    },
    {
      "field": "SUB_CATEGORY_3",
      "description": "The most specific description of the issue. This field provides detailed information about the problem, such as the type of defect or failure.",
      "type": "string",
      "Importance":"VERY HIGH",
      "example": "Seal Failure"
    },
    {
      "field": "PG_NAME",
      "description": "The program or department responsible for handling the complaint. This field identifies which part of the organization is managing the issue, which is useful for coordination and communication.",
      "type": "string",
      "Importance":"MEDIUM",
      "example": "Darling Homes LLC"
    },
  {
    "field": "INVOICE_DATE",
    "description": "The date when the order was invoiced. This field is prioritized for date-based analysis and helps track financial processing timelines.",
    "type": "date",
    "Importance":"HIGH",
    "example": "3/15/2025"
  }
]
