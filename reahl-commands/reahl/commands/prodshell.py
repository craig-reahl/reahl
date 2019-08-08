# Copyright 2013-2018 Reahl Software Services (Pty) Ltd. All rights reserved.
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

"""The Reahl production commandline utility."""

from __future__ import print_function, unicode_literals, absolute_import, division

import os.path
import os
import shutil

import six
import inspect

from pkg_resources import DistributionNotFound, get_distribution

from reahl.component.dbutils import SystemControl
from reahl.component.shelltools import Command, ReahlCommandline, AliasFile
from reahl.component.context import ExecutionContext
from reahl.component.config import EntryPointClassList, Configuration, ConfigSetting, StoredConfiguration, MissingValue
from reahl.component.eggs import ReahlEgg
from reahl.component.exceptions import DomainException



class ComponentInfo(Command):
    """Gives information about a given reahl component"""
    keyword = 'componentinfo'
    def assemble(self):
        self.parser.add_argument('component_name', type=str,  help='the name of a component')

    def execute(self, args):
        egg = ReahlEgg(get_distribution(args.component_name))
        print('Name: %s' % egg.name)
        print('Version: %s' % egg.version)
        configuration_class = egg.configuration_spec
        if configuration_class:
            self.print_configuration_info(configuration_class)
        if egg.translation_package:
            self.print_locale_info(egg)

    def print_locale_info(self, egg):
        print('\nLocale info:\n')
        print('\tTranslation package: %s' % egg.translation_package.__name__)
        print('\tTranslation POT: %s' % egg.translation_pot_filename)

    def print_configuration_info(self, configuration_class):
        print('\nConfiguration (%s):\n' % configuration_class.filename)
        if configuration_class.__doc__:
            for line in inspect.getdoc(configuration_class).split('\n'):
                print('\t%s' % line)
            print('')
        for name, value in configuration_class.__dict__.items():
            if isinstance(value, ConfigSetting):
                print('\t%s.%s:\t\t\t%s' % (configuration_class.config_key, name, value.description))


class ProductionCommand(Command):
    """Superclass used for all production shell commands."""
    def assemble(self):
        self.parser.add_argument('config_directory', type=str,  help='a reahl configuration directory')

    def execute(self, args):
        self.create_context(args.config_directory)
        self.directory = args.config_directory

    def create_context(self, config_directory):
        try:
            self.context = ExecutionContext.for_config_directory(config_directory)
        except DistributionNotFound as ex:
            ex.args = ('%s (In development? Did you forget to do a "reahl setup -- develop -N"?)' % ex.args[0],)
            raise
        self.context.install()
        self.context.system_control = SystemControl(self.context.config)

    @property
    def sys_control(self):
        return self.context.system_control
    
    @property
    def config(self):
        return self.context.config


class ListConfig(ProductionCommand):
    """Lists current configuration settings."""
    keyword = 'listconfig'

    def assemble(self):
        super(ListConfig, self).assemble()
        self.parser.add_argument('-v', '--values', action='store_true', dest='print_values', help='prints the currently configured value')
        self.parser.add_argument('-f', '--files', action='store_true', dest='print_files', help='prints the filename where the setting should be defined')
        self.parser.add_argument('-d', '--defaults', action='store_true', dest='print_defaults', help='prints the default value')
        self.parser.add_argument('-m', '--missing', action='store_true', dest='print_missing_only', help='prints the missing values only')
        self.parser.add_argument('-i', '--info', action='store_true', dest='print_description', help='prints a description')

    def create_context(self, config_directory):
        self.context = ExecutionContext(name=self.__class__.__name__)

    def execute(self, args):
        super(ListConfig, self).execute(args)
        self.context.install()

        print('Listing config for %s' % self.directory)
        config = StoredConfiguration(self.directory)
        config.configure(validate=False)
        for config_file, key, value, setting in config.list_all():
            to_print = '%-35s' % key
            if args.print_files:
                to_print += '\t%s' % config_file
            if args.print_values:
                to_print += '\t%s' % value
            if args.print_defaults:
                if setting.defaulted:
                    message = six.text_type(setting.default)
                    if setting.dangerous:
                        message += ' (DANGEROUS DEFAULT)'
                elif setting.automatic:
                    message = 'AUTOMATIC'
                else:
                    message = 'NO DEFAULT'
                to_print += '\t%s' % message
            if args.print_description:
                to_print += '\t%s' % setting.description

            if args.print_missing_only and not isinstance(value, MissingValue):
                pass
            else:
                print(to_print)


