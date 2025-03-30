from flask import Flask, jsonify, make_response, request
from flask_cors import CORS
import mysql.connector
import os
from dotenv import load_dotenv
import pandas as pd
from io import StringIO


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

@app.route('/api/transactions', methods=['GET'])
def get_trade():
    if request.method == 'GET':
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT transaction_id, s.name, t.ticker, s.type, t.action, t.shares, t.price, t.currency, t.portfolio, s.fund
                FROM Fund.Transactions t
                LEFT JOIN Fund.Securities s ON t.ticker = s.ticker
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


    # elif request.method == 'POST':
    #
    #     try:
    #         data = request.get_json()
    #         if not request.is_json:
    #             raise Exception("Missing JSON in POST request")
    #         required_fields = ['ticker', 'type', 'date', 'quantity', 'price', 'currency']
    #         missing_fields = [field for field in required_fields if field not in data]
    #         if missing_fields:
    #             raise Exception("Missing fields: {}".format(missing_fields))
    #
    #         formatted_date = datetime.strptime(data['date'], "%Y-%m-%d").date()
    #         new_transaction = {
    #             "ticker": data['ticker'],
    #             "type": data['type'],
    #             "date": formatted_date,
    #             "quantity": float(data['quantity']),
    #             "price": float(data['price']),
    #             "currency": data['currency']
    #         }
    #     except Exception as e:
    #         return jsonify({"success": False, "error": str(e)}), 500
    #
    #     try:
    #         with open('config_testing.yaml', 'r') as file:
    #             yaml_data = yaml.safe_load(file) or {}
    #             yaml_data['transactions'].append(new_transaction)
    #     except Exception as e:
    #         return jsonify({"success": False, "error": f"Error reading YAML file: {str(e)}"}), 500
    #
    #     try:
    #         with open('config_testing.yaml', 'w') as file:
    #             yaml.dump(yaml_data, file, sort_keys=False)
    #     except Exception as e:
    #         return jsonify({"success": False, "error": f"Error writing YAML file: {str(e)}"}), 500
    #
    #     return jsonify({"success": True}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, debug=True)
