#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import time
import uuid
from threading import Thread

import hjson
import requests
import sqlalchemy
import telegram
import validators
from flask import request, make_response, Blueprint, render_template, send_from_directory
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from telegram.ext import Dispatcher

from app_root import bot_helper
from app_root.ConstValue import *
from app_root.DbOperation import DbOperation
from dymodules.ConsolePrintWithColor import ConsolePrintWithColor as ConColor
from dymodules.database_module import *

bp = Blueprint('bot', __name__
               , template_folder='../../templates'
               , static_folder='../../static'
               )
bh = None
debug_target_user_id = -1
db_obj = DbOperation(os.path.join(bp.static_folder, 'smartqq.db'))

config_file_path = os.path.join(bp.static_folder, '../', 'config.json')
use_queue = False
release_error_text = '系统发生错误'
prohibit_key = ['telegram_bot_api', 'administrator_id']

try:
    if os.path.exists(config_file_path):
        bh = bot_helper.BotHelper(config_file_path, 'telegram_bot_api', use_queue)
        debug_target_user_id = bh.get_config('administrator_id', '-1')
        if use_queue:
            thread = Thread(target=bh.start_dispatcher, name='dispatch')
            thread.start()
    else:
        raise FileNotFoundError('bot config [%s] not found' % config_file_path)
except Exception as exx:
    print(ConColor.red_on_black(exx))

# init script begin
# set webhook if set
if bh is not None and bh.get_config('set_hook', '0') != '0':
    if bh.get_config('telegram_web_hook_url') is not None:
        updater = telegram.ext.Updater(token=bh.get_config('telegram_bot_api'))
        if validators.url(bh.get_config('telegram_web_hook_url'), public=True):
            updater.bot.setWebhook(bh.get_config('telegram_web_hook_url'))
            print('web_hook set to [{0}] '.format(bh.get_config('telegram_web_hook_url')))
        else:
            updater.bot.deleteWebhook()
            print('web_hook deleted')
    else:
        print('web hook None\n Not Changed')


# init script end


def __reply_msg(bot, update, message_string, parse_mode=None):
    """
    回复文本消息到Telegram 客户端
    :param bot: telegram bot 对象
    :param update: telegram update 对象
    :param message_string: 文本消息
    :param parse_mode: 处理文本方式,HTML或者Markdown
    :return: 
    """
    bot.send_message(reply_to_message_id=update.message.message_id
                     , chat_id=update.message.chat_id
                     , text=message_string
                     , parse_mode=parse_mode)
    pass


def __reply_error(bot, update, error_message, **kwargs):
    """
    回复错误信息文本到Telegram 客户端
    :param bot: telegram bot 对象
    :param update: telegram update 对象
    :param error_message: 错误信息
    :return: 
    """
    # 如果是Debug用户,则返回详细错误信息
    if str(update.message.from_user.id) == str(debug_target_user_id):
        __reply_msg(bot, update, error_message, kwargs)
    else:
        __reply_msg(bot, update, release_error_text)


@bp.route('/', methods=['POST', 'GET'])
def index():
    return_template_view = render_template('default.html', title='TelegramSmartQQ-Bot'
                                           , message=release_error_text)
    if request.method == 'GET':
        return return_template_view
    else:
        data = request.get_data(as_text=True)
        if data == '' or data is None:
            return return_template_view
        else:
            t = hjson.loads(data)
            wh_update = telegram.Update.de_json(t, bh.bot)
            if bh.get_config("debug", 0) != 0:
                print(ConColor.yellow_on_black(hjson.dumpsJSON(data, indent=True)))
            msg = get_message_entity_from_update(wh_update)
            if msg[0] != 'none':
                telegram_response_text = '[%s] [%s] Message From [%s,%s (@%s),%s] at Chat [%s]' % (
                    ConColor.blue_on_black(msg[0])
                    , ConColor.purple_on_black(get_message_type_name_desc(msg[1]))
                    , ConColor.dark_green_on_black(msg[1].from_user.first_name)
                    , ConColor.dark_green_on_black(msg[1].from_user.last_name)
                    , ConColor.blue_on_black(msg[1].from_user.username)
                    , ConColor.gold_on_black(msg[1].from_user.id)
                    , (ConColor.green_on_black(msg[1].chat.title) if str(msg[0]).lower() == 'general' else '')

                )
                print(telegram_response_text)
            if use_queue:
                bh.put_queue(wh_update)
            else:
                bh.process_update_message(wh_update)
    return make_response(bh.http_204(), 204)