class CheckConfig(ProductionCommand):
    """Checks current configuration settings."""
    keyword = 'checkconfig'
    def execute(self, args):
        super(CheckConfig, self).execute(args)
        print('Checking config in %s' % self.directory)
        config = StoredConfiguration(self.directory)
        config.configure(validate=True)
        print('Config parses OK')


class CreateDBUser(ProductionCommand):
    """Creates the database user."""
    keyword = 'createdbuser'
    def assemble(self):
        super(CreateDBUser, self).assemble()
        self.parser.add_argument('-n', '--no-create-password', action='store_true', dest='no_create_password',
                                 help='create the user without a password')
        self.parser.add_argument('-U', '--super-user-name', dest='super_user_name', default=None,
                                 help='the name of the priviledged user who may perform this operation')
    def execute(self, args):
        super(CreateDBUser, self).execute(args)
        return self.sys_control.create_db_user(super_user_name=args.super_user_name,
                                               create_with_password=not args.no_create_password)


class DropDBUser(ProductionCommand):
    """Drops the database user."""
    keyword = 'dropdbuser'
    def assemble(self):
        super(DropDBUser, self).assemble()
        self.parser.add_argument('-U', '--super-user-name', dest='super_user_name', default=None,
                                 help='the name of the priviledged user who may perform this operation')

    def execute(self, args):
        super(DropDBUser, self).execute(args)
        return self.sys_control.drop_db_user(super_user_name=args.super_user_name)


class DropDB(ProductionCommand):
    """Drops the database."""
    keyword = 'dropdb'
    def assemble(self):
        super(DropDB, self).assemble()
        self.parser.add_argument('-y', '--yes', action='store_true', dest='yes',
                                 help='automatically answers yes on prompts')
        self.parser.add_argument('-U', '--super-user-name', dest='super_user_name', default=None,
                                 help='the name of the priviledged user who may perform this operation')

    def execute(self, args):
        super(DropDB, self).execute(args)
        return self.sys_control.drop_database(super_user_name=args.super_user_name, yes=args.yes)


class CreateDB(ProductionCommand):
    """Creates the database."""
    keyword = 'createdb'
    def assemble(self):
        super(CreateDB, self).assemble()
        self.parser.add_argument('-U', '--super-user-name', dest='super_user_name', default=None,
                                 help='the name of the priviledged user who may perform this operation')

    def execute(self, args):
        super(CreateDB, self).execute(args)
        return self.sys_control.create_database(super_user_name=args.super_user_name)


class BackupDB(ProductionCommand):
    """Backs up the database."""
    keyword = 'backupdb'
    def assemble(self):
        super(BackupDB, self).assemble()
        self.parser.add_argument('-d', '--directory', dest='directory', default='/tmp', help='the directory to back up to')
        self.parser.add_argument('-U', '--super-user-name', dest='super_user_name', default=None,
                                 help='the name of the priviledged user who may perform this operation')
    def execute(self, args):
        super(BackupDB, self).execute(args)
        return self.sys_control.backup_database(args.directory, super_user_name=args.super_user_name)


class RestoreDB(ProductionCommand):
    """Restores the database."""
    keyword = 'restoredb'

    def assemble(self):
        super(RestoreDB, self).assemble()
        self.parser.add_argument('-f', '--filename', dest='filename', default='/tmp/data.pgsql', help='the file to restore from')
        self.parser.add_argument('-U', '--super-user-name', dest='super_user_name', default=None,
                                 help='the name of the priviledged user who may perform this operation')

    def execute(self, args):
        super(RestoreDB, self).execute(args)
        return self.sys_control.restore_database(args.filename, super_user_name=args.super_user_name)


class BackupAllDB(ProductionCommand):
    """Backs up all the databases on the host this project config points to."""
    keyword = 'backupall'
    def assemble(self):
        super(BackupAllDB, self).assemble()
        self.parser.add_argument('-d', '--directory', dest='directory', default='/tmp', help='the direcotry to back up to')
        self.parser.add_argument('-U', '--super-user-name', dest='super_user_name', default=None,
                                 help='the name of the priviledged user who may perform this operation')
        
    def execute(self, args):
        super(BackupAllDB, self).execute(args)
        return self.sys_control.backup_all_databases(args.directory, super_user_name=args.super_user_name)


class RestoreAllDB(ProductionCommand):
    """Restores all the databases on the host this project config points to."""
    keyword = 'restoreall'
    def assemble(self):
        super(RestoreAllDB, self).assemble()
        self.parser.add_argument('-f', '--filename', dest='filename', default='/tmp/data.sql', help='the file to restore from')
        self.parser.add_argument('-U', '--super-user-name', dest='super_user_name', default=None,
                                 help='the name of the priviledged user who may perform this operation')
        
    def execute(self, args):
        super(RestoreAllDB, self).execute(args)
        return self.sys_control.restore_all_databases(args.filename, super_user_name=args.super_user_name)


