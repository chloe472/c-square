
from flask import Flask

app = Flask(__name__)

# Import route modules so their handlers register on the shared app
from . import square # <-- make sure routes/blankety.py exists

