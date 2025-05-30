# Shopify Price Manager CLI

A powerful command-line tool to **backup**, **discount**, and **restore** product and market-specific prices in Shopify using the Admin GraphQL API.

## 🚀 Features

- 🧾 Backup product prices with all market-specific price lists
- 💸 Apply bulk discounts (e.g. 20% off across variants and markets)
- ♻️ Restore prices from backup JSON files
- 📦 Operates on all products or specific collections
- 🛑 Safe `MOCK_MODE` for dry runs
- 📊 Progress bars and clean terminal output using `tqdm`
- 📝 Verbose logs saved to timestamped log files

## 📦 Requirements

- Python 3.8+
- A Shopify store
- An Admin API access token with appropriate scopes, such as:
  - read_products
  - write_products
  - read_price_lists (for B2B/Markets)
  - write_price_lists (if modifying price lists)

## Install dependencies:
```
pip install requests tqdm python-dotenv colorama
```

## ⚙️ Setup

Create a .env file in the root of the project:
```
SHOP_NAME=your-store.myshopify.com
ACCESS_TOKEN=your-admin-api-token
```

## 🛠 Usage

Run the CLI:
```
python shopify-price-manager-cli.py
```

## Available actions:
- Backup prices for all products or by collection
- Apply discounts from a backup file
- Restore prices from a backup file
- Toggle between dry-run mode (MOCK) and live updates

## 📂 Backups & Logs
- JSON backups are saved in ./price_backups/
- Logs are stored in ./price_logs/, timestamped per operation

## 🔐 Security

- Your API token is read from a .env file and never logged or exposed in backups.

## 📈 Roadmap Ideas
- Use rich for styled output and progress bars
- Add interactive filtering by tag or vendor
- Export price deltas to CSV
- Wrap as installable CLI tool via setuptools

## 🪪 License

This project is licensed under the [MIT License](LICENSE).
