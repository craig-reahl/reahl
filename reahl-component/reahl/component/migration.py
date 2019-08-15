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

"""Support for database schema migration."""

from __future__ import print_function, unicode_literals, absolute_import, division
from pkg_resources import parse_version
import logging
import warnings
import inspect
import traceback

from collections import OrderedDict
from reahl.component.exceptions import ProgrammerError


class MigrationSeries(object):
    def __init__(self, orm_control, eggs_in_order, migration_runs, update_all_versions=False):
        self.eggs_in_order = eggs_in_order
        self.orm_control = orm_control
        self.migration_runs = migration_runs
        self.update_all_versions = update_all_versions

    @classmethod
    def from_eggs(cls, orm_control, eggs_in_order, max_migration_version=None):
        migration_runs = cls.collect_migration_runs_in_order(orm_control, eggs_in_order,
                                                             parse_version(max_migration_version) if max_migration_version else None)
        return MigrationSeries(orm_control, eggs_in_order, migration_runs, update_all_versions=max_migration_version is None)

    @classmethod
    def collect_migration_runs_in_order(cls, orm_control, eggs_in_order, max_migration_version):
        migrations_per_version = OrderedDict()
        previous_migration_version = '0.0'
        for migration_version in sorted(cls.collect_versions_of_migrations(eggs_in_order, max_migration_version), key=lambda v: parse_version(v)):
            for egg in eggs_in_order:
                current_schema_version = orm_control.schema_version_for(egg, default='0.0')
                #if len(migrations_per_version.keys())>0 and parse_version(list(migrations_per_version.keys())[-1]) > parse_version(current_schema_version):
                #    current_schema_version = list(migrations_per_version.keys())[-1]
                if parse_version(previous_migration_version) > parse_version(current_schema_version):
                    current_schema_version = previous_migration_version
                migrations_for_egg = egg.compute_migrations(current_schema_version, migration_version)
                migrations_in_error = [i for i in migrations_for_egg if i.version != migration_version]
                assert not migrations_in_error, 'Current version %s, unwanted migrations %s' % (migration_version, [(i, i.version) for i in migrations_in_error])

                if not migrations_for_egg:
                    class NopMigration(Migration):
                        _is_nop = True
                        version = migration_version
                        def schedule_upgrades(self): pass

                    migrations_for_egg = [NopMigration]

                migrations_per_version.setdefault(migration_version, []).append((egg, migrations_for_egg))
            previous_migration_version = migration_version

        return [MigrationRun(version_key, orm_control, migrations_for_version)
                for version_key, migrations_for_version in migrations_per_version.items()]

    @classmethod
    def collect_versions_of_migrations(self, eggs_in_order, max_migration_version):
        versions_of_migrations = set([])  
        for migration_list in [egg.migrations_in_order for egg in eggs_in_order]:
            for migration in migration_list:
                if not max_migration_version or (parse_version(migration.version) <= max_migration_version):
                    versions_of_migrations.add(migration.version)
        return versions_of_migrations

    def run(self):
        for migration_run in self.migration_runs:
            logging.getLogger(__name__).info('Migration run for version: %s' % migration_run.version)
            migration_run.schedule_migrations()
            migration_run.execute_migrations()

        if not self.migration_runs or self.is_all_migrations_are_nops():
            logging.getLogger(__name__).info('No migrations to run')

        if self.update_all_versions:
            self.update_schema_versions_to_latest_installed_eggs()

    def update_schema_versions_to_latest_installed_eggs(self):
        for egg in self.eggs_in_order:
            logging.getLogger(__name__).info('Migrating %s - updating schema version to latest %s' % (egg.name, egg.version))
            self.orm_control.update_schema_version_for(egg)

    def is_all_migrations_are_nops(self):
        migrations = []
        for migration_run in self.migration_runs:
            for egg, migration_classes in migration_run.eggs_in_order_migrations:
                for migration_class in migration_classes:
                    migrations.append(migration_class)
        return all([migration_class._is_nop for migration_class in migrations])


class MigrationRun(object):
    def __init__(self, version, orm_control, eggs_in_order_migrations):
        self.version = version
        self.orm_control = orm_control
        self.changes = MigrationSchedule('drop_fk', 'drop_pk', 'pre_alter', 'alter', 
                                         'create_pk', 'indexes', 'data', 'create_fk', 'cleanup')
        self.eggs_in_order_migrations = eggs_in_order_migrations

    def schedule_migrations(self):
        migrations_per_egg = []
        for egg, migration_classes in self.eggs_in_order_migrations:
            migrations_per_egg.append((egg, [migration_class(self.changes) for migration_class in migration_classes]))
        self.schedule_migration_changes(reversed(migrations_per_egg), 'upgrade')
        self.schedule_migration_changes(migrations_per_egg, 'upgrade_cleanup')
        self.schedule_migration_changes(migrations_per_egg, 'schedule_upgrades')

    def schedule_migration_changes(self, migrations_per_egg, method_name):
        for (egg, migration_list) in migrations_per_egg:
            message = 'Scheduling %s %s migrations for %s - version %s ' % \
                      (len(migration_list), method_name, egg.name, self.version)

            logging.getLogger(__name__).info(message)
            for migration in migration_list:
                if hasattr(migration, method_name):
                    logging.getLogger(__name__).info('Scheduling %s for %s' % (method_name, migration))
                    getattr(migration, method_name)()

    def execute_migrations(self):
        self.changes.execute_all()
        self.update_schema_versions()

    def update_schema_versions(self):
        for (egg, migrations) in self.eggs_in_order_migrations:
            current_schema_version = self.orm_control.schema_version_for(egg, default='0.0')
            if parse_version(self.version) > parse_version(current_schema_version):
                logging.getLogger(__name__).info('Migrating %s - updating schema version to %s' % (egg.name, self.version))
                self.orm_control.update_schema_version_for(egg, version=self.version)