@bp.route('/favicon.ico', methods=['GET'])
def fav_icon():
    static_folder = os.path.join(bp.root_path, '../', '../', '../', 'static')
    # return static_folder
    return send_from_directory(static_folder, 'telegram_bot.ico'
                               , mimetype='image/vnd.microsoft.icon')


@bp.route('/set', methods=['POST'])
def set_web_hook():
    web_hook = request.form['url']
    if web_hook is None:
        return "Url Error\n"
    else:
        web_updater = telegram.ext.Updater(token=bh.get_config('telegram_bot_api'))
        web_updater.bot.setWebhook(web_hook)
        return 'hook {0} set ok\n'.format(web_hook)


##########################################################
# MojoQQ相关命令响应
##########################################################
@bh.register_common_handler('refresh_meta', pass_args=True)
@bh.check_self_bot()
@bh.check_chat_type(telegram.Chat.PRIVATE, False)
@bh.check_user_id(debug_target_user_id, False)
def proc_refresh_mojo_qq_meta(bot, update, args):
    request_url = '%s/get_friend_info' % bh.get_config('mojo_qq_api_base', 'http://127.0.0.1:10000/openqq')
    friend_list = requests.get(request_url).json()
    db_obj.truncate_table_entity(MojoQqFriendInfo)

    request_url = '%s/get_group_basic_info' % bh.get_config('mojo_qq_api_base', 'http://127.0.0.1:10000/openqq')
    group_list = requests.get(request_url).json()
    db_obj.truncate_table_entity(MojoQqGroupInfo)

    request_url = '%s/get_discuss_info' % bh.get_config('mojo_qq_api_base', 'http://127.0.0.1:10000/openqq')
    discuss_list = requests.get(request_url).json()
    db_obj.truncate_table_entity(MojoQqDiscussInfo)

    for item in friend_list:
        friend = MojoQqFriendInfo(
            id=str(uuid.uuid1())
            , uid=item.get('uid')
            , mark_name=item.get('markname')
            , nick_name=item.get('name')
            , group_name=item.get('category')
            , session_id=item.get('id')
        )
        db_obj.add_entity(friend)
    all_friend = db_obj.query(MojoQqFriendInfo).count()

    for item in group_list:
        group = MojoQqGroupInfo(
            id=str(uuid.uuid1())
            , uid=item.get('uid')
            , name=item.get('name')
            , mark_name=item.get('markname')
            , session_id=item.get('id')
        )
        db_obj.add_entity(group)
    all_group = db_obj.query(MojoQqGroupInfo).count()

    for item in discuss_list:
        discuss = MojoQqDiscussInfo(
            id=str(uuid.uuid1())
            , uid=item.get('id')
            , owner_id=item.get('owner_id')
            , name=item.get('name')
        )
        db_obj.add_entity(discuss)
    all_discuss = db_obj.query(MojoQqDiscussInfo).count()

    __reply_msg(bot, update, 'Update OK `%s` Friends, `%s` Groups, `%s` Discussions' % (
        all_friend, all_group, all_discuss), parse_mode=telegram.ParseMode.MARKDOWN)
    pass


