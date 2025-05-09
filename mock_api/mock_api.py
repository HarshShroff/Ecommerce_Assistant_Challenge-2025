# mock_api/mock_api.py
import os
import pandas as pd
from fastapi import FastAPI

# Point at the real CSV (inside Docker/container or local)
DATASET_PATH = os.environ.get(
    "ORDER_DATA_CSV",
    os.path.abspath(os.path.join(os.path.dirname(__file__),
                                 "../data/Order_Data_Dataset.csv"))
)
df = pd.read_csv(DATASET_PATH, on_bad_lines="skip")
df.fillna("", inplace=True)

app = FastAPI(
    title="E-Commerce Order Dataset API",
    description="Expose order analytics endpoints for the e-commerce assistant",
)

@app.get("/data")
def get_all_data():
    return df.to_dict(orient="records")

@app.get("/data/customer/{customer_id}")
def get_customer_data(customer_id: int):
    filtered = df[df["Customer_Id"] == customer_id]
    if filtered.empty:
        return {"error": f"No data found for Customer ID {customer_id}"}
    return filtered.to_dict(orient="records")

@app.get("/data/product-category/{category}")
def get_product_category_data(category: str):
    filtered = df[df["Product_Category"]
                  .str.contains(category, case=False, na=False)]
    if filtered.empty:
        return {"error": f"No data for category '{category}'"}
    return filtered.to_dict(orient="records")

@app.get("/data/order-priority/{priority}")
def get_orders_by_priority(priority: str):
    filtered = df[df["Order_Priority"]
                  .str.contains(priority, case=False, na=False)]
    if filtered.empty:
        return {"error": f"No orders with priority '{priority}'"}
    return filtered.to_dict(orient="records")

@app.get("/data/total-sales-by-category")
def total_sales_by_category():
    summary = (
        df.groupby("Product_Category")["Sales"]
          .sum()
          .reset_index()
    )
    return summary.to_dict(orient="records")

@app.get("/data/high-profit-products")
def high_profit_products(min_profit: float = 100.0):
    filtered = df[df["Profit"] > min_profit]
    if filtered.empty:
        return {"error": f"No products with profit > {min_profit}"}
    return filtered.to_dict(orient="records")

@app.get("/data/shipping-cost-summary")
def shipping_cost_summary():
    return {
        "average_shipping_cost": df["Shipping_Cost"].mean(),
        "min_shipping_cost": df["Shipping_Cost"].min(),
        "max_shipping_cost": df["Shipping_Cost"].max()
    }

@app.get("/data/profit-by-gender")
def profit_by_gender():
    summary = (
        df.groupby("Gender")["Profit"]
          .sum()
          .reset_index()
    )
    return summary.to_dict(orient="records")
