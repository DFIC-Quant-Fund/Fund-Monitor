from flask import Flask, jsonify, make_response
from flask_cors import CORS
import mysql.connector
import os
from dotenv import load_dotenv
import pandas as pd
from io import StringIO


load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://dfic-fund.netlify.app", "https://api.degrootefinance.com/"]}})

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
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch all performance returns data
        cursor.execute("""
            SELECT 
                DATE_FORMAT(date, '%Y-%m-%d') as date,
                one_day_return,
                one_week_return,
                one_month_return,
                ytd_return,
                one_year_return,
                inception_return
            FROM performance_returns
            ORDER BY date DESC
        """)
        
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