@bh.register_common_handler('link', pass_args=True)
@bh.check_self_bot()
@bh.check_chat_type(telegram.Chat.PRIVATE, False)
@bh.check_user_id(debug_target_user_id, False)
def proc_link_qq_friend(bot, update, args):
    if len(args) != 1:
        __reply_msg(bot, update, 'Need Query')
        return

    inline_button = []

    # query friend
    friend_query_result = db_obj.query(MojoQqFriendInfo).filter(
        sqlalchemy.text('mark_name like :m or nick_name like :m')
    ).params(m='%{0}%'.format(args[0])).all()
    for item in friend_query_result:
        btn_text = '%s %s' % (EMOJI_QQ_USER, item.nick_name)
        if item.mark_name is not None and item.mark_name != '':
            btn_text = item.mark_name
        inline_button.append([telegram.InlineKeyboardButton(
            text=btn_text
            , callback_data='mojo_link|%s|%s' % (item.uid, QQ_USER)
        )])

    # query discussion
    discussion_query_result = db_obj.query(MojoQqDiscussInfo).filter(
        sqlalchemy.text('name like :m')
    ).params(m='%{0}%'.format(args[0])).all()
    for item in discussion_query_result:
        btn_text = '%s %s' % (EMOJI_QQ_DISCUSSION, item.name)  # discussion emoji
        inline_button.append([telegram.InlineKeyboardButton(
            text=btn_text
            , callback_data='mojo_link|%s|%s' % (item.uid, QQ_DISCUSSION)
        )])

    cancel_btn = telegram.InlineKeyboardButton(text='Cancel', callback_data='mojo_link|cancel|NG')
    inline_button.append([cancel_btn])

    final_markup = inline_button
    markup = telegram.InlineKeyboardMarkup(final_markup)
    bot.send_message(chat_id=update.message.chat.id
                     , text='选择需要绑定的用户'
                     , reply_markup=markup)
    pass


@bh.register_common_handler('chat', pass_args=True)
@bh.check_self_bot()
@bh.check_chat_type(telegram.Chat.PRIVATE, False)
@bh.check_user_id(debug_target_user_id, False)
def proc_start_new_qq_chat(bot, update, args):
    if len(args) != 1:
        __reply_msg(bot, update, 'Need Query')
        return

    inline_button = []

    # query friend
    friend_query_result = db_obj.query(MojoQqFriendInfo).filter(
        sqlalchemy.text('mark_name like :m or nick_name like :m')
    ).params(m='%{0}%'.format(args[0])).all()
    for item in friend_query_result:
        btn_text = '%s %s' % (EMOJI_QQ_USER, item.nick_name)
        if item.mark_name is not None and item.mark_name != '':
            btn_text = '%s %s' % (EMOJI_QQ_USER, item.mark_name)
        inline_button.append([telegram.InlineKeyboardButton(
            text=btn_text
            , callback_data='mojo_chat|%s|%s|%s' % (item.uid, QQ_USER, btn_text)
        )])

    # query discussion
    discussion_query_result = db_obj.query(MojoQqDiscussInfo).filter(
        sqlalchemy.text('name like :m')
    ).params(m='%{0}%'.format(args[0])).all()
    for item in discussion_query_result:
        btn_text = '%s %s' % (EMOJI_QQ_DISCUSSION, item.name)  # discussion emoji
        inline_button.append([telegram.InlineKeyboardButton(
            text=btn_text
            , callback_data='mojo_chat|%s|%s|%s' % (item.uid, QQ_DISCUSSION, btn_text)
        )])

    cancel_btn = telegram.InlineKeyboardButton(text='Cancel', callback_data='mojo_chat|cancel|NG')
    inline_button.append([cancel_btn])

    final_markup = inline_button
    markup = telegram.InlineKeyboardMarkup(final_markup)
    bot.send_message(chat_id=update.message.chat.id
                     , text='选择需要对话的用户'
                     , reply_markup=markup)


