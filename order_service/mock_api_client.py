import pandas as pd
import logging
import os # Import os

logger = logging.getLogger(__name__)

# Load the dataset once when the module is imported - CORRECTED PATH
ORDERS_DF = None
try:
    # Use the absolute path inside the container
    csv_path = '../data/Order_Data_Dataset.csv'
    if os.path.exists(csv_path):
        ORDERS_DF = pd.read_csv(csv_path, on_bad_lines='skip')
        logger.info(f"Successfully loaded order data in mock client from {csv_path}")
    else:
        logger.error(f"FATAL: Order CSV file not found at {csv_path}")
        ORDERS_DF = pd.DataFrame()
except Exception as e:
    logger.error(f"FATAL: Error loading order dataset in mock client: {e}")
    ORDERS_DF = pd.DataFrame()

def get_order_details(customer_id: int) -> pd.DataFrame:
    """
    Mock API function to retrieve order details for a specific customer.

    Args:
        customer_id (int): The customer ID to retrieve orders for

    Returns:
        pandas.DataFrame: DataFrame containing the customer's orders, empty if not found.
    """
    if ORDERS_DF is None or ORDERS_DF.empty:
        logger.error("Order dataset is not loaded or is empty.")
        return pd.DataFrame()

    try:
        # Ensure Customer_Id column exists and is of a comparable type
        if 'Customer_Id' not in ORDERS_DF.columns:
            logger.error("Column 'Customer_Id' not found in the DataFrame.")
            return pd.DataFrame()

        # Filter orders for the specified customer
        # Convert column to numeric if needed, coercing errors
        orders_df_customer_id = pd.to_numeric(ORDERS_DF['Customer_Id'], errors='coerce')
        customer_orders = ORDERS_DF[orders_df_customer_id == customer_id]

        if customer_orders.empty:
            logger.warning(f"No orders found for customer ID: {customer_id}")
        else:
            logger.info(f"Found {len(customer_orders)} orders for customer ID: {customer_id}")

        return customer_orders
    except Exception as e:
        logger.error(f"Error in get_order_details for customer {customer_id}: {e}", exc_info=True) # Log traceback
        # Return empty DataFrame in case of error
        return pd.DataFrame()