class MigrationSchedule(object):
    def __init__(self, *phases):
        self.phases_in_order = phases
        self.phases = dict([(i, []) for i in phases])

    def schedule(self, phase, scheduling_context, to_call, *args, **kwargs):
        try:
            self.phases[phase].append((to_call, scheduling_context, args, kwargs))
        except KeyError as e:
            raise ProgrammerError('A phase with name<%s> does not exist.' % phase)

    def execute(self, phase):
        logging.getLogger(__name__).info('Executing schema change phase %s' % phase)
        for to_call, scheduling_context, args, kwargs in self.phases[phase]:
            logging.getLogger(__name__).debug(' change: %s(%s, %s)' % (to_call.__name__, args, kwargs))
            try:
                to_call(*args, **kwargs)
            except Exception as e:
                class ExceptionDuringMigration(Exception):
                    def __init__(self, scheduling_context):
                        super(ExceptionDuringMigration, self).__init__()
                        self.scheduling_context = scheduling_context
                    def __str__(self):
                        message = super(ExceptionDuringMigration, self).__str__()
                        formatted_context = traceback.format_list([(frame_info.filename, frame_info.lineno, frame_info.function, frame_info.code_context[frame_info.index]) 
                                                                   for frame_info in self.scheduling_context])
                        return '%s\n\n%s\n\n%s' % (message, 'The above Exception happened for the migration that was scheduled here:', ''.join(formatted_context))
                raise ExceptionDuringMigration(scheduling_context)

    def execute_all(self):
        for phase in self.phases_in_order:
            self.execute(phase)


class Migration(object):
    """Represents one logical change that can be made to an existing database schema.
    
       You should extend this class to build your own domain-specific database schema migrations. Set the
       `version` class attribute to a string containing the version of your component for which this Migration
       should be run when upgrading from a previous version.
       
       Never use code imported from your component in a Migration, since Migration code is kept around in
       future versions of a component and may be run to migrate a schema with different versions of the code in your component.
    """
    _is_nop = False
    version = None

    @classmethod
    def is_applicable(cls, current_schema_version, new_version):
        if not cls.version:
            raise ProgrammerError('Migration %s does not have a version set' % cls)
        return parse_version(cls.version) > parse_version(current_schema_version) and \
               parse_version(cls.version) <= parse_version(new_version)

    def __init__(self, changes):
        self.changes = changes

    def schedule(self, phase, to_call, *args, **kwargs):
        """Call this method to schedule a method call for execution later during the specified migration phase.

           Scheduled migrations are first collected from all components, then the calls scheduled for each defined
           phase are executed. Calls in one phase are executed in the order they were scheduled. Phases are executed
           in the following order:

           'drop_fk', 'drop_pk', 'pre_alter', 'alter', 'create_pk', 'indexes', 'data', 'create_fk', 'cleanup'

           :param phase: The name of the phase to schedule this call.
           :param to_call: The method or function to call.
           :param args: The positional arguments to be passed in the call.
           :param kwargs: The keyword arguments to be passed in the call.
        """
        def get_scheduling_context():
            relevant_frames = []
            found_framework_code = False
            frames = iter(inspect.stack()[2:]) #remove this function from the stack
            while not found_framework_code:
                frame = next(frames)
                found_framework_code = frame.filename.endswith(__file__)
                if not found_framework_code:
                    relevant_frames.append(frame)

            return reversed(relevant_frames)
        self.changes.schedule(phase, get_scheduling_context(), to_call, *args, **kwargs)

    def schedule_upgrades(self):
        """Override this method in a subclass in order to supply custom logic for changing the database schema. This
           method will be called for each of the applicable Migrations listed for all components, in order of 
           dependency of components (the component deepest down in the dependency tree, first).

           **Added in 2.1.2**: Supply custom upgrade logic by calling `self.schedule()`.
        """
        warnings.warn('Ignoring %s.schedule_upgrades(): it does not override schedule_upgrades() (method name typo perhaps?)' % self.__class__.__name__ , 
                      UserWarning, stacklevel=-1)

    @property
    def name(self):
        return '%s.%s' % (inspect.getmodule(self).__name__, self.__class__.__name__)

    def __str__(self):
        return '%s %s' % (self.name, self.version)
