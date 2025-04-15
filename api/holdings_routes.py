from flask import Blueprint, jsonify, request
import pandas as pd

import os
import sys
import yaml
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_utils import get_db_connection

holdings_bp = Blueprint('holdings', __name__)

with open("../config.yaml", "r") as f:
    config = yaml.safe_load(f)
    default_start_date = config['start_date']

@holdings_bp.route('/holdings/test', methods=['GET'])
def test_holdings():
    try:
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
        SELECT count(*) 
        FROM Transactions
        """)

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
    
@holdings_bp.route('/holdings/sector-weights-geography', methods=['GET'])
def sector_weights_geography():
    try:
        end_date = request.args.get('end_date', None) or pd.Timestamp.now().strftime('%Y-%m-%d')
        portfolio = request.args.get('portfolio', None) or 'core'
        start_date = request.args.get('start_date', None) or default_start_date

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        print("Geography Weights from", start_date, "to", end_date, "for portfolio", portfolio)

        cursor.execute("""
        SELECT 
            m.trading_date,
            m.geography,
            ROUND(SUM(
                CASE m.security_currency
                    WHEN 'CAD' THEN m.market_value / c.CAD
                    WHEN 'USD' THEN m.market_value / c.USD
                    WHEN 'EUR' THEN m.market_value / c.EUR
                    ELSE 0
                END
            ), 3) AS market_value_in_CAD
        FROM Fund.MaterializedHoldings m
        JOIN Fund.Currencies c
            ON m.trading_date = c.date
        WHERE m.portfolio = %s
          AND m.trading_date >= %s
          AND m.trading_date <= %s
        GROUP BY 
            m.trading_date,
            m.geography
        ORDER BY 
            m.trading_date DESC;
        """, (portfolio, start_date, end_date))

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
    
@holdings_bp.route('/holdings/sector-weights-fund', methods=['GET'])
def sector_weights_fund():
    try:
        end_date = request.args.get('end_date', None) or pd.Timestamp.now().strftime('%Y-%m-%d')
        portfolio = request.args.get('portfolio', None) or 'core'
        start_date = request.args.get('start_date', None) or default_start_date

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
        SELECT 
            m.trading_date,
            m.fund,
            ROUND(SUM(
                CASE m.security_currency
                    WHEN 'CAD' THEN m.market_value / c.CAD
                    WHEN 'USD' THEN m.market_value / c.USD
                    WHEN 'EUR' THEN m.market_value / c.EUR
                    ELSE 0
                END
            ), 3) AS market_value_in_CAD
        FROM Fund.MaterializedHoldings m
        JOIN Fund.Currencies c
            ON m.trading_date = c.date
        WHERE m.portfolio = %s
          AND m.trading_date >= %s
          AND m.trading_date <= %s
        GROUP BY 
            m.trading_date,
            m.fund
        ORDER BY 
            m.trading_date DESC;
        """, (portfolio, start_date, end_date))

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
    
@holdings_bp.route('/holdings/sector-weights-sector', methods=['GET'])
def sector_weights_sector():
    try:
        end_date = request.args.get('end_date', None) or pd.Timestamp.now().strftime('%Y-%m-%d')
        portfolio = request.args.get('portfolio', None) or 'core'
        start_date = request.args.get('start_date', None) or default_start_date

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
        SELECT 
            m.trading_date,
            m.sector,
            ROUND(SUM(
                CASE m.security_currency
                    WHEN 'CAD' THEN m.market_value / c.CAD
                    WHEN 'USD' THEN m.market_value / c.USD
                    WHEN 'EUR' THEN m.market_value / c.EUR
                    ELSE 0
                END
            ), 3) AS market_value_in_CAD
        FROM Fund.MaterializedHoldings m
        JOIN Fund.Currencies c
            ON m.trading_date = c.date
        WHERE m.portfolio = %s
          AND m.trading_date >= %s
          AND m.trading_date <= %s
        GROUP BY 
            m.trading_date,
            m.sector
        ORDER BY 
            m.trading_date ASC;
        """, (portfolio, start_date, end_date))

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
    


