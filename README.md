# DFIC Fund Monitor

A comprehensive portfolio management and analysis system using a simple MVC architecture.

## 🏗️ Architecture

The project uses a **simple MVC (Model-View-Controller) architecture**:

### **Models** (`src/models/`)
- **`portfolio_csv_builder.py`** - Your original data building engine
- Handles CSV file creation and data processing

### **Controllers** (`src/controllers/`)
- **`portfolio_controller.py`** - Main business logic orchestrator
- **Performance modules** - Your original sophisticated analytics
  - `returns_calculator.py` - Multiple return horizons
  - `risk_metrics.py` - Volatility, drawdown, etc.
  - `ratios.py` - Sharpe, Sortino, Information ratios
  - `market_comparison.py` - Beta, Alpha, risk premium
  - `benchmark.py` - Custom and SPY benchmarks

### **Views** (`src/views/`)
- **`app.py`** - Main Streamlit interface
- Clean, tabbed UI for portfolio analysis

### **Config** (`src/config/`)
- **`securities_config.py`** - Loads `core.yaml` configuration
- Provides sector, fund, and geography mapping

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
streamlit run src/app.py
```

### 3. Build Data (one-time or when inputs change)
```bash
python scripts/build_all_portfolios.py
```
This runs the legacy builder for both `core` and `benchmark`.

### Configuration
Edit `config/portfolio_definitions/core.yaml` to:
- Add new securities
- Update fund classifications
- Modify sector mappings

### Live Deployed Website
https://dfic-fund.streamlit.app/
This will update automatically on main pushes
