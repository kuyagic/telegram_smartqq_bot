class ConsolePrintWithColor:
    @staticmethod
    def red_on_black(msg):
        return '\x1b[1;31;40m%s\x1b[0m' % msg

    @staticmethod
    def green_on_black(msg):
        return '\x1b[1;32;40m%s\x1b[0m' % msg

    @staticmethod
    def yellow_on_black(msg):
        return '\x1b[1;33;40m%s\x1b[0m' % msg

    @staticmethod
    def blue_on_black(msg):
        return '\x1b[1;34;40m%s\x1b[0m' % msg

    @staticmethod
    def purple_on_black(msg):
        return '\x1b[1;35;40m%s\x1b[0m' % msg

    @staticmethod
    def gold_on_black(msg):
        return '\x1b[1;36;40m%s\x1b[0m' % msg

    @staticmethod
    def white_on_black(msg):
        return '\x1b[1;37;40m%s\x1b[0m' % msg

    @staticmethod
    def dark_green_on_black(msg):
        return '\x1b[0;32;40m%s\x1b[0m' % msg

    @staticmethod
    def white_on_purple(msg):
        return '\x1b[5;37;45m%s\x1b[0m' % msg
