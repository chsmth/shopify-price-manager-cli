import requests
import json
import os
import time
import datetime
import logging
from colorama import init, Fore, Style
init(autoreset=True)
from tqdm import tqdm

class TqdmLoggingHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
        except Exception:
            self.handleError(record)

class ColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        level_color = self.LEVEL_COLORS.get(record.levelno, "")
        record.levelname = f"{level_color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
        except Exception:
            self.handleError(record)

import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SHOP_NAME = os.getenv('SHOP_NAME')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
API_VERSION = "2025-04"

# Directory for storing price backups
BACKUP_DIR = "price_backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

# Directory for logs
LOG_DIR = "price_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Mock mode - When True, no actual updates are sent to the API
MOCK_MODE = False

# Set up logging

def setup_logging(operation_name=None):
    """Set up logging to both console and file using tqdm.write for terminal output"""
    # Clear any existing handlers
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Set up tqdm-aware console handler
    console_handler = TqdmLoggingHandler()
    console_handler.setFormatter(ColorFormatter("%(asctime)s - %(levelname)s - %(message)s"))

    # Add console handler
    root_logger.addHandler(console_handler)

    # Optionally set up file logging
    if operation_name:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{operation_name}_{timestamp}.log"
        log_path = os.path.join(LOG_DIR, log_filename)

        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        root_logger.setLevel(logging.INFO)
        logging.info(f"Logging to file: {log_path}")
        return log_path
    else:
        root_logger.setLevel(logging.INFO)
        return None
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Set up console handler
    console_handler = TqdmLoggingHandler()
    console_handler.setFormatter(ColorFormatter("%(asctime)s - %(levelname)s - %(message)s"))
    
    # Set up file handler if operation_name is provided
    if operation_name:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{operation_name}_{timestamp}.log"
        log_path = os.path.join(LOG_DIR, log_filename)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        
        # Configure root logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        root_logger.setLevel(logging.INFO)
        
        logging.info(f"Logging to file: {log_path}")
        return log_path
    else:
        # Configure root logger for console only
        root_logger.addHandler(console_handler)
        root_logger.setLevel(logging.INFO)
        return None

# API URL
base_url = f"https://{SHOP_NAME}/admin/api/{API_VERSION}/graphql.json"

# Headers
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ACCESS_TOKEN
}

def fetch_product(product_id):
    """Fetch a single product and its variants"""
    query = """
    query GetProduct($productId: ID!) {
        product(id: $productId) {
            id
            title
            handle
            variants(first: 100) {
                edges {
                    node {
                        id
                        title
                        sku
                        price
                        compareAtPrice
                    }
                }
            }
        }
    }
    """
    
    variables = {
        "productId": product_id
    }
    
    response = requests.post(
        base_url,
        headers=headers,
        json={"query": query, "variables": variables}
    )
    
    data = response.json()
    
    if "errors" in data:
        logging.error(f"Error fetching product {product_id}: {data['errors']}")
        return None
    
    return data["data"]["product"]

