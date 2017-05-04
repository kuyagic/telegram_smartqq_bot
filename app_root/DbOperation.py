import uuid

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from dymodules.database_module import *


class DbOperation:
    _database_orm_object = None

    def __init__(self, data_base_file_path):
        self._database_orm_object = DatabaseHelper(data_base_file_path)

    def get_link_chat(self, mojo_chat_id, mojo_chat_type):
        try:
            found = self._database_orm_object.database.query(MojoQqConversationLink).filter(
                MojoQqConversationLink.mojo_qq_id == str(mojo_chat_id)
                , MojoQqConversationLink.mojo_qq_type == mojo_chat_type
            ).one()
            return found.telegram_id
        except (NoResultFound, MultipleResultsFound):
            return None
        except Exception as exx:
            print(exx)
            return None

    def check_mojo_link(self, telegram_chat_id):
        found = None
        try:
            found = self._database_orm_object.database.query(MojoQqConversationLink).filter(
                MojoQqConversationLink.telegram_id == str(telegram_chat_id)
            )
            _try = found.one()
            return _try
        except MultipleResultsFound:
            print('MultipleResultsFound, %s' % found.count())
            for item_multi in found:
                self._database_orm_object.database.delete(item_multi)
                self._database_orm_object.database.commit()
            return None
        except NoResultFound:
            return None

    def cache_message(self, msg_id, mojo_qq_uid, mojo_qq_type):
        conv = MojoQqConversation(
            id=str(uuid.uuid1())
            , mojo_qq_target_id=str(mojo_qq_uid)
            , telegram_message_id=str(msg_id)
            , mojo_qq_target_type=str(mojo_qq_type)
        )
        self._database_orm_object.database.add(conv)
        self._database_orm_object.database.commit()

    def add_entity(self, entity):
        self._database_orm_object.database.add(entity)
        self._database_orm_object.database.commit()

    def truncate_table_entity(self, entity):
        self._database_orm_object.database.query(entity).delete()

    def query(self, entity):
        return self._database_orm_object.database.query(entity)
