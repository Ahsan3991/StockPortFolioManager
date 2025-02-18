 # StockPortFolioManager
This is a simple application to keep track of PSX stock port folio. The idea is to use the existing LLM framework like gpt4all and allow the user to directly upload the trade receipts and dividend warrants without needing to type anything and the required information will be filled out to create the database using the LLM. Portfolio summary page provides a comprehensive overview of the current portfolio value, holdings pie chart and P/L.

# How to test
1. Goto your project folder
2. Run the terminal to clone the repo
3. Install the requirements using "pip install requirements.txt"
4. If you are using VSCODE then install the SQLite extension by alexcvzz
5. Run the scripts using "streamlit run main.py --server.fileWatcherType none"