@bh.register_common_handler('bind', pass_args=True)
@bh.check_self_bot()
@bh.check_chat_type('%s,%s' % (telegram.Chat.GROUP, telegram.Chat.SUPERGROUP), False)
@bh.check_user_id(debug_target_user_id, False)
def proc_mojo_bind(bot, update, args):
    if len(args) != 2:
        __reply_error(bot, update, 'args error')
        return
    message = get_message_entity_from_update(update)
    if message[1] is None:
        return
    chat_id = message[1].chat.id

    # check group creator
    group_admin = bot.get_chat_administrators(chat_id=chat_id)

    found = [a for a in group_admin if (a.status == telegram.ChatMember.CREATOR
                                        and str(a.user.id) == debug_target_user_id)]

    if len(found) == 0:
        __reply_error(bot, update, 'Group Creator Only')
        return

    check_link_exist = db_obj.check_mojo_link(chat_id)
    if check_link_exist is not None:
        __reply_msg(bot, update, 'Group Already Linked')
    else:
        qq_type = None
        if str(args[1]).lower() == 'u':
            qq_type = 'friend_message'
        if str(args[1]).lower() == 'g':
            qq_type = 'group_message'
        if str(args[1]).lower() == 'd':
            qq_type = 'discuss_message'

        if qq_type is not None:
            link_object = MojoQqConversationLink(
                id=str(uuid.uuid1())
                , telegram_id=str(chat_id)
                , mojo_qq_id=str(args[0])
                , mojo_qq_type=qq_type
            )
            db_obj.add_entity(link_object)
            __reply_msg(bot, update, 'Link OK')
        else:
            __reply_msg(bot, update, 'args error')


@bh.register_common_handler('unbind', pass_args=True)
@bh.check_self_bot()
@bh.check_chat_type('%s,%s' % (telegram.Chat.GROUP, telegram.Chat.SUPERGROUP), False)
@bh.check_user_id(debug_target_user_id, False)
def proc_mojo_unbind(bot, update, args):
    message = get_message_entity_from_update(update)
    if message[1] is None:
        return
    chat_id = message[1].chat.id
    check_link_exist = db_obj.check_mojo_link(chat_id)
    if check_link_exist is None:
        __reply_msg(bot, update, 'Group Not Linked')
    else:
        db_obj.query(MojoQqConversationLink).filter(
            MojoQqConversationLink.telegram_id == str(chat_id)).delete()
        __reply_msg(bot, update, 'Unlink OK')


@bh.register_common_handler('info', pass_args=True)
@bh.check_self_bot()
@bh.check_chat_type('%s,%s' % (telegram.Chat.GROUP, telegram.Chat.SUPERGROUP), False)
@bh.check_user_id(debug_target_user_id, False)
def proc_mojo_info(bot, update, args):
    message = get_message_entity_from_update(update)
    if message[1] is None:
        return
    chat_id = message[1].chat.id
    check_link_exist = db_obj.check_mojo_link(chat_id)
    if check_link_exist is None:
        __reply_msg(bot, update, 'Group Not Linked')
    else:
        found = db_obj.query(MojoQqConversationLink).filter(
            MojoQqConversationLink.telegram_id == str(chat_id)).one()

        if found.mojo_qq_type == QQ_USER:
            found_user = db_obj.query(MojoQqFriendInfo).filter(
                MojoQqFriendInfo.uid == found.mojo_qq_id
            )
            try:
                _try = found_user.one()
                _t_mark_name = _try.mark_name
                _t_name = _try.nick_name
                if _t_mark_name != '' and _t_mark_name is not None:
                    _t_name = _t_mark_name
                __reply_msg(bot, update
                            , '`Linked with %s %s (%s)`' % (EMOJI_QQ_USER, _t_name, _try.uid)
                            , parse_mode=telegram.ParseMode.MARKDOWN)
            except NoResultFound:
                __reply_msg(bot, update, 'Linked user not found in table')

        if found.mojo_qq_type == QQ_DISCUSSION:
            found_user = db_obj.query(MojoQqDiscussInfo).filter(
                MojoQqDiscussInfo.uid == found.mojo_qq_id
            )
            try:
                _try = found_user.one()
                __reply_msg(bot, update
                            , '`Linked with %s %s (讨论组)`' % (EMOJI_QQ_DISCUSSION, _try.name)
                            , parse_mode=telegram.ParseMode.MARKDOWN)
            except NoResultFound:
                __reply_msg(bot, update, 'Linked Discussion not found in table')


