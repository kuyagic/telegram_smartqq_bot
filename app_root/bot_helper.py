import hjson
import telegram
from telegram import Bot
from telegram.ext import Dispatcher

from dymodules.ConsolePrintWithColor import ConsolePrintWithColor as ConColor


class BotHelper:
    """
    机器人帮助类
    """
    _job_queue = None
    _dispatcher = None
    _config_file_path = None
    _telegram_bot_api_key = ''
    bot = None
    bot_config = None

    def __init__(self, config_file_path, config_api_key, use_queue=True):
        """
        构造函数
        :param config_file_path: 配置文件绝对路径
        :param config_api_key: Telegram API Key 对应的配置文件项目名称(Key)
        :param use_queue: 是否使用消息队列处理API请求
        """
        self._config_file_path = config_file_path
        self.load_config(self._config_file_path)
        api_key = self.get_config(config_api_key, None)
        if api_key is None:
            raise ValueError('Telegram API Key Item Not Found in config with the json-key %s' % config_api_key)
        else:
            self.bot = Bot(api_key)
            if use_queue:
                self._job_queue = telegram.ext.updater.Queue()
                self._dispatcher = Dispatcher(self.bot, self._job_queue, workers=8)
            else:
                self._dispatcher = Dispatcher(self.bot, None, workers=8)

    def register_common_handler(self, cmd, **kw):
        """
        注册 指令 处理器
        :param cmd: 指令
        :param kw: 参数
        :return: 处理函数
        """

        def func_receiver(func):
            self._dispatcher.add_handler(
                telegram.ext.CommandHandler(cmd, func, **kw))
            return func

        return func_receiver

    def register_message_handler(self, telegram_message_filter, **kw):
        """
        注册 通用消息 处理器
        :param telegram_message_filter: telegram消息类型
        :param kw: 参数
        :return: 处理函数
        """

        def func_receiver(func):
            self._dispatcher.add_handler(
                telegram.ext.MessageHandler(telegram_message_filter, func, **kw)
            )
            return func

        return func_receiver

    def register_callback_handler(self, callback_pattern, **kw):
        """
        注册 回调消息 处理器
        :param callback_pattern: 回调过滤器
        :param kw: 参数
        :return: 处理函数
        """

        def func_receiver(func):
            self._dispatcher.add_handler(
                telegram.ext.CallbackQueryHandler(func, pattern=callback_pattern, **kw)
            )
            return func

        return func_receiver

    def start_dispatcher(self):
        """
        启动 Dispatcher
        :return: 
        """
        self._dispatcher.start()

    def put_queue(self, ext_update):
        """
        添加消息到消息队列
        :param ext_update: Telegram 更新消息实体 
        :return: 
        """
        if self._job_queue is not None:
            self._job_queue.put(ext_update)

    def process_update_message(self, ext_update):
        """
        处理 一条 Telegram 更新消息
        :param ext_update: Telegram 更新消息实体 
        :return: 
        """
        self._dispatcher.process_update(ext_update)

    def load_config(self, path):
        """
        加载配置文件
        :param path: 配置文件路径 
        :return: 
        """
        self.bot_config = hjson.load(open(path))
        return True

    def refresh_config(self):
        """
        热刷新配置文件
        :return: 
        """
        self.bot_config = hjson.load(open(self._config_file_path))
        return True

    def get_config(self, key, default_value=None):
        """
        获取配置项目的值
        :param key: 配置项Key
        :param default_value: 当Key不存在时, 返回的值 
        :return: 对应配置项的Value
        """
        return self.bot_config.get(key, default_value)

    def set_config(self, config_key, config_value):
        """
        设置配置项目的值
        :param config_key: 配置项Key
        :param config_value: 配置项Value , 当值为 None 时,则删除这个配置项
        :return: 
        """
        if config_value is None:
            del self.bot_config[config_key]
        else:
            self.bot_config[config_key] = config_value
        try:
            with open(self._config_file_path, 'w') as outfile:
                hjson.dump(self.bot_config, outfile)
                return True
        except Exception as exx:
            colored_message = ConColor.red_on_black(exx)
            print(colored_message)
            return False

    @staticmethod
    def check_chat_type(telegram_chat_type, show_warn=True):
        """
        装饰函数
        检查是否被指定类型的会话调用
        :param telegram_chat_type: 类型为 private,group,supergroup,channel 
        :param show_warn: 是否返回错误提示信息
        :return: 
        """

        def decorator(f):  # 需要装饰的函数 f
            def check_args(*args, **kwds):  # 函数参数 *args
                # 判断参数过程
                msg = args[1].message
                bot = args[0]
                chat_type_array = str(telegram_chat_type).split(',')
                for t in chat_type_array:
                    if msg.chat.type == t:
                        return f(*args, **kwds)
                if show_warn:
                    bot.send_message(reply_to_message_id=msg.message_id
                                     , chat_id=msg.chat_id
                                     , text='Only available in %s chat' % telegram_chat_type)

            return check_args

        return decorator

    @staticmethod
    def check_chat_id(telegram_chat_ids):
        """
        装饰函数
        检查是否被指定的群调用
        :param telegram_chat_ids: 逗号分割的群组ID
        :return: 函数
        """

        def decorator(f):
            def check_args(*args, **kwargs):
                update = args[1]
                chat_id = update.message.chat.id
                id_array = str(telegram_chat_ids).split(',')
                for s in id_array:
                    if str(s) == str(chat_id):
                        return f(*args, **kwargs)

            return check_args

        return decorator

    @staticmethod
    def check_user_id(telegram_user_ids, show_warn=True):
        """
        装饰函数
        检查是否被指定的用户调用
        :param telegram_user_ids: 逗号分割的用户ID
        :param show_warn: 是否返回错误提示信息
        :return: 函数
        """

        def decorator(f):
            def check_args(*args, **kwargs):
                bot = args[0]
                update = args[1]
                try:
                    user_id = update.message.from_user.id
                except (NameError, AttributeError):
                    try:
                        user_id = update.inline_query.from_user.id
                    except (NameError, AttributeError):
                        try:
                            user_id = update.chosen_inline_result.from_user.id
                        except (NameError, AttributeError):
                            try:
                                user_id = update.callback_query.from_user.id
                            except (NameError, AttributeError):
                                return
                id_array = str(telegram_user_ids).split(',')
                for s in id_array:
                    if str(s) == str(user_id):
                        return f(*args, **kwargs)

                if show_warn:
                    bot.send_message(reply_to_message_id=update.message.message_id
                                     , chat_id=update.message.chat_id
                                     , text='Only available to Administrators')

            return check_args

        return decorator

    @staticmethod
    def check_self_bot():  # parse_entity
        """
        装饰函数
        检查是否是调用此Bot
        :return: 函数
        """

        def decorator(f):
            def check_args(*args, **kwargs):
                try:
                    bot = args[0]
                    update = args[1]
                    extracted_user_and_arg = update.message.text.split('@')
                    if len(extracted_user_and_arg) > 1:
                        bot_name = extracted_user_and_arg[-1].split(' ')[0]
                        if bot_name == bot.username:
                            return f(*args, **kwargs)
                        else:
                            return
                    else:
                        return f(*args, **kwargs)
                except Exception as exx:
                    colored_message = ConColor.red_on_black(exx)
                    print(colored_message)

            return check_args

        return decorator

    @staticmethod
    def http_204():
        return '\n'
