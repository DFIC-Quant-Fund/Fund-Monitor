from flask import Flask, jsonify, make_response, request
from flask_cors import CORS
import mysql.connector
import os
from dotenv import load_dotenv
import pandas as pd
from io import StringIO

import yaml

from api.routes.health_routes import health_bp
from api.routes.holdings_routes import holdings_bp

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": [
    "https://dfic-fund.netlify.app",
    "https://api.degrootefinance.com",
    "https://fund.degrootefinance.com",
    "http://localhost:3000", #local dev
    "http://127.0.0.1:3000", #local dev 
    r"^https://deploy-preview-\d+--dfic-fund\.netlify\.app$"
]}})

app.register_blueprint(health_bp, url_prefix='/api')
app.register_blueprint(holdings_bp, url_prefix='/api')

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOSTNAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT'),
        database="Fund"
    )

@app.route('/api/data', methods=['GET'])
def get_data():
    # Replace with your actual data logic
    return jsonify({"message": "Test api endpoint"})

@app.route('/api/performance', methods=['GET'])
def get_performance_data():
    try:
        end_date = request.args.get('date', None) or pd.Timestamp.now().strftime('%Y-%m-%d')
        portfolio = request.args.get('portfolio', None) or 'core'
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Base query
        cursor.execute("""
            SELECT 
                DATE_FORMAT(date, '%Y-%m-%d') as date,
                portfolio,
                one_day_return,
                one_week_return,
                one_month_return,
                ytd_return,
                one_year_return,
                inception_return
            FROM PerformanceReturns
            WHERE portfolio = %s
            AND date <= %s
            ORDER BY date DESC
        """, (portfolio, end_date))
        
        # Add date filter if date parameter is provided
        # if end_date:
        #     query += " WHERE date <= %s"
        #     query += " ORDER BY date DESC"
        #     cursor.execute(query, (end_date,))
        # else:
        #     query += " ORDER BY date DESC"
        #     cursor.execute(query)

        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        print(results[0])

        return jsonify({
            "success": True,
            "data": results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/holdings', methods=['GET'])
def get_holdings_data():
    try:
        end_date = request.args.get('date', None) or pd.Timestamp.now().strftime('%Y-%m-%d')
        portfolio = request.args.get('portfolio', None) or 'core'

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
        SELECT * 
        FROM Holdings
        WHERE trading_date = %s
            and portfolio = %s;
        """, (end_date, portfolio))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "data": results
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/exchange-rates', methods=['GET'])
def get_currency_data():
    try:
        end_date = request.args.get('date', None) or pd.Timestamp.now().strftime('%Y-%m-%d')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(f"""
        SELECT *
        FROM Currencies
        WHERE date = %s;
        """, (end_date,))

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Pulling fund thesis - all  at once (will filter in frontend based on which one is needed)
@app.route('/api/fund-thesis', methods=['GET'])
def get_fund_thesis():
    try:
        with open("./portfolios/dfic_core.yaml", "r") as f:
            config = yaml.safe_load(f)

        result = config['funds']

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# CAN LATER WORK TO COMBINE THE BELOW TO ONE ROUTE - since there is some overlap between queries for different graphs 
# Pulling fund market value  - fund value everyday from selected time frame (line chart)
@app.route('/api/fund-market', methods=['GET'])
def get_fund_market():
    try:
        # evaluate fund from the chosen date (else default is one year from current date)
        one_year_ago = pd.Timestamp.now() - pd.Timedelta(days=365)
        start_date = request.args.get('date', None) or one_year_ago.strftime('%Y-%m-%d')
        fund = request.args.get('fund', None) or 'TMT Fund'

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(f"""
        SELECT trading_date, SUM(market_value) as market_value
        FROM Holdings
        WHERE trading_date >= %s AND fund LIKE %s
        GROUP BY trading_date;
        """, (start_date, fund))

        result = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
# fund holdings - distinct holdings of fund in time frame (pie chart)
@app.route('/api/fund-holdings', methods=['GET'])
def get_fund_holdings():
    try:
        # evaluate fund from the chosen date (else default is one year from current date)
        one_year_ago = pd.Timestamp.now() - pd.Timedelta(days=365)
        start_date = request.args.get('date', None) or one_year_ago.strftime('%Y-%m-%d')
        fund = request.args.get('fund', None) or 'TMT Fund'

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(f"""
        SELECT ticker, sum(market_value) as ticker_holdings
        FROM Holdings
        WHERE trading_date = %s AND fund LIKE %s
        GROUP BY ticker;
        """, (start_date, fund))

        result = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Pulling fund stats - table - number of total names invested in, total market value (sum of everything), sectors, trades 
@app.route('/api/fund-highlights', methods=['GET'])
def get_fund_highlights():
    try:
        # evaluate fund from the chosen date (else default is one year from current date)
        one_year_ago = pd.Timestamp.now() - pd.Timedelta(days=365)
        start_date = request.args.get('date', None) or one_year_ago.strftime('%Y-%m-%d')
        fund = request.args.get('fund', None) or 'TMT Fund'

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(f"""
        SELECT count(ticker) as total_trades, count(distinct ticker) as assets, sum(market_value) as investments, count(distinct sector) as sectors
        FROM Holdings
        WHERE trading_date >= %s AND fund LIKE %s
        """, (start_date, fund))

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Pulling fund transactions - table
@app.route('/api/transactions', methods=['GET'])
def get_trade():
    if request.method == 'GET':
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            # Get param arguments from request and filter result according to portfolio
            portfolio = request.args.get('portfolio')
            if portfolio not in ('core', 'benchmark'):
                portfolio = None
            if portfolio is not None:
                cursor.execute("""
                    SELECT transaction_id, s.name, t.date, t.ticker, s.type, t.action, t.shares, t.price, t.currency, t.portfolio, s.fund
                    FROM Fund.Transactions t
                    LEFT JOIN Fund.Securities s ON t.ticker = s.ticker
                    WHERE t.portfolio = %s AND s.fund != 'Benchmark'
                    ORDER BY t.transaction_id desc
                    """, (portfolio,))
            else:
                cursor.execute("""
                    SELECT transaction_id, s.name, t.date, t.ticker, s.type, t.action, t.shares, t.price, t.currency, t.portfolio, s.fund
                    FROM Fund.Transactions t
                    LEFT JOIN Fund.Securities s ON t.ticker = s.ticker
                    WHERE s.fund != 'Benchmark'
                    ORDER BY t.transaction_id desc
                    """)
            result = cursor.fetchall()
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            cursor.close()
            conn.close()
        return jsonify({
            "success": True,
            "data": result}), 200

@app.route('/api/latest-date', methods=['GET'])
def get_latest_date():
    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(f"""
            SELECT trading_date 
            FROM Fund.MaterializedHoldings
            order by trading_date desc
            limit 1
        """)

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/holdings/pnl', methods=['GET'])
def get_position_details():
    try:
        end_date = request.args.get('date', None) or pd.Timestamp.now().strftime('%Y-%m-%d')
        portfolio = request.args.get('portfolio', None) or 'core'

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            WITH PurchaseCosts AS (
                SELECT 
                    t.ticker,
                    t.portfolio,
                    SUM(t.shares * t.price) as total_purchase_cost,
                    SUM(t.shares) as total_shares,
                    COUNT(DISTINCT t.date) as number_of_purchases
                FROM Transactions t
                WHERE t.action = 'BUY'
                GROUP BY t.ticker, t.portfolio
            ),
            CurrentHoldings AS (
                SELECT 
                    h.ticker,
                    h.portfolio,
                    h.shares_held,
                    h.market_value,
                    h.security_currency as currency
                FROM Holdings h
                WHERE h.trading_date = %s
            )
            SELECT 
                ch.ticker,
                s.name,
                s.type,
                s.geography,
                s.sector,
                s.fund,
                ch.currency,
                ch.shares_held,
                ch.market_value,
                pc.total_purchase_cost,
                pc.total_shares as total_shares_purchased,
                pc.number_of_purchases,
                (pc.total_purchase_cost / pc.total_shares) as average_purchase_price,
                (pc.total_purchase_cost / pc.total_shares * ch.shares_held) as book_value
            FROM CurrentHoldings ch
            JOIN Securities s ON ch.ticker = s.ticker AND ch.portfolio = s.portfolio
            JOIN PurchaseCosts pc ON ch.ticker = pc.ticker AND ch.portfolio = pc.portfolio
            WHERE ch.portfolio = %s
                AND s.fund != 'Benchmark'
                AND ch.shares_held > 0
            ORDER BY ch.ticker
        """, (end_date, portfolio))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "data": results
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, debug=True)
