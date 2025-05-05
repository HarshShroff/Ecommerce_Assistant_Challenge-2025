import pandas as pd
import logging

logger = logging.getLogger(__name__)

def get_order_details(customer_id):
    """
    Mock API function to retrieve order details for a specific customer.
    
    Args:
        customer_id (int): The customer ID to retrieve orders for
        
    Returns:
        pandas.DataFrame: DataFrame containing the customer's orders
    """
    try:
        # Load the order dataset
        orders_df = pd.read_csv('/data/Order_Data_Dataset.csv')
        
        # Filter orders for the specified customer
        customer_orders = orders_df[orders_df['Customer_Id'] == int(customer_id)]
        
        if customer_orders.empty:
            logger.warning(f"No orders found for customer ID: {customer_id}")
        else:
            logger.info(f"Found {len(customer_orders)} orders for customer ID: {customer_id}")
            
        return customer_orders
    except Exception as e:
        logger.error(f"Error in get_order_details: {e}")
        # Return empty DataFrame in case of error
        return pd.DataFrame()