def fetch_products_by_collection(collection_id, cursor=None, batch_size=10):
    """Fetch products in a collection with pagination"""
    query = """
    query GetProductsByCollection($collectionId: ID!, $cursor: String, $batchSize: Int!) {
        collection(id: $collectionId) {
            id
            title
            products(first: $batchSize, after: $cursor) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                edges {
                    node {
                        id
                        title
                        handle
                        variants(first: 100) {
                            edges {
                                node {
                                    id
                                    title
                                    sku
                                    price
                                    compareAtPrice
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    variables = {
        "collectionId": collection_id,
        "batchSize": batch_size
    }
    
    if cursor:
        variables["cursor"] = cursor
    
    response = requests.post(
        base_url,
        headers=headers,
        json={"query": query, "variables": variables}
    )
    
    data = response.json()
    
    if "errors" in data:
        logging.error(f"Error fetching collection products: {data['errors']}")
        return [], None, None
    
    try:
        collection_data = data["data"]["collection"]
        collection_title = collection_data["title"]
        products_data = collection_data["products"]
        products = [edge["node"] for edge in products_data["edges"]]
        page_info = products_data["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        end_cursor = page_info["endCursor"] if has_next_page else None
        
        return products, collection_title, end_cursor
    except Exception as e:
        logging.error(f"Error processing collection data: {e}")
        return [], None, None

def fetch_all_collections():
    """Fetch all collections in the shop"""
    query = """
    query {
        collections(first: 50) {
            edges {
                node {
                    id
                    title
                    productsCount
                }
            }
        }
    }
    """
    
    response = requests.post(
        base_url,
        headers=headers,
        json={"query": query}
    )
    
    data = response.json()
    
    if "errors" in data:
        logging.error(f"Error fetching collections: {data['errors']}")
        return []
    
    collections = []
    for edge in data["data"]["collections"]["edges"]:
        collection = edge["node"]
        collections.append({
            "id": collection["id"],
            "title": collection["title"],
            "productsCount": collection["productsCount"]
        })
    
    return collections

def fetch_all_products(cursor=None, batch_size=50):
    """Fetch all products in the shop with pagination"""
    query = """
    query GetProducts($cursor: String, $batchSize: Int!) {
        products(first: $batchSize, after: $cursor) {
            pageInfo {
                hasNextPage
                endCursor
            }
            edges {
                node {
                    id
                    title
                    handle
                    variants(first: 100) {
                        edges {
                            node {
                                id
                                title
                                sku
                                price
                                compareAtPrice
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    variables = {
        "batchSize": batch_size
    }
    
    if cursor:
        variables["cursor"] = cursor
    
    response = requests.post(
        base_url,
        headers=headers,
        json={"query": query, "variables": variables}
    )
    
    data = response.json()
    
    if "errors" in data:
        logging.error(f"Error fetching products: {data['errors']}")
        return [], None
    
    products_data = data["data"]["products"]
    products = [edge["node"] for edge in products_data["edges"]]
    page_info = products_data["pageInfo"]
    has_next_page = page_info["hasNextPage"]
    end_cursor = page_info["endCursor"] if has_next_page else None
    
    return products, end_cursor

def fetch_price_lists():
    """Fetch all price lists in the shop"""
    query = """
    query {
        priceLists(first: 20) {
            edges {
                node {
                    id
                    name
                    currency
                }
            }
        }
    }
    """
    
    response = requests.post(
        base_url,
        headers=headers,
        json={"query": query}
    )
    
    data = response.json()
    
    if "errors" in data:
        logging.error(f"Error fetching price lists: {data['errors']}")
        return []
    
    price_lists = []
    try:
        price_list_edges = data["data"]["priceLists"]["edges"]
        for edge in price_list_edges:
            price_list = edge["node"]
            price_lists.append(price_list)
    except Exception as e:
        logging.error(f"Error processing price lists: {e}")
    
    logging.info(f"Found {len(price_lists)} price lists in the shop")
    return price_lists

def fetch_market_prices_for_product(price_list_id, product_id):
    """Fetch market-specific prices for a product in a price list"""
    # First, get the price list details to know its currency
    price_list_query = """
    query GetPriceList($priceListId: ID!) {
        priceList(id: $priceListId) {
            id
            name
            currency
        }
    }
    """
    
    variables = {
        "priceListId": price_list_id
    }
    
    response = requests.post(
        base_url,
        headers=headers,
        json={"query": price_list_query, "variables": variables}
    )
    
    data = response.json()
    
    if "errors" in data:
        logging.error(f"Error fetching price list details: {data['errors']}")
        return None
    
    try:
        price_list_data = data["data"]["priceList"]
        price_list_currency = price_list_data.get("currency", "USD")
        price_list_name = price_list_data.get("name", "Unknown")
        logging.info(f"Processing price list: {price_list_name} ({price_list_currency})")
    except Exception as e:
        logging.error(f"Error extracting price list details: {e}")
        return None
    
    # Now, fetch product variants to get their IDs
    product = fetch_product(product_id)
    if not product:
        return None
    
    # Get all variant IDs for this product
    variant_ids = []
    variant_id_parts = []
    for variant_edge in product["variants"]["edges"]:
        variant = variant_edge["node"]
        variant_ids.append(variant["id"])
        # Extract the numeric part of the variant ID for the query
        variant_id_parts.append(variant["id"].split("/")[-1])
    
    # Build a query string that will find variants for this product
    # Use the variant_id: syntax in the query parameter
    query_string = ""
    if len(variant_id_parts) > 0:
        query_string = "variant_id:" + " OR variant_id:".join(variant_id_parts)
    
    # Use the correct query format based on the schema
    query = """
    query GetPriceListPrices($priceListId: ID!, $queryString: String) {
        priceList(id: $priceListId) {
            prices(first: 100, query: $queryString) {
                nodes {
                    price {
                        amount
                        currencyCode
                    }
                    compareAtPrice {
                        amount
                        currencyCode
                    }
                    variant {
                        id
                    }
                }
            }
        }
    }
    """
    
    variables = {
        "priceListId": price_list_id,
        "queryString": query_string
    }
    
    response = requests.post(
        base_url,
        headers=headers,
        json={"query": query, "variables": variables}
    )
    
    data = response.json()
    
    if "errors" in data:
        logging.error(f"Error fetching market prices: {data['errors']}")
        return None
    
    prices = []
    try:
        price_nodes = data["data"]["priceList"]["prices"]["nodes"]
        for node in price_nodes:
            # Format the price data in our expected structure
            price_data = {
                "variant_id": node["variant"]["id"],
                "price": node["price"],
                "compare_at_price": node.get("compareAtPrice")
            }
            prices.append(price_data)
    except Exception as e:
        logging.error(f"Error processing price list data: {e}")
        prices = []
    
    if len(prices) > 0:
        logging.info(f"Found {len(prices)} prices for product in price list {price_list_name}")
    
    # Store price list metadata along with the prices
    return {
        "prices": prices,
        "currency": price_list_currency,
        "name": price_list_name
    }

def backup_product(product_id):
    """Backup a single product's prices and its market-specific prices"""
    logging.info(f"Backing up prices for product ID: {product_id}")
    
    # 1. Fetch the product data
    product = fetch_product(product_id)
    if not product:
        logging.error(f"Failed to fetch product {product_id}. Skipping.")
        return None
    
    logging.info(f"Product: {product['title']}")
    
    # 2. Get all price lists
    price_lists = fetch_price_lists()
    
    # 3. Fetch market prices for this product
    market_prices = {}
    for price_list in price_lists:
        price_list_id = price_list["id"]
        price_list_data = fetch_market_prices_for_product(price_list_id, product_id)
        
        # Only store price lists with prices for this product
        if price_list_data and price_list_data["prices"]:
            market_prices[price_list_id] = price_list_data
    
    # 4. Create backup data structure
    backup_data = {
        "metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "shop": SHOP_NAME,
            "product_id": product_id,
            "product_title": product.get("title", "Unknown")
        },
        "product": product,
        "market_prices": market_prices
    }
    
    return backup_data

def backup_products(products, backup_name=None):
    """Backup multiple products"""
    if not backup_name:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"bulk_backup_{timestamp}"
    
    backup_path = os.path.join(BACKUP_DIR, f"{backup_name}.json")
    
    all_backups = {}
    success_count = 0
    error_count = 0
    
    logging.info(f"Starting backup of {len(products)} products...")
    
    for i, product in enumerate(tqdm(products, desc="Backing up products")):
        product_id = product["id"]
        try:
            logging.info(f"[{i+1}/{len(products)}] Backing up: {product['title']} (ID: {product_id})")
            backup_data = backup_product(product_id)
            
            if backup_data:
                all_backups[product_id] = backup_data
                success_count += 1
            else:
                logging.warning(f"No backup data returned for {product['title']} (ID: {product_id})")
                error_count += 1
                
            # Be nice to the API - add small delay between products
            if i < len(products) - 1:
                time.sleep(0.5)
        
        except Exception as e:
            logging.error(f"Error backing up product {product_id}: {e}")
            error_count += 1
    
    # Save the combined backup
    with open(backup_path, 'w') as f:
        json.dump(all_backups, f, indent=2)
    
    logging.info(f"Backup completed: {success_count} products backed up successfully, {error_count} errors")
    logging.info(f"Backup saved to: {backup_path}")
    
    return backup_path

def update_product_variants_prices(product_id, variants_data, mock=MOCK_MODE):
    """Update prices for a product's variants"""
    if not variants_data:
        return False
    
    # When in mock mode, just simulate success and print the data
    if mock:
        logging.info(f"MOCK: Would update prices for product {product_id}")
        logging.info(f"MOCK: Data: {variants_data[:3]}... (and {len(variants_data) - 3} more variants)")
        return True
    
    mutation = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
        productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            product {
                id
                title
            }
            productVariants {
                id
                title
                price
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    variables = {
        "productId": product_id,
        "variants": variants_data
    }
    
    response = requests.post(
        base_url,
        headers=headers,
        json={"query": mutation, "variables": variables}
    )
    
    data = response.json()
    
    if "errors" in data:
        logging.error(f"Error updating variants: {data['errors']}")
        return False
    
    user_errors = data["data"]["productVariantsBulkUpdate"]["userErrors"]
    if user_errors:
        logging.error(f"User errors updating variants: {user_errors}")
        return False
    
    return True

def update_price_list_prices(price_list_id, variant_prices, mock=MOCK_MODE):
    """Update market-specific prices for variants"""
    if not variant_prices:
        return True
    
    # When in mock mode, just simulate success and print the data
    if mock:
        logging.info(f"MOCK: Would update market prices for price list {price_list_id}")
        logging.info(f"MOCK: Data: {variant_prices[:3]}... (and {len(variant_prices) - 3} more variants)")
        return True
    
    mutation = """
    mutation priceListFixedPricesAdd($priceListId: ID!, $prices: [PriceListPriceInput!]!) {
        priceListFixedPricesAdd(priceListId: $priceListId, prices: $prices) {
            prices {
                price {
                    amount
                    currencyCode
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    # Convert variant prices to the format expected by the API
    api_prices = []
    for price_data in variant_prices:
        variant_id = price_data["variant_id"]
        price = price_data["price"]
        
        api_price = {
            "variantId": variant_id,
            "price": price
        }
        
        # Add compareAtPrice if it exists
        if price_data.get("compare_at_price"):
            api_price["compareAtPrice"] = price_data["compare_at_price"]
        
        api_prices.append(api_price)
    
    variables = {
        "priceListId": price_list_id,
        "prices": api_prices
    }
    
    response = requests.post(
        base_url,
        headers=headers,
        json={"query": mutation, "variables": variables}
    )
    
    data = response.json()
    
    if "errors" in data:
        logging.error(f"Error updating price list: {data['errors']}")
        return False
    
    user_errors = data["data"]["priceListFixedPricesAdd"]["userErrors"]
    if user_errors:
        logging.error(f"User errors updating price list: {user_errors}")
        return False
    
    return True

def apply_discount_to_product_data(product_data, discount_percentage=20, set_compare_at_price=True):
    """Apply a discount to product data (without API calls)"""
    product_id = product_data["product"]["id"]
    product_title = product_data["product"]["title"]
    
    logging.info(f"Processing discount for product: {product_title} (ID: {product_id})")
    
    # 1. Calculate discounted variant prices
    product = product_data["product"]
    variants = product["variants"]["edges"]
    
    variants_data = []
    for variant_edge in variants:
        variant = variant_edge["node"]
        variant_id = variant["id"]
        original_price = variant["price"]
        current_compare_at_price = variant.get("compareAtPrice")
        
        # Calculate discounted price
        discounted_price = str(round(float(original_price) * (1 - discount_percentage/100), 2))
        
        variant_update = {
            "id": variant_id,
            "price": discounted_price
        }
        
        # Set the original price as compareAtPrice if requested and no compareAtPrice exists
        if set_compare_at_price and not current_compare_at_price:
            variant_update["compareAtPrice"] = original_price
            logging.info(f"Setting compare-at price for variant {variant_id}: {original_price}")
        
        variants_data.append(variant_update)
        
        logging.info(f"Variant {variant['title']}: {original_price} -> {discounted_price}")
    
    # Update regular prices
    success = update_product_variants_prices(product_id, variants_data)
    if not success:
        logging.error(f"Failed to update regular prices for {product_title}")
        return False
    
    # 2. Update market-specific prices if they exist
    market_prices = product_data.get("market_prices", {})
    if market_prices:
        for price_list_id, price_list_data in market_prices.items():
            price_list_currency = price_list_data["currency"]
            price_list_name = price_list_data["name"]
            
            logging.info(f"Processing price list: {price_list_name} ({price_list_currency})")
            
            prices = price_list_data["prices"]
            variant_prices = []
            
            for price_data in prices:
                variant_id = price_data["variant_id"]
                original_price = price_data["price"].get("amount")
                current_compare_at_price = price_data.get("compare_at_price")
                
                if original_price:
                    # Calculate discounted price
                    discounted_price = str(round(float(original_price) * (1 - discount_percentage/100), 2))
                    
                    variant_price = {
                        "variant_id": variant_id,
                        "price": {
                            "amount": discounted_price,
                            "currencyCode": price_list_currency
                        }
                    }
                    
                    # Set the original price as compareAtPrice if requested and no compareAtPrice exists
                    if set_compare_at_price and not current_compare_at_price:
                        variant_price["compare_at_price"] = {
                            "amount": original_price,
                            "currencyCode": price_list_currency
                        }
                        logging.info(f"Setting market compare-at price for variant {variant_id}: {price_list_currency} {original_price}")
                    
                    variant_prices.append(variant_price)
                    
                    logging.info(f"Market variant {variant_id.split('/')[-1]}: {price_list_currency} {original_price} -> {price_list_currency} {discounted_price}")
            
            # Update this price list
            if variant_prices:
                success = update_price_list_prices(price_list_id, variant_prices)
                if not success:
                    logging.error(f"Failed to update market prices for {price_list_name}")
    
    return True

def apply_bulk_discount(backup_file, discount_percentage=20, set_compare_at_price=True):
    """Apply a discount to all products in a backup file"""
    # Load backup data
    with open(backup_file, 'r') as f:
        backup_data = json.load(f)
    
    total_products = len(backup_data)
    success_count = 0
    error_count = 0
    
    logging.info(f"Starting discount application for {total_products} products...")
    logging.info(f"Discount: {discount_percentage}%")
    logging.info(f"Set compare-at prices: {set_compare_at_price}")
    
    # Process each product
    for i, (product_id, product_data) in enumerate(tqdm(backup_data.items(), desc="Applying discounts")):
        try:
            product_title = product_data.get("product", {}).get("title", "Unknown")
            logging.info(f"[{i+1}/{total_products}] Applying discount to: {product_title}")
            
            success = apply_discount_to_product_data(
                product_data, 
                discount_percentage, 
                set_compare_at_price
            )
            
            if success:
                success_count += 1
                logging.info(f"✓ Successfully applied discount to {product_title}")
            else:
                error_count += 1
                logging.error(f"✗ Failed to apply discount to {product_title}")
            
            # Be nice to the API - add small delay between products
            if i < total_products - 1:
                time.sleep(0.5)
                
        except Exception as e:
            logging.error(f"Error applying discount to product {product_id}: {e}")
            error_count += 1
    
    logging.info(f"\nDiscount application completed: {success_count} successful, {error_count} errors")
    return success_count, error_count

def restore_product_prices_from_data(product_data):
    """Restore a product's prices from backup data (without API calls)"""
    product_id = product_data["product"]["id"]
    product_title = product_data["product"]["title"]
    
    logging.info(f"Restoring prices for: {product_title} (ID: {product_id})")
    
    # 1. Restore regular product prices
    product = product_data["product"]
    variants = product["variants"]["edges"]
    
    variants_data = []
    for variant_edge in variants:
        variant = variant_edge["node"]
        variant_id = variant["id"]
        original_price = variant["price"]
        compare_at_price = variant.get("compareAtPrice")
        
        variant_update = {
            "id": variant_id,
            "price": original_price
        }
        
        if compare_at_price:
            variant_update["compareAtPrice"] = compare_at_price
            logging.info(f"Variant {variant['title']}: {original_price} (compare-at: {compare_at_price})")
        else:
            logging.info(f"Variant {variant['title']}: {original_price}")
        
        variants_data.append(variant_update)
    
    # Update regular prices
    success = update_product_variants_prices(product_id, variants_data)
    if not success:
        logging.error(f"Failed to restore regular prices for {product_title}")
        return False
    
    # 2. Restore market-specific prices if they exist
    market_prices = product_data.get("market_prices", {})
    if market_prices:
        for price_list_id, price_list_data in market_prices.items():
            price_list_currency = price_list_data["currency"]
            price_list_name = price_list_data["name"]
            
            logging.info(f"Processing price list: {price_list_name} ({price_list_currency})")
            
            prices = price_list_data["prices"]
            variant_prices = []
            
            for price_data in prices:
                variant_id = price_data["variant_id"]
                price = price_data["price"]
                compare_at_price = price_data.get("compare_at_price")
                
                if price and "amount" in price:
                    variant_price = {
                        "variant_id": variant_id,
                        "price": {
                            "amount": price['amount'],
                            "currencyCode": price_list_currency
                        }
                    }
                    
                    if compare_at_price:
                        # Ensure correct currency for compareAtPrice
                        variant_price["compare_at_price"] = {
                            "amount": compare_at_price['amount'],
                            "currencyCode": price_list_currency
                        }
                        logging.info(f"Market variant {variant_id.split('/')[-1]}: {price_list_currency} {price['amount']} (compare-at: {compare_at_price['amount']})")
                    else:
                        logging.info(f"Market variant {variant_id.split('/')[-1]}: {price_list_currency} {price['amount']}")
                    
                    variant_prices.append(variant_price)
            
            # Update this price list
            if variant_prices:
                success = update_price_list_prices(price_list_id, variant_prices)
                if not success:
                    logging.error(f"Failed to restore market prices for {price_list_name}")
    
    return True

def restore_bulk_prices(backup_file):
    """Restore all products' prices from a backup file"""
    # Load backup data
    with open(backup_file, 'r') as f:
        backup_data = json.load(f)
    
    total_products = len(backup_data)
    success_count = 0
    error_count = 0
    
    logging.info(f"Starting price restoration for {total_products} products...")
    
    # Process each product
    for i, (product_id, product_data) in enumerate(tqdm(backup_data.items(), desc="Applying discounts")):
        try:
            product_title = product_data.get("product", {}).get("title", "Unknown")
            logging.info(f"[{i+1}/{total_products}] Applying discount to: {product_title}")
            
            success = restore_product_prices_from_data(product_data)
            
            if success:
                success_count += 1
                logging.info(f"✓ Successfully restored prices for {product_title}")
            else:
                error_count += 1
                logging.error(f"✗ Failed to restore prices for {product_title}")
            
            # Be nice to the API - add small delay between products
            if i < total_products - 1:
                time.sleep(0.5)
                
        except Exception as e:
            logging.error(f"Error restoring prices for product {product_id}: {e}")
            error_count += 1
    
    logging.info(f"\nPrice restoration completed: {success_count} successful, {error_count} errors")
    return success_count, error_count

def list_backups():
    """List all available price backups"""
    logging.info("Listing available price backups")
    print("Available price backups:")
    backup_files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")]
    
    if not backup_files:
        logging.warning("No backups found.")
        print("No backups found.")
        return []
    
    # Sort by date (newest first)
    backup_files.sort(reverse=True)
    
    for i, file in enumerate(backup_files):
        # Get file creation time
        file_path = os.path.join(BACKUP_DIR, file)
        creation_time = os.path.getctime(file_path)
        creation_date = datetime.datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S")
        
        # Extract info from the backup if possible
        try:
            with open(file_path, 'r') as f:
                backup_data = json.load(f)
                product_count = len(backup_data)
                
                print(f"{i+1}. {file} - Created: {creation_date}")
                print(f"   Products: {product_count}")
                logging.info(f"Backup {i+1}: {file} - Created: {creation_date} - Products: {product_count}")
        except:
            print(f"{i+1}. {file} - Created: {creation_date}")
            logging.warning(f"Couldn't read details for backup file: {file}")
    
    return backup_files

def main():
    """Main function with interactive menu"""
    global MOCK_MODE
    
    # Set up initial logging to console only
    setup_logging()
    
    while True:
        print("\n===== Shopify Bulk Price Manager =====")
        print(f"Mock Mode: {'ENABLED (no actual updates)' if MOCK_MODE else 'DISABLED (real updates)'}")
        print("\n1. Create backup for a collection")
        print("2. Create backup for all products")
        print("3. Apply discount using backup")
        print("4. Restore prices from backup")
        print("5. List available backups")
        print("6. Toggle mock mode")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ")
        
        if choice == "1":
            # Set up logging for this operation
            log_file = setup_logging("collection_backup")
            logging.info("Starting collection backup operation")
            
            # Fetch collections
            collections = fetch_all_collections()
            if not collections:
                logging.warning("No collections found.")
                continue
            
            logging.info(f"Found {len(collections)} collections")
            print("\nAvailable collections:")
            for i, collection in enumerate(collections):
                print(f"{i+1}. {collection['title']} ({collection['productsCount']} products)")
            
            collection_index = input("\nEnter collection number to backup (or 0 to cancel): ")
            try:
                collection_index = int(collection_index) - 1
                if collection_index < 0:
                    logging.info("Operation cancelled by user.")
                    continue
                if 0 <= collection_index < len(collections):
                    collection = collections[collection_index]
                    collection_id = collection["id"]
                    
                    logging.info(f"Starting backup of collection: {collection['title']} (ID: {collection_id})")
                    
                    # Fetch products in batches
                    all_products = []
                    cursor = None
                    
                    while True:
                        products, collection_title, cursor = fetch_products_by_collection(collection_id, cursor)
                        all_products.extend(products)
                        
                        logging.info(f"Fetched {len(products)} products (total: {len(all_products)})")
                        
                        if not cursor:
                            break
                    
                    # Create backup name with collection name
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    collection_name = collection["title"].lower().replace(" ", "_")
                    backup_name = f"collection_{collection_name}_{timestamp}"
                    
                    backup_file = backup_products(all_products, backup_name)
                    logging.info(f"Collection backup completed. Backup file: {backup_file}")
                else:
                    logging.warning(f"Invalid collection number: {collection_index + 1}")
            except ValueError:
                logging.error("Invalid input. Please enter a number.")
            
        elif choice == "2":
            # Set up logging for this operation
            log_file = setup_logging("all_products_backup")
            logging.info("Starting backup of all products")
            
            # Fetch products in batches
            all_products = []
            cursor = None
            
            while True:
                products, cursor = fetch_all_products(cursor)
                all_products.extend(products)
                
                logging.info(f"Fetched {len(products)} products (total: {len(all_products)})")
                
                if not cursor:
                    break
                
                # Ask if user wants to continue after each batch
                if len(all_products) % 200 == 0:
                    continue_fetch = input(f"Continue fetching products? (total so far: {len(all_products)}) (yes/no): ")
                    if continue_fetch.lower() != "yes":
                        logging.info("User chose to stop fetching more products")
                        break
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"all_products_{timestamp}"
            
            backup_file = backup_products(all_products, backup_name)
            logging.info(f"Full catalog backup completed. Backup file: {backup_file}")
            
        elif choice == "3":
            # Set up logging for this operation
            log_file = setup_logging("apply_discount")
            logging.info("Starting discount application process")
            
            # List backups
            backup_files = list_backups()
            if not backup_files:
                logging.warning("No backups found")
                continue
            
            backup_index = input("\nEnter backup number to use for discount (or 0 to cancel): ")
            try:
                backup_index = int(backup_index) - 1
                if backup_index < 0:
                    logging.info("Operation cancelled by user")
                    continue
                if 0 <= backup_index < len(backup_files):
                    backup_file = os.path.join(BACKUP_DIR, backup_files[backup_index])
                    logging.info(f"Selected backup file: {backup_files[backup_index]}")
                    
                    # Get discount parameters
                    discount = input("Enter discount percentage (default: 20): ")
                    try:
                        discount = float(discount) if discount else 20
                    except:
                        discount = 20
                    logging.info(f"Discount percentage: {discount}%")
                    
                    set_compare = input("Set original price as compare-at price if none exists? (yes/no, default: yes): ")
                    set_compare_at_price = set_compare.lower() != "no"
                    logging.info(f"Set compare-at prices: {set_compare_at_price}")
                    
                    # Confirm action
                    if MOCK_MODE:
                        confirm = input(f"\nApply {discount}% discount using {backup_files[backup_index]} in MOCK mode? (yes/no): ")
                    else:
                        confirm = input(f"\nWARNING: This will apply real price changes to your store.\nApply {discount}% discount using {backup_files[backup_index]}? (yes/no): ")
                    
                    if confirm.lower() == "yes":
                        logging.info("User confirmed discount application")
                        success_count, error_count = apply_bulk_discount(backup_file, discount, set_compare_at_price)
                        logging.info(f"Discount application completed: {success_count} successful, {error_count} errors")
                    else:
                        logging.info("Operation cancelled by user")
                else:
                    logging.warning(f"Invalid backup number: {backup_index + 1}")
            except ValueError:
                logging.error("Invalid input. Please enter a number.")
            
        elif choice == "4":
            # Set up logging for this operation
            log_file = setup_logging("restore_prices")
            logging.info("Starting price restoration process")
            
            # List backups
            backup_files = list_backups()
            if not backup_files:
                logging.warning("No backups found")
                continue
            
            backup_index = input("\nEnter backup number to restore prices from (or 0 to cancel): ")
            try:
                backup_index = int(backup_index) - 1
                if backup_index < 0:
                    logging.info("Operation cancelled by user")
                    continue
                if 0 <= backup_index < len(backup_files):
                    backup_file = os.path.join(BACKUP_DIR, backup_files[backup_index])
                    logging.info(f"Selected backup file: {backup_files[backup_index]}")
                    
                    # Confirm action
                    if MOCK_MODE:
                        confirm = input(f"\nRestore prices from {backup_files[backup_index]} in MOCK mode? (yes/no): ")
                    else:
                        confirm = input(f"\nWARNING: This will apply real price changes to your store.\nRestore prices from {backup_files[backup_index]}? (yes/no): ")
                    
                    if confirm.lower() == "yes":
                        logging.info("User confirmed price restoration")
                        success_count, error_count = restore_bulk_prices(backup_file)
                        logging.info(f"Price restoration completed: {success_count} successful, {error_count} errors")
                    else:
                        logging.info("Operation cancelled by user")
                else:
                    logging.warning(f"Invalid backup number: {backup_index + 1}")
            except ValueError:
                logging.error("Invalid input. Please enter a number.")
            
        elif choice == "5":
            # Set up logging for this operation
            log_file = setup_logging("list_backups")
            logging.info("Listing available backups")
            list_backups()
            
        elif choice == "6":
            MOCK_MODE = not MOCK_MODE
            status = "ENABLED (no actual updates)" if MOCK_MODE else "DISABLED (real updates)"
            print(f"Mock Mode: {status}")
            logging.info(f"Mock mode changed to: {status}")
            
        elif choice == "7":
            logging.info("Exiting application")
            print("Exiting. Goodbye!")
            break
            
        else:
            logging.warning(f"Invalid choice: {choice}")
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()