class SizeDB(ProductionCommand):
    """Prints the current size of the database."""
    keyword = 'sizedb'
    def execute(self, args):
        super(SizeDB, self).execute(args)
        self.context.install()
        with self.sys_control.auto_connected():
            print('Database size: %s' % self.sys_control.size_database())
        return 0


class CreateDBTables(ProductionCommand):
    """Creates all necessary tables in the database."""
    keyword = 'createdbtables'
    def execute(self, args):
        super(CreateDBTables, self).execute(args)
        self.context.install()
        with self.sys_control.auto_connected():
            return self.sys_control.create_db_tables()


class DropDBTables(ProductionCommand):
    """Drops all necessary tables in the database."""
    keyword = 'dropdbtables'
    def execute(self, args):
        super(DropDBTables, self).execute(args)
        self.context.install()
        with self.sys_control.auto_connected():
            return self.sys_control.drop_db_tables()


class MigrateDB(ProductionCommand):
    """Runs all necessary database migrations."""
    keyword = 'migratedb'
    def assemble(self):
        super(MigrateDB, self).assemble()
        self.parser.add_argument('-d', '--dryrun', action='store_true', dest='dry_run',
                                 help='apply the migration, but do not commit(rollback changes)')
        self.parser.add_argument('-s', '--output-sql', action='store_true', dest='output_sql',
                                 help='don\'t migrate, only output the sql that would be executed when migrating')
        self.parser.add_argument('-m', '--maxmigrationversion', action='store', dest='max_migration_version',
                                 help='run migrations up to(inclusive) this version')

    def execute(self, args):
        super(MigrateDB, self).execute(args)
        self.context.install()
        with self.sys_control.auto_connected():
            return self.sys_control.migrate_db(dry_run=args.dry_run, output_sql=args.output_sql,
                                               max_migration_version=args.max_migration_version)


class DiffDB(ProductionCommand):
    """Prints out a diff(required alembic operations) between the current database schema and what is expected by the current code."""
    keyword = 'diffdb'
    def assemble(self):
        super(DiffDB, self).assemble()
        self.parser.add_argument('-s', '--output_sql', action='store_true', dest='output_sql',
                                 help='show differences as sql')

    def execute(self, args):
        super(DiffDB, self).execute(args)
        self.context.install()
        with self.sys_control.auto_connected():
            self.sys_control.diff_db(output_sql=args.output_sql)


class ListDependencies(ProductionCommand):
    """List all dependency eggs in dependency order."""
    keyword = 'listdeps'
    def assemble(self):
        super(ListDependencies, self).assemble()
        self.parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help='list direct dependencies too')
        
    def execute(self, args):
        super(ListDependencies, self).execute(args)
        self.context.install()
        distributions = ReahlEgg.compute_ordered_dependent_distributions(self.config.reahlsystem.root_egg)
        for distribution in distributions:
            deps = ''
            if args.verbose:
                deps = '[%s]' % (' | '.join([six.text_type(i) for i in distribution.requires()]))
            print('%s %s' % (distribution, deps))
        return 0


class RunJobs(ProductionCommand):
    """Runs all registered scripts."""
    keyword = 'runjobs'
    def execute(self, args):
        super(RunJobs, self).execute(args)
        self.context.install()
        with self.sys_control.auto_connected():
            self.sys_control.do_daily_maintenance()
        return 0


class ExportStaticFiles(ProductionCommand):
    """Exports all static web assets found in web.libraries to a specified directory."""
    keyword = 'exportstatics'
    def assemble(self):
        super(ExportStaticFiles, self).assemble()
        self.parser.add_argument('destination_directory', type=str,  help='the destination directory to export to')

    def execute(self, args):
        super(ExportStaticFiles, self).execute(args)
        if os.path.exists(args.destination_directory):
            raise DomainException(message='The path %s already exists. Please move it out of the way first.' % args.destination_directory)
        try:
            os.mkdir(args.destination_directory)
        except Exception as ex:
            raise DomainException(message='Could not create %s: %s' % (args.destination_directory, six.text_type(ex)))
            
        for packaged_file in self.config.web.frontend_libraries.packaged_files():
            print('extracting %s' % packaged_file.full_path)
            shutil.copy(packaged_file.full_path, args.destination_directory)


