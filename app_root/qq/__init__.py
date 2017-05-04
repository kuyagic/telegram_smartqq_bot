#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hjson
import telegram
from flask import Blueprint, render_template, make_response, request
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from app_root import bot_helper
from dymodules.database_module import *

bp = Blueprint('mojo_qq', __name__
               , template_folder='../../templates'
               , static_folder='../../static')
bh = None
db_obj = DatabaseHelper(os.path.join(bp.static_folder, 'smartqq.db'))

config_file_path = os.path.join(bp.static_folder, '../', 'config.json')

if os.path.exists(config_file_path):
    bh = bot_helper.BotHelper(config_file_path, 'telegram_bot_api', False)


@bp.route('/', methods=['GET', 'POST'])
def index():
    return_template_view = render_template('default.html', title='MojoQQ Bridge'
                                           , message='Working')
    if request.method == 'GET':
        return return_template_view
    else:
        data = request.get_data(as_text=True)
        if data == '' or data is None:
            return return_template_view
        else:
            # print(data)
            reported_data = hjson.loads(data)
            if reported_data.get('post_type') == 'event':
                event_type = reported_data.get('event')
                if event_type == 'input_qrcode':
                    print('input_qr')
                    qr_img_file_path = reported_data.get('params')[0]
                    print(qr_img_file_path)
                    bh.bot.send_photo(chat_id=bh.get_config('administrator_id')
                                      , photo=open(qr_img_file_path, 'rb'))
            if reported_data.get('post_type') == 'receive_message' and reported_data.get('class') == 'recv':
                if str(bh.get_config('qq_push_type', 'friend_message,discuss_message')
                       ).find(reported_data.get('type')) > -1:
                    # found type
                    message_from = reported_data.get('type')
                    return_message = None
                    mojo_source_uid = None
                    if message_from == 'friend_message':
                        mojo_source_uid = reported_data.get('sender_uid')
                        return_message = '`%s (%s)`\n%s' % (
                            reported_data.get('sender')
                            , reported_data.get('sender_uid')
                            , reported_data.get('content'))
                    if message_from == 'discuss_message':
                        mojo_source_uid = reported_data.get('discuss_id')
                        return_message = '`%s@%s`\n%s' % (
                            reported_data.get('sender')
                            , reported_data.get('discuss')
                            , reported_data.get('content'))
                    if return_message is not None:
                        # print(return_message)
                        # print('get_link_chat, %s,%s' % (mojo_source_uid, message_from))
                        target_telegram_chat = get_link_chat(mojo_source_uid, message_from)
                        target_telegram_chat_id = bh.get_config('administrator_id', '-1')
                        if target_telegram_chat is not None and target_telegram_chat_id != '-1':
                            target_telegram_chat_id = target_telegram_chat
                        bh.bot.send_message(chat_id=target_telegram_chat_id
                                            , text=return_message
                                            , parse_mode=telegram.ParseMode.MARKDOWN)
        return make_response(bh.http_204(), 204)


def get_link_chat(mojo_chat_id, mojo_chat_type):
    try:
        found = db_obj.database.query(MojoQqConversionLink).filter(
            MojoQqConversionLink.mojo_qq_id == str(mojo_chat_id)
            , MojoQqConversionLink.mojo_qq_type == mojo_chat_type
        ).one()
        return found.telegram_id
    except (NoResultFound, MultipleResultsFound):
        return None
    except Exception as exx:
        print(exx)
        return None
