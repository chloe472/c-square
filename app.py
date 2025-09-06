import logging
import socket

from routes import app

logger = logging.getLogger(__name__)


@app.route("/", methods=["GET"])
def root():
    return "OK", 200

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

if __name__ == "__main__":
    logging.info("Starting application ...")
    app.run(host="0.0.0.0", port=8080)

