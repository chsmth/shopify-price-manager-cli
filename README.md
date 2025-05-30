# Shopify Price Manager CLI

A powerful command-line tool to **backup**, **discount**, and **restore** product and market-specific prices in Shopify using the Admin GraphQL API.

---

## 🚀 Features

- 🧾 Backup product prices with all market-specific price lists
- 💸 Apply bulk discounts (e.g., 20% off across variants and markets)
- ♻️ Restore prices from backup JSON files
- 📦 Operate on all products or specific collections
- 🛑 Safe `MOCK_MODE` for dry runs
- 📊 Progress bars and clean terminal output using `tqdm`
- 📝 Verbose logs saved to timestamped log files

---

## 📦 Requirements

- Python 3.8+
- A Shopify store
- An Admin API access token with the following scopes:
  - `read_products`
  - `write_products`
  - `read_price_lists` _(for B2B/Markets)_
  - `write_price_lists` _(if modifying price lists)_

Install dependencies:

```bash
pip install requests tqdm python-dotenv colorama
```

Or use:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Setup

Create a `.env` file in the root of the project with the following:

```env
SHOP_NAME=your-store.myshopify.com
ACCESS_TOKEN=your-admin-api-token
```

---

## 🛠 Usage

Run the CLI:

```bash
python shopify-price-manager-cli.py
```

Available actions:

- Create backups for all products or by collection
- Apply discounts using a backup file
- Restore prices using a backup file
- Toggle between MOCK mode and real updates
- View available backups

---

## 📂 Backups & Logs

- 📁 JSON backups saved in: `./price_backups/`
- 📝 Logs stored in: `./price_logs/` with timestamps

---

## 🔐 Security

Your Admin API token is loaded securely from a `.env` file and never printed or included in backup files.

---

## 📈 Roadmap Ideas

- [ ] Use `rich` for styled output and better progress bars
- [ ] Add interactive filtering (e.g. by tag or vendor)
- [ ] Export before/after price deltas to CSV
- [ ] Wrap as installable CLI tool via `setuptools`
- [ ] Add support for automated GitHub backup commits

---

## 🪪 License

This project is licensed under the [MIT License](LICENSE).

---

```
+-------------------------+
| Built with ❤️ by chsmth |
+-------------------------+
```
