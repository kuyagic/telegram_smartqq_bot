#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

import hjson
from flask import Flask, render_template
from gevent.wsgi import WSGIServer

from app_root.bot import bp as bp_bot
from app_root.qq import bp as bp_qq

app = Flask(__name__, template_folder='templates')

app.register_blueprint(bp_bot, url_prefix='/start')
app.register_blueprint(bp_qq, url_prefix='/qq')


@app.route('/')
def index():
    return render_template('default.html', title='TelegramSmartQQ-Bot'
                           , message='@your_bot_id')


env_file_path = os.path.join(os.path.dirname(__file__), 'env.json')
env_config = {}
if os.path.exists(env_file_path):
    env_config = hjson.load(open(env_file_path))
try:
    http_server = WSGIServer((env_config.get('host', '127.0.0.1'), env_config.get('port', 5004))
                             , app
                             , log=env_config.get('log_file', None)
                             )
    print('Server Started At %s:%s' % (env_config.get('host'), env_config.get('port')))
    http_server.serve_forever()
except KeyboardInterrupt as exx:
    print('Exiting...')
except Exception as exx:
    print(exx)
