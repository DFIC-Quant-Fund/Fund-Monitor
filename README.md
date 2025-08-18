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

### 4. Use the Controller
```python
from src.controllers.portfolio_controller import PortfolioController

# Initialize controller
controller = PortfolioController("core")

# Get portfolio data
summary = controller.get_portfolio_summary()
holdings = controller.get_holdings_data()
performance = controller.get_performance_metrics()

# Note: Building is done via scripts/build_all_portfolios.py, not via the controller
```

## 📁 Project Structure

```
src/
├── models/                    # 🗃️ DATA MODELS
│   ├── __init__.py
│   └── portfolio_csv_builder.py  # Your original CSV builder
├── controllers/               # 🎮 BUSINESS LOGIC
│   ├── __init__.py
│   ├── portfolio_controller.py   # Main controller
│   ├── benchmark.py              # Your original analytics
│   ├── returns_calculator.py
│   ├── risk_metrics.py
│   ├── ratios.py
│   ├── market_comparison.py
│   └── ... (all your original performance files)
├── views/                     # 🎨 USER INTERFACE
│   ├── __init__.py
│   └── (future view components)
├── config/                    # ⚙️ CONFIGURATION
│   ├── __init__.py
│   └── securities_config.py   # Loads core.yaml
└── app.py                     # 🚀 MAIN STREAMLIT APP
```

## 🔧 Key Benefits

1. **Simple & Clean**: Clear separation of concerns
2. **Preserved**: All your original functionality intact
3. **Maintainable**: Easy to understand and modify
4. **Scalable**: Easy to add new features
5. **Compatible**: Works with existing data and config

## 📊 Features

### Portfolio Analysis
- Real-time holdings data
- Sector and fund allocation
- Geographic distribution
- Asset class breakdown

### Performance Metrics
- Multiple time horizons (1-day to inception)
- Risk-adjusted ratios (Sharpe, Sortino, Information)
- Market comparison (Beta, Alpha, Risk Premium)
- Downside risk metrics

### Data Management
- Automatic CSV file generation
- Dividend tracking
- Currency conversion
- Exchange rate handling

## 🎯 Usage Examples

### Load Portfolio Data
```python
from src.controllers.portfolio_controller import PortfolioController

controller = PortfolioController("core")
summary = controller.get_portfolio_summary("2025-05-29")

print(f"Total Value: ${summary['total_value']:,.0f}")
print(f"Holdings: {summary['total_holdings']}")
```

### Get Performance Metrics
```python
performance = controller.get_performance_metrics("2025-05-29")

# Period returns
print(f"YTD Return: {performance['performance']['ytd']:.2f}%")

# Risk metrics
print(f"Sharpe Ratio: {performance['ratios']['annualized_sharpe_ratio']:.3f}")
```

### Rebuild Data
Use the script instead of the controller:
```bash
python scripts/build_all_portfolios.py
```

## 🔄 Data Flow

1. **Input**: Trades, prices, dividends in `data/{portfolio}/input/`
2. **Models**: `portfolio_csv_builder.py` creates processed CSV files
3. **Controllers**: Performance modules calculate metrics
4. **Views**: Streamlit app provides visualization

## 🛠️ Development

### Adding New Features
1. **Models**: Add new data processing in `portfolio_csv_builder.py`
2. **Controllers**: Add new business logic in `portfolio_controller.py`
3. **Views**: Add new UI components in `app.py`

### Testing
```bash
python -c "from src.controllers.portfolio_controller import PortfolioController; print('✅ MVC working!')"
```

### Configuration
Edit `config/portfolio_definitions/core.yaml` to:
- Add new securities
- Update fund classifications
- Modify sector mappings

## 📈 Performance Analytics

The system includes sophisticated performance analytics:

- **Returns Analysis**: Multiple time horizons and calculation methods
- **Risk Metrics**: Volatility, downside risk, maximum drawdown
- **Risk-Adjusted Ratios**: Sharpe, Sortino, Information ratios
- **Market Comparison**: Beta, Alpha, risk premium calculations
- **Benchmarking**: Custom and SPY benchmark comparisons

All analytics preserve your original implementation while integrating seamlessly with the MVC architecture.

## 🎯 Why This Architecture?

- **Simple**: Easy to understand and maintain
- **Familiar**: Standard MVC pattern
- **Preserved**: All your original work intact
- **Scalable**: Easy to add new features
- **Clean**: Clear separation of concerns

Perfect for a project of this size and complexity!