@bh.register_callback_handler('mojo_link')
def proc_mojo_link_callback(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    text = query.data
    array_text = text.split('|')
    msg_id = update.callback_query.message.message_id

    if array_text[1] == 'cancel':
        bot.editMessageText(chat_id=chat_id, message_id=msg_id, text='cancelled')
    else:
        telegram_return_message = 'use `/bind %s %s` to bind a qq chat to the group you want' % (
            array_text[1], array_text[2]
        )
        bot.editMessageText(chat_id=chat_id
                            , message_id=msg_id
                            , text=telegram_return_message
                            , parse_mode=telegram.ParseMode.MARKDOWN)
    pass


@bh.register_callback_handler('mojo_chat')
def proc_mojo_chat_callback(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    text = query.data
    array_text = text.split('|')
    msg_id = update.callback_query.message.message_id

    if array_text[1] == 'cancel':
        bot.editMessageText(chat_id=chat_id, message_id=msg_id, text='cancelled')
    else:
        telegram_return_message = 'reply this to chat with %s' % array_text[3]
        db_obj.cache_message(msg_id, array_text[1], array_text[2])
        bot.editMessageText(chat_id=chat_id
                            , message_id=msg_id
                            , text=telegram_return_message
                            , parse_mode=telegram.ParseMode.MARKDOWN)
    pass


##########################################################
# 配置,控制相关
##########################################################


@bh.register_common_handler('setconfig', pass_args=True)
@bh.check_self_bot()
@bh.check_chat_type(telegram.Chat.PRIVATE, False)
@bh.check_user_id(debug_target_user_id, False)
def prox_bot_config_set_value(bot, update, args):
    if len(args) < 2:
        __reply_error(bot, update, 'args missing')
    else:
        config_key = args[0]
        if config_key in prohibit_key:
            __reply_error(bot, update, 'key prohibited')
        else:
            config_value = ' '.join(args[1:])
            ok_message = '`%s` = `%s`' % (config_key, config_value)
            console_ok_message = 'set config %s = %s' % (ConColor.green_on_black(config_key), config_value)
            print(console_ok_message)
            if bh.set_config(config_key, config_value):
                __reply_msg(bot, update, ok_message, parse_mode=telegram.ParseMode.MARKDOWN)
            else:
                __reply_error(bot, update, 'error')
    pass


@bh.register_common_handler('delconfig', pass_args=True)
@bh.check_self_bot()
@bh.check_chat_type(telegram.Chat.PRIVATE, False)
@bh.check_user_id(debug_target_user_id, False)
def prox_bot_config_del_key(bot, update, args):
    if len(args) > 1:
        __reply_error(bot, update, 'too many args')
    else:
        config_key = args[0]
        if prohibit_key.index(config_key):
            __reply_error(bot, update, 'key prohibited')
        else:
            ok_message = 'remove config `%s`' % config_key
            console_ok_message = 'remove config [%s]' % (ConColor.red_on_black(config_key))
            print(console_ok_message)
            if bh.set_config(config_key, None):
                __reply_msg(bot, update, ok_message, parse_mode=telegram.ParseMode.MARKDOWN)
            else:
                __reply_error(bot, update, 'error')


@bh.register_common_handler('getconfig', pass_args=True)
@bh.check_self_bot()
@bh.check_chat_type(telegram.Chat.PRIVATE, False)
@bh.check_user_id(debug_target_user_id, False)
def prox_bot_config_get_value(bot, update, args):
    if len(args) > 1:
        __reply_error(bot, update, 'too many args')
    else:
        config_key = args[0]
        config_value = bh.get_config(config_key, None)
        ok_message = 'get config `%s`,type= `%s` ,value= `%s`' % (config_key, type(config_value), config_value)
        console_ok_message = 'get config [%s],type=[%s],value=[%s]' % (
            ConColor.green_on_black(config_key)
            , type(config_value), config_value)
        print(console_ok_message)
        if bh.set_config(config_key, config_value):
            __reply_msg(bot, update, ok_message, parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            __reply_error(bot, update, 'error')
    pass


@bh.register_common_handler('reload')
@bh.check_self_bot()
@bh.check_chat_type(telegram.Chat.PRIVATE, False)
@bh.check_user_id(debug_target_user_id, False)
def proc_bot_config_reload(bot, update):
    cfg = os.path.join(bp.root_path, 'config.json')
    if os.path.exists(cfg):
        bh.load_config(cfg)
        __reply_msg(bot, update, 'Reload OK')
    else:
        __reply_error(bot, update, 'config [%s] not found' % cfg)


@bh.register_common_handler('showconfig')
@bh.check_self_bot()
@bh.check_chat_type(telegram.Chat.PRIVATE, False)
@bh.check_user_id(debug_target_user_id, False)
def proc_bot_config_confirm(bot, update):
    if os.path.exists(config_file_path):
        msg = hjson.load(open(config_file_path))
        code_msg = '```\n %s \n```' % hjson.dumpsJSON(msg, indent=True, sort_keys=True)
        __reply_msg(bot, update, code_msg, parse_mode=telegram.ParseMode.MARKDOWN)
    else:
        __reply_error(bot, update, 'config [%s] not found' % config_file_path)


@bh.register_common_handler('reboot')
@bh.check_self_bot()
@bh.check_chat_type(telegram.Chat.PRIVATE, False)
@bh.check_user_id(debug_target_user_id, False)
def proc_bot_reboot(bot, update):
    if bh.get_config('reboot', 0) == 1:
        print(ConColor.white_on_purple('Bot Started Successfully'))
        bot.sendMessage(update.message.chat_id, 'Bot Started Successfully')
        bh.set_config('reboot', None)
        bh.refresh_config()
    else:
        bh.set_config('reboot', 1)
        print(ConColor.white_on_purple('Bot is going to restart'))
        bot.sendMessage(update.message.chat_id, 'Bot is restarting...\nWaiting 20 sec for bot to response')
        time.sleep(5)
        os.execl(sys.executable, sys.executable, *sys.argv)


##########################################################
# 隐藏菜单,回调相关
##########################################################


@bh.register_common_handler('leave', pass_args=True)
@bh.check_self_bot()
@bh.check_chat_type(telegram.Chat.PRIVATE, False)
@bh.check_user_id(debug_target_user_id, False)
def proc_leave_group(bot, update, args):
    if len(args) != 1:
        return
    confirm_btn = [
        [telegram.InlineKeyboardButton('Yes', callback_data='leave_group_yes|%s' % args[0]),
         telegram.InlineKeyboardButton('No', callback_data='leave_group_no')]
    ]

    markup = telegram.InlineKeyboardMarkup(confirm_btn)
    bot.send_message(chat_id=update.message.chat.id
                     , text='Confirm to leave ?'
                     , reply_markup=markup)


@bh.register_callback_handler('leave_group')
def proc_leave_group_callback(bot, update):
    query = update.callback_query
    chat_id = query.message.chat.id
    text = query.data
    msg_id = update.callback_query.message.message_id
    if text.find('yes') > -1:
        leave_id = text.split('|')[1]
        bot.leave_chat(chat_id=leave_id)
        bot.editMessageText(text='OK', chat_id=chat_id, message_id=msg_id)
    if text.find('no') > -1:
        bot.editMessageText(text='Cancelled', chat_id=chat_id, message_id=msg_id)


##########################################################
# 隐藏菜单,回调相关
##########################################################


@bh.register_message_handler(telegram.ext.Filters.text)
def proc_all_text_msg(bot, update):
    p_message = update.message

    if p_message.reply_to_message is not None:
        print(ConColor.blue_on_black('process reply msg'))
        chat_id = p_message.reply_to_message.chat.id
        msg_id = p_message.reply_to_message.message_id
        found = db_obj.query(MojoQqConversation).filter(
            MojoQqConversation.telegram_message_id == str(msg_id)
        )
        mojo_qq_msg = p_message.text
        try:
            _try = found.one()
            send_message_to_mojo(_try.mojo_qq_target_id, _try.mojo_qq_target_type, mojo_qq_msg)
        except NoResultFound:
            print(ConColor.red_on_black('NOT found in db'))
            __reply_msg(bot, update, 'Chat Not found in db')
            return
            pass
        except MultipleResultsFound:
            m = ''
            for item in found:
                m += '%s,%s,%s\n' % (item.telegram_message_id, item.mojo_qq_target_id, item.mojo_qq_target_type)
                print(m)
            return
        except Exception as exx:
            print(exx)
            return
    else:
        chat_id = p_message.chat.id
        mojo_qq_msg = update.message.text
        # check if forwoard to mojo
        found = db_obj.query(MojoQqConversationLink).filter(
            MojoQqConversationLink.telegram_id == str(chat_id)
        )
        try:
            _try = found.one()
            send_message_to_mojo(_try.mojo_qq_id, _try.mojo_qq_type, mojo_qq_msg)
        except NoResultFound:
            return
            pass
        except MultipleResultsFound:
            return
        except Exception as exx:
            print(exx)
            return
        pass


##########################################################
# 内部方法
##########################################################

def query_message_for_qq_to_send(reply_msg_id):
    found = db_obj.database.query(MojoQqConversation).filter(
        MojoQqConversation.telegram_message_id == str(reply_msg_id)
    )
    try:
        _try = found.one()
        return _try
    except NoResultFound:
        return None


def send_message_to_mojo(target_uid, target_type, content):
    mojo_send_msg_api_url = None
    if target_type == QQ_USER:
        mojo_send_msg_api_url = 'send_friend_message?uid=%s&content=%s' % (target_uid, content)
    if target_type == QQ_DISCUSSION:
        mojo_send_msg_api_url = 'send_discuss_message?id=%s&content=%s' % (target_uid, content)

    if mojo_send_msg_api_url is not None:
        # try to call mojo_qq api to send the msg
        full_request_url = '%s/%s' % (
            bh.get_config('mojo_qq_api_base', 'http://127.0.0.1:10000/openqq')
            , mojo_send_msg_api_url)
        return requests.get(full_request_url).json()

    return None


def get_message_type_name_desc(message):
    sys_property = ['new_chat_member',
                    'left_chat_member',
                    'new_chat_title',
                    'new_chat_photo',
                    'delete_chat_photo',
                    'group_chat_created',
                    'supergroup_chat_created',
                    'migrate_to_chat_id',
                    'migrate_from_chat_id',
                    'channel_chat_created',
                    'pinned_message']
    for i in sys_property:
        if getattr(message, i, False):
            return 'system'
    msg_property = ['audio',
                    'document',
                    'photo',
                    'sticker',
                    'video',
                    'voice',
                    'contact',
                    'location',
                    'venue']
    for i in msg_property:
        if getattr(message, i, False):
            return i.capitalize()
    return 'Text'


def get_message_entity_from_update(update):
    m_type = 'General'
    try:
        message = update.message
        if message is None:
            message = update.edited_message
            m_type = 'Edited'
            if message is None:
                message = update.inline_query
                m_type = 'Inline'
                if message is None:
                    message = update.callback_query
                    m_type = 'Callback'
                    if message is None:
                        message = update.chosen_inline_result
                        m_type = 'Chosen_inline'

        return m_type, message
    except Exception as exx:
        print(ConColor.red_on_black(exx))
        return 'none', None
    pass


