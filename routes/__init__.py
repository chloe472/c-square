
from flask import Flask

app = Flask(__name__)

# Import the ticketing agent module (with underscore, not hyphen)
import routes.ticketing_agent