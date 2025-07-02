import pandas as pd

excel_path = r"G:\My Drive\Pennymac.xlsx"

# Try skipping first 100 rows; adjust if necessary
df = pd.read_excel(excel_path, skiprows=10)

print("First few rows of the adjusted Pennymac rate sheet:")
print(df.head())
