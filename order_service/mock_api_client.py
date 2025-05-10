# mock_api_client.py

import os
import pandas as pd

# Load dataset once
DATASET_PATH = os.environ.get("DATA_PATH", "/data/Order_Data_Dataset.csv")
_df = pd.read_csv(DATASET_PATH)
_df.fillna("", inplace=True)

# coerce numeric columns
for col in ["Sales", "Profit", "Shipping_Cost"]:
    _df[col] = pd.to_numeric(_df[col], errors="coerce").fillna(0.0)

def get_all_data():
    return _df.to_dict(orient="records")

def get_customer_data(customer_id: int):
    filtered = _df[_df["Customer_Id"] == customer_id]
    if filtered.empty:
        return {"error": f"No data found for Customer ID {customer_id}"}
    return filtered.to_dict(orient="records")

def get_product_category_data(category: str):
    filt = _df[_df["Product_Category"].str.contains(category, case=False, na=False)]
    if filt.empty:
        return {"error": f"No data found for Product Category '{category}'"}
    return filt.to_dict(orient="records")

def get_orders_by_priority(priority: str):
    filt = _df[_df["Order_Priority"].str.contains(priority, case=False, na=False)]
    if filt.empty:
        return {"error": f"No data found for Order Priority '{priority}'"}
    return filt.to_dict(orient="records")

def total_sales_by_category():
    summary = (
        _df.groupby("Product_Category", as_index=False)["Sales"]
           .sum()
    )
    return summary.to_dict(orient="records")

def high_profit_products(min_profit: float = 100.0):
    filt = _df[_df["Profit"] > min_profit]
    if filt.empty:
        return {"error": f"No products found with profit > {min_profit}"}
    return filt.to_dict(orient="records")

def shipping_cost_summary():
    return {
        "average_shipping_cost": _df["Shipping_Cost"].mean(),
        "min_shipping_cost":     _df["Shipping_Cost"].min(),
        "max_shipping_cost":     _df["Shipping_Cost"].max(),
    }

def profit_by_gender():
    summary = (
        _df.groupby("Gender", as_index=False)["Profit"]
           .sum()
    )
    return summary.to_dict(orient="records")
