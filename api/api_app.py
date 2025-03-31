from flask import Flask, jsonify, make_response, request
from flask_cors import CORS
import mysql.connector
import os
from dotenv import load_dotenv
import pandas as pd
from io import StringIO

import yaml


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
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Base query
        query = """
            SELECT 
                DATE_FORMAT(date, '%Y-%m-%d') as date,
                one_day_return,
                one_week_return,
                one_month_return,
                ytd_return,
                one_year_return,
                inception_return
            FROM PerformanceReturns
        """
        
        # Add date filter if date parameter is provided
        if end_date:
            query += " WHERE date <= %s"
            query += " ORDER BY date DESC"
            cursor.execute(query, (end_date,))
        else:
            query += " ORDER BY date DESC"
            cursor.execute(query)
        
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
        with open("../portfolios/dfic_core.yaml", "r") as f:
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
        WHERE trading_date >= %s AND fund LIKE %s
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, debug=True)
