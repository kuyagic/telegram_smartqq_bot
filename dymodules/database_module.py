import os

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

entity_base = declarative_base()


class MojoQqFriendInfo(entity_base):
    __tablename__ = 'mojo_qq_friend'
    id = Column(String, primary_key=True)
    uid = Column(String)
    mark_name = Column(String)
    nick_name = Column(String)
    group_name = Column(String)
    session_id = Column(String)


class MojoQqGroupInfo(entity_base):
    __tablename__ = 'mojo_qq_group'
    id = Column(String, primary_key=True)
    name = Column(String)
    mark_name = Column(String)
    uid = Column(String)
    session_id = Column(String)


class MojoQqDiscussInfo(entity_base):
    __tablename__ = 'mojo_qq_discuss'
    id = Column(String, primary_key=True)
    owner_id = Column(String)
    name = Column(String)
    uid = Column(String)
    session_id = Column(String)


class MojoQqConversation(entity_base):
    __tablename__ = 'mojo_qq_conversation'
    id = Column(String, primary_key=True)
    telegram_message_id = Column(Integer)
    mojo_qq_target_id = Column(String)
    mojo_qq_target_type = Column(String)


class MojoQqConversationLink(entity_base):
    __tablename__ = 'mojo_qq_conv_link'
    id = Column(String, primary_key=True)
    telegram_id = Column(String)
    mojo_qq_id = Column(String)
    mojo_qq_type = Column(String)
    mojo_qq_session_id = Column(String)


class DatabaseHelper:
    __database_file = None
    __session = None
    database = None

    def __init__(self, db_file_path):
        self.__database_file = os.path.abspath(db_file_path)
        db_file = 'sqlite:///%s' % ('' if self.__database_file is None else self.__database_file)
        # print(self.__database_file)
        engine = create_engine(db_file)
        self.__session = sessionmaker()
        self.__session.configure(bind=engine)
        self.database = self.__session()
        entity_base.metadata.create_all(engine)
