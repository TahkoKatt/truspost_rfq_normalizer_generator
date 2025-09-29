# 🚢 Smart RFQ Normalizer

A Python application that normalizes messy shipping RFQs (Request for Quote) into structured JSON data using OpenAI's API. Supports both console output and interactive Streamlit UI.

## 🎯 Features

- **Console Mode**: Process sample RFQs and display results in a formatted table
- **Streamlit UI**: Interactive web interface for processing custom RFQs
- **CSV Export**: Download normalized results as CSV files
- **Error Handling**: Graceful handling of JSON parsing errors and API issues
- **Batch Processing**: Process multiple RFQs at once

## 📋 Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your OpenAI API key**:
   - Get your API key from https://platform.openai.com/api-keys
   - Edit the `.env` file and replace `your_openai_api_key_here` with your actual API key

## 🚀 Usage

### Console Mode
Run the script directly to see sample RFQ normalization:

```bash
python smart_rfq_normalizer.py
```

This will:
- Process 3 hard-coded sample RFQs
- Display results in a formatted console table
- Show normalized fields: origin, destination, cargo_type, weight, price, transit_time, conditions, notes

### Streamlit UI Mode
Launch the interactive web interface:

```bash
streamlit run smart_rfq_normalizer.py
```

This will:
- Open a web browser with the Streamlit interface
- Allow you to paste multiple RFQs (one per line)
- Process them with a click
- Display results in an interactive table
- Provide CSV download functionality

## 📊 Output Schema

Each RFQ is normalized into the following fields:

- **origin**: Shipping origin location
- **destination**: Shipping destination location
- **cargo_type**: Type of cargo/goods
- **weight**: Weight of shipment
- **price**: Price with currency
- **transit_time**: Transit time in days
- **conditions**: Special conditions or terms
- **notes**: Additional notes or error messages

## 🛠️ Requirements

- Python 3.7+
- OpenAI API key
- Internet connection for API calls

## 📝 Example Input/Output

**Input RFQ:**
```
Shipping quote from Shanghai to Los Angeles:
Container: 20ft FCL
Cargo: Electronics (5000 kg)
Price: $2,800 USD all-in
Transit: 14-16 days ocean freight
Terms: FOB Shanghai, payment 30 days
```

**Normalized Output:**
```json
{
  "origin": "Shanghai",
  "destination": "Los Angeles",
  "cargo_type": "Electronics",
  "weight": "5000 kg",
  "price": "$2,800 USD",
  "transit_time": "14-16",
  "conditions": "FOB Shanghai, payment 30 days",
  "notes": ""
}
```

## 🔧 Troubleshooting

- **API Key Error**: Make sure your `.env` file contains a valid OpenAI API key
- **Import Errors**: Run `pip install -r requirements.txt` to install dependencies
- **JSON Parsing**: The app handles malformed API responses gracefully with error notes