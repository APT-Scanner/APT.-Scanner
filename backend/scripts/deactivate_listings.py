from datetime import datetime, timedelta
import logging
from populate_database import get_db_connection

# Logging setup
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
EXPIRATION_DAYS = 7


def deactivate_stale_listings(conn):
    cutoff_date = datetime.utcnow() - timedelta(days=EXPIRATION_DAYS)
    logger.info(f"Marking listings with updated_at older than {cutoff_date} as inactive...")

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE listings
                SET is_active = FALSE
                WHERE is_active = TRUE AND updated_at < %s
            """, (cutoff_date,))
            affected = cursor.rowcount
            conn.commit()
            logger.info(f"Deactivated {affected} outdated listings.")
    except Exception as e:
        conn.rollback()
        logger.exception(f"Error while deactivating listings: {e}")

def main():
    conn = get_db_connection()
    if conn:
        deactivate_stale_listings(conn)
        conn.close()

if __name__ == "__main__":
    main()
