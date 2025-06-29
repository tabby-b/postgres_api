from flask import Flask, request, jsonify
import psycopg2
import os
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

DATABASE_URL = "postgresql://postgres:SmCfMJbkpuSWMlHwDpWMqBTDiTOhZYtO@postgresapi-production.up.railway.app:443/railway?sslmode=require"


@app.route('/')
def health():
    return jsonify({"status": "PostgreSQL API is running!", "timestamp": datetime.now().isoformat()})


@app.route('/test')
def test_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        conn.close()
        return jsonify({"status": "success", "database_version": version})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/escalation', methods=['POST'])
def save_escalation():
    try:
        data = request.json
        app.logger.info(f"Received data: {data}")

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Create table if needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS escalation_data (
                id SERIAL PRIMARY KEY,
                timestamp VARCHAR(255),
                sme VARCHAR(255),
                ra VARCHAR(255),
                node VARCHAR(255),
                gate VARCHAR(255),
                issue TEXT,
                takeover VARCHAR(255),
                ra_andon VARCHAR(255),
                andon_ops_live VARCHAR(255),
                broken_seal_time VARCHAR(255),
                additional_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert the data
        cursor.execute("""
            INSERT INTO escalation_data 
            (timestamp, sme, ra, node, gate, issue, takeover, ra_andon, andon_ops_live, broken_seal_time, additional_notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('Timestamp'),
            data.get('SME'),
            data.get('RA'),
            data.get('Node'),
            data.get('Gate'),
            data.get('Issue'),
            data.get('Takeover?'),
            data.get('RA Andon?'),
            data.get('Andon OPs\nLive?'),
            data.get('Broken Seal\nResolve Time'),
            data.get('Additional\n Notes')
        ))

        record_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Escalation data saved successfully!",
            "record_id": record_id
        })

    except Exception as e:
        app.logger.error(f"Database error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/escalation', methods=['GET'])
def get_escalations():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT timestamp, sme, ra, node, gate, issue, takeover, ra_andon, 
                   andon_ops_live, broken_seal_time, additional_notes, created_at 
            FROM escalation_data 
            ORDER BY created_at DESC 
            LIMIT 50
        """)

        rows = cursor.fetchall()
        conn.close()

        escalations = []
        for row in rows:
            escalations.append({
                'Timestamp': row[0],
                'SME': row[1],
                'RA': row[2],
                'Node': row[3],
                'Gate': row[4],
                'Issue': row[5],
                'Takeover?': row[6],
                'RA Andon?': row[7],
                'Andon OPs\nLive?': row[8],
                'Broken Seal\nResolve Time': row[9],
                'Additional\n Notes': row[10],
                'created_at': row[11].isoformat() if row[11] else None
            })

        return jsonify({"status": "success", "data": escalations, "count": len(escalations)})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/debug-db')
def debug_db():
    try:
        app.logger.info(f"DATABASE_URL: {DATABASE_URL[:50]}...")  # Only log first 50 chars for security

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Test basic connection
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]

        # Test if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'escalation_data'
            )
        """)
        table_exists = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            "status": "success",
            "database_version": version,
            "table_exists": table_exists,
            "connection": "OK"
        })

    except Exception as e:
        app.logger.error(f"Database debug error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "database_url_length": len(DATABASE_URL) if DATABASE_URL else 0
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)