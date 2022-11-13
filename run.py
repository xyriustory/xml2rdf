import logging
import os
logging.basicConfig(level=logging.DEBUG)

from app import server

if __name__ == '__main__':
    server.app.run(host='localhost', port=int(os.environ.get('PORT', 9000)), debug=True)