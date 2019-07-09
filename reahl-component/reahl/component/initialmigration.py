# Copyright 2019 Reahl Software Services (Pty) Ltd. All rights reserved.
#
#    This file is part of Reahl.
#
#    Reahl is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation; version 3 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


from alembic import op
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKeyConstraint, \
    LargeBinary, BigInteger, UniqueConstraint

from reahl.component.migration import Migration


class GenesisMigration(Migration):
    version = '2.0'

    def schedule_upgrades(self):
        self.schedule('alter', op.create_table, 'reahl_schema_version',
                      Column('id', Integer(), primary_key=True, nullable=False),
                      Column('version', String(length=50), nullable=True),
                      Column('egg_name', String(), nullable=True),
                      # PrimaryKeyConstraint('id')
                      )
        # self.schedule('indexes', op.create_index, 'reahl_schema_version_id_seq', 'reahl_schema_version', ['id'])

        self.schedule('alter', op.create_table, 'accountmanagementinterface',
                        Column('id', Integer(), primary_key=True, nullable=False),
                        Column('email', Text(), nullable=True),
                        Column('session_id', Integer(), nullable=True),
                        ForeignKeyConstraint(['session_id'], [u'usersession.id'], ondelete=u'CASCADE'),
                        #PrimaryKeyConstraint('id')
                        )
        # self.schedule('indexes', op.create_index, 'accountmanagementinterface_id_seq', 'accountmanagementinterface', ['id'])
        self.schedule('indexes', op.create_index, 'ix_accountmanagementinterface_email', 'accountmanagementinterface', ['email'], unique=False)
        self.schedule('indexes', op.create_index, 'ix_accountmanagementinterface_session_id', 'accountmanagementinterface', ['session_id'], unique=False)

        self.schedule('alter', op.create_table, 'deferredaction',
                      Column('id', Integer(), primary_key=True, nullable=False),
                      Column('deadline', DateTime(), nullable=False),
                      Column('row_type', String(length=40), nullable=True),
                      # PrimaryKeyConstraint('id')
                      )

        self.schedule('alter', op.create_table, 'queue',
                        Column('id', Integer(), primary_key=True, nullable=False),
                        Column('name', Text(), nullable=False),
                        #PrimaryKeyConstraint('id'),
                        UniqueConstraint('name')
                        )

        # self.schedule('indexes', op.create_index, 'deferredaction_id_seq', 'deferredaction', ['id'])
        self.schedule('alter', op.create_table, 'requirement',
                      Column('id', Integer(), primary_key=True,  nullable=False),
                      Column('fulfilled', Boolean(), nullable=False),
                      Column('row_type', String(length=40), nullable=True),
                      # PrimaryKeyConstraint('id')
                      )
        # self.schedule('indexes', op.create_index, 'requirement_id_seq', 'requirement', ['id'])
        self.schedule('alter', op.create_table, 'systemaccount',
                      Column('id', Integer(), primary_key=True, nullable=False),
                      Column('registration_date', DateTime(), nullable=True),
                      Column('account_enabled', Boolean(), nullable=False),
                      Column('failed_logins', Integer(), nullable=False),
                      Column('row_type', String(length=40), nullable=True),
                      # PrimaryKeyConstraint('id')
                      )
        # self.schedule('indexes', op.create_index, 'systemaccount_id_seq', 'systemaccount', ['id'])
        self.schedule('alter', op.create_table, 'activateaccount',
                      Column('deferredaction_id', Integer(), nullable=False),
                      Column('system_account_id', Integer(), nullable=True),
                      ForeignKeyConstraint(['deferredaction_id'], ['deferredaction.id'], ondelete='CASCADE'),
                      ForeignKeyConstraint(['system_account_id'], ['systemaccount.id'], initially='DEFERRED', deferrable=True),
                      # PrimaryKeyConstraint('deferredaction_id')
                      )
        self.schedule('indexes', op.create_index, 'ix_activateaccount_system_account_id', 'activateaccount', ['system_account_id'], unique=False)
        self.schedule('alter', op.create_table, 'changeaccountemail',
                      Column('deferredaction_id', Integer(), nullable=False),
                      Column('system_account_id', Integer(), nullable=True),
                      ForeignKeyConstraint(['deferredaction_id'], ['deferredaction.id'], ondelete='CASCADE'),
                      ForeignKeyConstraint(['system_account_id'], ['systemaccount.id'], initially='DEFERRED', deferrable=True),
                      # PrimaryKeyConstraint('deferredaction_id')
                      )
        self.schedule('indexes', op.create_index, 'ix_changeaccountemail_system_account_id', 'changeaccountemail', ['system_account_id'], unique=False)
        self.schedule('alter', op.create_table, 'emailandpasswordsystemaccount',
                      Column('systemaccount_id', Integer(), nullable=False),
                      Column('password_md5', String(length=32), nullable=False),
                      Column('email', Text(), nullable=False),
                      Column('apache_digest', String(length=32), nullable=False),
                      ForeignKeyConstraint(['systemaccount_id'], ['systemaccount.id'], ondelete='CASCADE'),
                      # PrimaryKeyConstraint('systemaccount_id'),
                      UniqueConstraint('email')
                      )
        self.schedule('alter', op.create_table, 'party',
                      Column('id', Integer(), primary_key=True, nullable=False),
                      Column('system_account_id', Integer(), nullable=True),
                      ForeignKeyConstraint(['system_account_id'], ['systemaccount.id'], ),
                      # PrimaryKeyConstraint('id')
                      )
        # self.schedule('indexes', op.create_index, 'party_id_seq', 'party', ['id'])
        self.schedule('indexes', op.create_index, 'ix_party_system_account_id', 'party', ['system_account_id'], unique=False)
        self.schedule('alter', op.create_table, 'requirement_deferred_actions__deferredaction_requirements',
                      Column('requirement_id', Integer(), nullable=False),
                      Column('deferredaction_id', Integer(), nullable=False),
                      ForeignKeyConstraint(['deferredaction_id'], ['deferredaction.id'], ),
                      ForeignKeyConstraint(['requirement_id'], ['requirement.id'], ),
                      # PrimaryKeyConstraint('requirement_id', 'deferredaction_id')
                      )
        self.schedule('alter', op.create_table, 'usersession',
                      Column('id', Integer(), primary_key=True, nullable=False),
                      Column('account_id', Integer(), nullable=True),
                      Column('idle_lifetime', Integer(), nullable=False),
                      Column('last_activity', DateTime(), nullable=False),
                      Column('row_type', String(length=40), nullable=True),
                      ForeignKeyConstraint(['account_id'], ['systemaccount.id'], ),
                      # PrimaryKeyConstraint('id')
                      )
        # self.schedule('indexes', op.create_index, 'usersession_id_seq', 'usersession', ['id'])
        self.schedule('indexes', op.create_index, 'ix_usersession_account_id', 'usersession', ['account_id'], unique=False)
        self.schedule('alter', op.create_table, 'verificationrequest',
                      Column('requirement_id', Integer(), primary_key=True, nullable=False),
                      Column('salt', String(length=10), nullable=False),
                      ForeignKeyConstraint(['requirement_id'], ['requirement.id'], ondelete='CASCADE'),
                      # PrimaryKeyConstraint('requirement_id')
                      )
        self.schedule('alter', op.create_table, 'newpasswordrequest',
                      Column('system_account_id', Integer(), primary_key=True, nullable=False),
                      Column('verificationrequest_requirement_id', Integer(), nullable=False),
                      ForeignKeyConstraint(['system_account_id'], ['systemaccount.id'], initially='DEFERRED', deferrable=True),
                      ForeignKeyConstraint(['verificationrequest_requirement_id'], ['verificationrequest.requirement_id'], ondelete='CASCADE'),
                      # PrimaryKeyConstraint('system_account_id', 'verificationrequest_requirement_id')
                      )
        self.schedule('indexes', op.create_index, 'ix_newpasswordrequest_system_account_id', 'newpasswordrequest', ['system_account_id'], unique=False)
        self.schedule('alter', op.create_table, 'sessiondata',
                      Column('id', Integer(), primary_key=True, nullable=False),
                      Column('web_session_id', Integer(), nullable=True),
                      Column('region_name', Text(), nullable=False),
                      Column('channel_name', Text(), nullable=False),
                      Column('row_type', String(length=40), nullable=True),
                      ForeignKeyConstraint(['web_session_id'], ['usersession.id'], name='sessiondata_web_session_id_fk', ondelete='CASCADE'),
                      # PrimaryKeyConstraint('id')
                      )
        # self.schedule('indexes', op.create_index, 'sessiondata_id_seq', 'sessiondata', ['id'])
        self.schedule('indexes', op.create_index, 'ix_sessiondata_web_session_id', 'sessiondata', ['web_session_id'], unique=False)

        self.schedule('alter', op.create_table, 'task',
                        Column('id', Integer(), primary_key=True, nullable=False),
                        Column('queue_id', Integer(), nullable=True),
                        Column('title', Text(), nullable=False),
                        Column('reserved_by_id', Integer(), nullable=True),
                        ForeignKeyConstraint(['queue_id'], ['queue.id'], ),
                        ForeignKeyConstraint(['reserved_by_id'], ['party.id'], ),
                        #PrimaryKeyConstraint('id')
                        )
        self.schedule('indexes', op.create_index, 'ix_task_queue_id', 'task', ['queue_id'], unique=False)
        self.schedule('indexes', op.create_index, 'ix_task_reserved_by_id', 'task', ['reserved_by_id'], unique=False)

        self.schedule('alter', op.create_table, 'verifyemailrequest',
                      Column('verificationrequest_requirement_id', Integer(), nullable=False),
                      Column('email', Text(), nullable=False),
                      Column('subject_config', Text(), nullable=False),
                      Column('email_config', Text(), nullable=False),
                      ForeignKeyConstraint(['verificationrequest_requirement_id'], ['verificationrequest.requirement_id'], ondelete='CASCADE'),
                      # PrimaryKeyConstraint('verificationrequest_requirement_id'),
                      UniqueConstraint('email')
                      )
        self.schedule('alter', op.create_table, 'webusersession',
                      Column('usersession_id', Integer(), primary_key=True, nullable=False),
                      Column('salt', String(length=40), nullable=False),
                      Column('secure_salt', String(length=40), nullable=False),
                      ForeignKeyConstraint(['usersession_id'], ['usersession.id'], ondelete='CASCADE'),
                      # PrimaryKeyConstraint('usersession_id')
                      )
        self.schedule('alter', op.create_table, 'persistedexception',
                      Column('sessiondata_id', Integer(), primary_key=True, nullable=False),
                      Column('exception', LargeBinary(), nullable=False),
                      Column('input_name', Text(), nullable=True),
                      ForeignKeyConstraint(['sessiondata_id'], ['sessiondata.id'], ondelete='CASCADE'),
                      # PrimaryKeyConstraint('sessiondata_id')
                      )
        self.schedule('alter', op.create_table, 'persistedfile',
                      Column('sessiondata_id', Integer(), primary_key=True, nullable=False),
                      Column('input_name', Text(), nullable=False),
                      Column('filename', Text(), nullable=False),
                      Column('file_data', LargeBinary(), nullable=False),
                      Column('content_type', Text(), nullable=False),
                      Column('size', BigInteger(), nullable=False),
                      ForeignKeyConstraint(['sessiondata_id'], ['sessiondata.id'], ondelete='CASCADE'),
                      # PrimaryKeyConstraint('sessiondata_id')
                      )
        self.schedule('alter', op.create_table, 'userinput',
                      Column('sessiondata_id', Integer(), primary_key=True, nullable=False),
                      Column('key', Text(), nullable=False),
                      Column('value', Text(), nullable=False),
                      ForeignKeyConstraint(['sessiondata_id'], ['sessiondata.id'], ondelete='CASCADE'),
                      # PrimaryKeyConstraint('sessiondata_id')
                      )

        self.schedule('data', op.execute, 'update persistedfile set mime_type=content_type')

