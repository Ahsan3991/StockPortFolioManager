# Asset Portfolio Manager called WealthWise 📈

A comprehensive web application built with Streamlit for managing your portfolio, tracking trades, monitoring dividends and keeping track of precious metal investments. This tool helps investors maintain a clear record of their investments and analyze their portfolio performance. The application uses SQLite for data storage, with separate databases for each user. It integrates with external APIs like GoldAPI for metal prices and uses the PSX (Pakistan Stock Exchange) data reader for stock prices.

## 🌟 Start you investment journey today! 

### Trade Management
- **Upload Trade Receipts**: Automatically extract trade details from PDF receipts (not deployed yet)
- **Manual Trade Entry**: Add trades manually with a user-friendly interface
- **Edit & Delete**: Modify or remove existing trades as needed
- **Search Functionality**: Easily find specific trades by memo number, stock name, or date

### Dividend Tracking
- **Upload Dividend Warrants**: Process dividend warrants from PDF files
- **Manual Dividend Entry**: Add dividend records manually
- **Track Tax Deductions**: Monitor tax deducted from dividend payments
- **Dividend History**: View complete dividend payment history

### Precious Metal Trades
- **Upload Trade Receipts**: Automatically extract trade details from PDF receipts (not deployed yet)
- **Manual Trade Entry**: Add trades manually with a user-friendly interface. Options to choose between Gold, Silver, Palladium and more
- **Edit & Delete**: Modify or remove existing trades as needed
- **Search Functionality**: Easily find specific trades by memo number, metal type, or date

### Portfolio Analysis
- **Current Positions**: View all active positions with quantities and average prices
- **Portfolio Distribution**: Visual representation of your portfolio allocation
- **Realized Profit/Loss**: Track completed trades and their outcomes
- **Performance Metrics**: Monitor overall portfolio performance

### Sell Trade Management
- **Sell Stock**: Record stock sales with CGT calculations
- **Profit/Loss Calculation**: Automatic P/L calculation based on average buy price
- **Tax Management**: Track Capital Gains Tax (CGT) on sales

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Ahsan3991/StockPortFolioManager.git
cd StockPortFolioManager
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run main.py
```

## 💻 Usage

1. **Adding Buy Trades**:
   - Upload trade confirmation PDFs for automatic processing
   - Or manually enter trade details with the form interface
   - Each trade requires a unique memo number

2. **Recording Dividends**:
   - Upload dividend warrants for automatic processing
   - Or manually enter dividend details
   - Track tax deductions automatically

3. **Selling Stocks**:
   - Select the stock to sell from your portfolio
   - Enter selling details including quantity and rate
   - System automatically calculates CGT

4. **Viewing Portfolio**:
   - Access comprehensive portfolio summary
   - View distribution charts and performance metrics
   - Track realized and unrealized gains

## 🔧 Technical Details

### Built With
- [Streamlit](https://streamlit.io/) - The web framework used
- [SQLite](https://www.sqlite.org/index.html) - Database management
- [Plotly](https://plotly.com/) - Interactive visualizations
- [Pandas](https://pandas.pydata.org/) - Data manipulation
- [GPT4All](https://github.com/nomic-ai/gpt4all) - PDF text extraction

### Database Schema
The application uses SQLite with the following main tables:
- `trades`: Records all buy trades
- `memos`: Tracks trade memo numbers
- `warrants`: Stores dividend warrant information
- `dividends`: Records dividend payments
- `sell_trades`: Tracks stock sales

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check [issues page](https://github.com/Ahsan3991/StockPortFolioManager/issues).

## 📝 License

This project is not licensed yet!

## 👥 Author

- **Ahsan** - [GitHub Profile](https://github.com/Ahsan3991)

## 🙏 Acknowledgments

- Thanks to all contributors who have helped shape this project
- Special thanks to the Streamlit team for their amazing framework
- Appreciation to the open-source community for their invaluable tools and libraries

## 📞 Support

For support or queries:
- Create an [issue](https://github.com/Ahsan3991/StockPortFolioManager/issues)
- Contact the maintainer

## Actual Screenshots
(to be added)
---
Made with ❤️ for investors and traders
