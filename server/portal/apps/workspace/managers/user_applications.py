"""
..: module:: apps.workspace.managers.user_applications
   : synopsis: Manager handling user's cloned applications and systems
"""
import logging

from requests.exceptions import HTTPError

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from portal.libs.agave.models.systems.execution import ExecutionSystem
from portal.libs.agave.models.applications import Application
from portal.apps.workspace.managers.base import AbstractApplicationsManager
from portal.utils import encryption as EncryptionUtil
from portal.apps.accounts.managers.accounts import _lookup_user_home_manager
from portal.apps.accounts.models import SSHKeys
from portal.apps.accounts.managers.user_work_home import UserWORKHomeManager

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)
# pylint: enable=invalid-name


class UserApplicationsManager(AbstractApplicationsManager):
    """User Applications Manager

    Class that provides workflows to clone apps and execution systems for a user.

    """

    def __init__(self, *args, **kwargs):
        super(UserApplicationsManager, self).__init__(*args, **kwargs)
        self.home_mgr = _lookup_user_home_manager(self.user)

    def get_clone_system_id(self):
        """Gets system id to deploy cloned app materials to.

        *System Id* is a string, unique id for each system.
        This function returns the system id for a user's home system.

        :returns: System unique id
        :rtype: str
        """

        id = self.home_mgr.get_system_id()
        return id

    def get_application(self, appId):
        """Gets an application

        :param str appId: Unique id of the application

        :returns: Application instance
        :rtype: class Application
        """

        app = Application(self.client, id=appId)
        return app

    def check_app_for_updates(self, cloned_app, host_app_id=None, host_app=None):
        """Checks cloned app for updates against host app by comparing the revision
        of the host app to the 'cloneRevision' tag inserted into the cloned apps tags.

        :param cloned_app: Application instance of the cloned application
        :param host_app_id: Agave id of the host application
        :param host_app: Application instance of the host application

        :returns: update_required
        :rtype: bool
        """
        update_required = False

        # compare cloned app revision number to original app revision number
        if not host_app:
            host_app = self.get_application(host_app_id)

        logger.debug('Looking for revision match in tags for app def: {}'.format(cloned_app.to_dict()))
        # find revision number in tags
        tag_match = [s for s in cloned_app.tags if 'cloneRevision' in s]
        if not tag_match:
            logger.error('No cloneRevision in tags, app should be updated to ensure consistency.')
            update_required = True
        else:
            try:
                clone_rev = int(tag_match[0].split(':')[1])
                if clone_rev != host_app.revision:
                    logger.warning('Cloned app revision does not match host: {} != {}'.format(
                        clone_rev,
                        host_app.revision
                    ))
                    update_required = True
            except ValueError as exc:
                logger.exception('cloneRevision in tags cannot be converted to integer, app should be updated to ensure consistency. %s', exc)
                update_required = True

        return update_required

    def clone_application(self, allocation, cloned_app_name, host_app_id=None, host_app=None):
        """Clones an application given a host app, allocation, and target name.

        ..note: checks if cloned Execution System already exists for user,
        and creates it if not.

        :param str allocation: Project allocation
        :param str cloned_app_name: Name of application clone
        :param str host_app_id: Agave id of host app
        :param host_app: Application instance of host app

        :returns: Application instance
        :rtype: class Application
        """
        if not host_app:
            host_app = self.get_application(host_app_id)

        logger.debug('Starting process to clone new application for user with id: {}-{}.0'.format(
            cloned_app_name,
            host_app.revision))

        host_exec = ExecutionSystem(self.client, host_app.execution_system)

        host_exec_user_role = host_exec.roles.for_user(username=self.user.username)
        if host_exec_user_role and host_exec_user_role.role == 'OWNER':
            cloned_exec_sys = host_exec
            logger.debug('Using current execution system {}'.format(cloned_exec_sys.id))
        else:
            cloned_exec_id = '{username}.{allocation}.exec.{resource}.{execType}'.format(
                username=self.user.username,
                allocation=allocation,
                resource=host_exec.login.host.replace('.tacc.utexas.edu', ''),
                execType=host_exec.execution_type
            )
            logger.debug('Getting cloned execution system: {}'.format(cloned_exec_id))
            cloned_exec_sys = self.get_or_create_exec_system(cloned_exec_id, host_exec.id, allocation)

        cloned_depl_path = '.APPDATA/{appName}-{rev}.0'.format(
            username=self.user.username,
            appName=cloned_app_name,
            rev=host_app.revision
        )

        logger.debug('Cloning app id {}-{} with exec sys {} at path {} on deployment sys {}'.format(
            cloned_app_name,
            host_app.revision,
            cloned_exec_sys.id,
            cloned_depl_path,
            self.get_clone_system_id(),
        ))
        cloned_app = host_app.clone(self.client,
                                    depl_path=cloned_depl_path,
                                    exec_sys=cloned_exec_sys.id,
                                    depl_sys=self.get_clone_system_id(),
                                    name=cloned_app_name,
                                    ver='{}.0'.format(host_app.revision)
                                    )

        # add host revision number to cloned app's tags
        cloned_app.tags.append('cloneRevision:{}'.format(host_app.revision))
        cloned_app.update()

        # if system is new, pass system along with app object to instantiate push keys modal
        if hasattr(cloned_exec_sys, 'is_new'):
            cloned_app._new_exec_sys = cloned_exec_sys

        return cloned_app

    def get_or_create_cloned_app(self, host_app, allocation):
        """Gets or creates a cloned app for the user.

        Generates a cloned app id and tries to fetch that app.
        If the app exists, check for updates.

        If app does not exist, clone the host app to cloned app id.

        :param host_app: Application instance of host app
        :param str allocation: Project allocation for app to be run on

        :returns: Application instance
        :rtype: class Application
        """

        # cloned_app_name is of the form 'prtl.clone.sal.PT2050-DataX.compress-0.1u1'
        # NOTE: host revision # will be appended to cloned_app_id, e.g. prtl.clone.sal.PT2050-DataX.compress-0.1u1-2.0
        cloned_app_name = 'prtl.clone.{username}.{allocation}.{appId}'.format(
            username=self.user.username,
            allocation=allocation,
            appId=host_app.id
        )

        cloned_app_id = '{appId}-{rev}.0'.format(
            appId=cloned_app_name,
            rev=host_app.revision)
        try:
            cloned_app = self.get_application(cloned_app_id)

            logger.debug('Cloned app {} found! Checking for updates...'.format(cloned_app_id))

            if not host_app.is_public:
                update_required = self.check_app_for_updates(cloned_app, host_app=host_app)
                if update_required:
                    # Need to update cloned app by deleting and re-cloning
                    logger.warning('Cloned app is being updated (i.e. deleted and re-cloned)')
                    cloned_app.delete()
                    cloned_app = self.clone_application(allocation, cloned_app_name, host_app=host_app)
                else:
                    logger.debug('Cloned app is current with host!')

            # cloned_app._new_exec_sys = ExecutionSystem(self.client, id=cloned_app.execution_system)
            return cloned_app

        except HTTPError as exc:
            if exc.response.status_code == 404:
                logger.debug('No app found with id {}. Cloning app...'.format(cloned_app_id))
                cloned_app = self.clone_application(allocation, cloned_app_name, host_app=host_app)
                return cloned_app

    def get_or_create_app(self, appId, allocation):
        """Gets or creates application for user.

        If application selected is owned by user, return the app,
        else clone the app to the same exec system with the
        specified allocation.

        ..note: Entry point.

        :param str appId: Agave id of application selected to run
        :param str allocation: Project alloction for app to run on

        :returns: Application instance
        :rtype: class Application
        """

        app = self.get_application(appId)

        # if app is owned by user, no need to clone
        if app.owner == self.user.username:
            logger.debug('User is app owner, no need to clone. Returning original app.')
            return app

        else:
            return self.get_or_create_cloned_app(app, allocation)

    def clone_execution_system(self, host_system_id, new_system_id, alloc):
        """Clone execution system for user.

        :param str host_system_id: Agave id of host execution system
        :param str new_system_id: id for system clone
        :param str alloc: Project allocation for system's custom directives

        :returns: ExecutionSystem instance
        :rtype: ExecutionSystem
        """

        clone_body = {
            'action': 'CLONE',
            'id': new_system_id
        }

        cloned_sys = self.client.systems.manage(body=clone_body, systemId=host_system_id)

        sys = self.validate_exec_system(cloned_sys['id'], alloc)

        return sys

    def set_system_definition(
            self,
            system_id,
            allocation
    ):  # pylint:disable=arguments-differ
        """Initializes Agave execution system

        :param class system: ExecutionSystem instance
        :param str allocation: Project allocation for customDirectives

        :returns: ExecutionSystem instance
        :rtype: class ExecutionSystem
        """
        username = self.user.username

        system = self.get_exec_system(system_id)

        if not system.available:
            system.enable()

        system.site = 'portal.dev'
        system.description = 'Exec system for user: {username}'.format(
            username=username
        )

        user_work_home_mgr = UserWORKHomeManager(self.user)

        system.storage.host = system.login.host
        system.storage.home_dir = user_work_home_mgr.get_home_dir_abs_path()
        system.storage.port = system.login.port
        system.storage.root_dir = '/'
        system.storage.protocol = 'SFTP'
        system.storage.auth.username = self.user.username
        system.storage.auth.type = system.AUTH_TYPES.SSHKEYS

        system.login.protocol = 'SSH'
        system.login.auth.username = self.user.username
        system.login.auth.type = system.AUTH_TYPES.SSHKEYS

        scratch_hosts = ['data', 'stampede2', 'lonestar5']
        if system.storage.host in [s + '.tacc.utexas.edu' for s in scratch_hosts]:
            system.scratch_dir = system.storage.home_dir.replace(settings.PORTAL_DATA_DEPOT_WORK_HOME_DIR_FS, '/scratch')
        else:
            system.scratch_dir = system.storage.home_dir
        system.work_dir = system.storage.home_dir

        if system.scheduler == 'SLURM':
            for queue in system.queues.all():
                if queue.custom_directives:
                    queue.custom_directives = '-A {}'.format(allocation)
        return system

    def validate_exec_system(self, system_id, alloc, *args, **kwargs):
        """Validate execution system and generate keys for it

        :param system_id: Agave system id
        :param alloc: Project allocation for system

        :returns: ExecutionSystsem instance
        :rtype: class ExecutionSystem
        """

        system = self.set_system_definition(
            system_id,
            alloc
        )

        # NOTE: Check if host keys already exist for user for both login and storage hosts
        for host_type in [system.login, system.storage]:
            try:
                keys = self.user.ssh_keys.for_hostname(hostname=host_type.host)
                priv_key_str = keys.private_key()
                publ_key_str = keys.public
            except ObjectDoesNotExist:
                private_key = EncryptionUtil.create_private_key()
                priv_key_str = EncryptionUtil.export_key(private_key, 'PEM')
                public_key = EncryptionUtil.create_public_key(private_key)
                publ_key_str = EncryptionUtil.export_key(public_key, 'OpenSSH')

                SSHKeys.objects.update_hostname_keys(
                    self.user,
                    hostname=host_type.host,
                    priv_key=priv_key_str,
                    pub_key=publ_key_str
                )

                system.is_new = True

            host_type.auth.public_key = publ_key_str
            host_type.auth.private_key = priv_key_str

        system.update()

        return system

    def get_exec_system(self, systemId, *args, **kwargs):
        """Gets an execution system

        :param systemId: Agave Execution system id

        :returns: ExecutionSystem instance
        :rtype: class ExecutionSystem
        """

        exec_sys = ExecutionSystem(self.client, systemId, ignore_error=None)
        return exec_sys

    def get_or_create_exec_system(self, clonedSystemId, hostSystemId, alloc, *args, **kwargs):
        """Gets or creates user's execution system

        :param str clonedSystemId: Agave id of new system to be created
        :param str hostSystemId: Agave id of host system to clone from
        :param str alloc: Project allocation for system

        :returns: Agave response for the system
        """
        try:
            exec_sys = self.get_exec_system(clonedSystemId)
            if not exec_sys.available:
                exec_sys = self.validate_exec_system(exec_sys.id, alloc)
            logger.debug('Execution system found!')
            return exec_sys
        except HTTPError as exc:
            if exc.response.status_code == 404:
                logger.debug('No execution system found, cloning system')
                exec_sys = self.clone_execution_system(hostSystemId, clonedSystemId, alloc)
                return exec_sys
