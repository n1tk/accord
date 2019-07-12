
from .fixtures import model_returns
from unittest import TestCase


from accord import exceptions
from accord import models


import subprocess
import mock
import os


class TestModels(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        if os.path.isfile('restore'):
            os.remove('restore')

        if os.path.exists('anaconda_backup'):
            os.rmdir('anaconda_backup')

    def setup_args_backup_default(self, repos_only=False, sync=False,
                                  sync_node=None, sync_user='root',
                                  start_deployments=False,
                                  directory='/opt/anaconda_backup'):
        class MockArgs(object):
            def __init__(self):
                self.action = 'backup'
                self.directory = directory
                self.no_config = False
                self.override = False
                self.repos_only = repos_only
                self.start_deployments = start_deployments
                self.sync = sync
                self.sync_node = sync_node
                self.sync_user = sync_user

        return MockArgs()

    def setup_args_restore_default(self, override=False, repos_only=False,
                                   no_config=False, start_deployments=False,
                                   directory='/opt/anaconda_backup'):
        class MockArgs(object):
            def __init__(self):
                self.action = 'restore'
                self.directory = directory
                self.no_config = no_config
                self.override = override
                self.repos_only = repos_only
                self.start_deployments = start_deployments

        return MockArgs()

    def setup_temp_restore_file(self, temp_path):
        open(temp_path, 'a').close()

    def test_init_class_backup_default(self):
        expected_secrets = {
            'kube-system': ['cluster-tls'],
            'default': ['anaconda-enterprise-certs', 'anaconda-config-files']
        }
        expected_cms = {
            'default': ['anaconda-enterprise-anaconda-platform.yml']
        }

        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                test = models.Accord(self.setup_args_backup_default())

        self.assertEqual(test.backup_directory, '/opt/anaconda_backup')
        self.assertEqual(test.action, 'backup')
        self.assertEqual(
            test.var_lib_gravity_backup_name,
            'var_lib_gravity_backup.tar.gz'
        )
        self.assertEqual(test.postgres_backup_name, 'full_postgres_backup.sql')
        self.assertEqual(test.storage_backup_name, 'storage_backup.tar.gz')
        self.assertEqual(test.repository_db_name, 'all_repositories.tar')
        self.assertEqual(
            test.postgres_container_backup,
            '/var/lib/postgresql/data'
        )
        self.assertEqual(
            test.postgres_system_backup,
            '/opt/anaconda/storage/pgdata'
        )
        self.assertEqual(
            test.postgres_system_backup_path,
            '/opt/anaconda/storage/pgdata/full_postgres_backup.sql'
        )
        self.assertEqual(
            test.postgres_container_backup_path,
            '/var/lib/postgresql/data/full_postgres_backup.sql'
        )
        self.assertEqual(
            test.repository,
            '/opt/anaconda/storage/object/anaconda-repository'
        )
        self.assertEqual(test.signal_file, '/opt/anaconda_backup/restore')
        self.assertEqual(test.sync_files, False)
        self.assertEqual(test.start_deployments, False)
        self.assertEqual(test.no_config, False)
        self.assertEqual(test.repos_only, False)
        self.assertEqual(test.namespace, 'default')
        self.assertEqual(test.secret_files, expected_secrets)
        self.assertEqual(test.config_maps, expected_cms)

    def test_init_class_restore_defaults(self):
        with mock.patch('accord.models.Accord.check_for_restore'):
            test = models.Accord(self.setup_args_restore_default())

        self.assertEqual(test.action, 'restore')

    def test_init_class_restore_exception_file(self):
        with mock.patch('accord.models.Accord.check_for_restore') as restore:
            restore.return_value = False
            try:
                models.Accord(self.setup_args_restore_default())
            except exceptions.RestoreSignal:
                pass
            except Exception:
                assert False, 'Did not catch the proper exception'

    def test_init_class_restore_force(self):
        test = models.Accord(
            self.setup_args_restore_default(override=True)
        )

        self.assertEqual(test.override, True)
        self.assertEqual(test.action, 'restore')

    def test_init_class_backup_sync_user(self):
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                with mock.patch('accord.models.Accord.test_sync_to_backup'):
                    test = models.Accord(
                        self.setup_args_backup_default(
                            sync=True,
                            sync_user='billdo',
                            sync_node='1.2.3.4'
                        )
                    )

        self.assertEqual(test.sync_files, True)
        self.assertEqual(test.sync_user, 'billdo')
        self.assertEqual(test.sync_node, '1.2.3.4')

    def test_init_class_backup_sync_no_node(self):
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                try:
                    models.Accord(
                        self.setup_args_backup_default(
                            sync=True,
                            sync_user='billdo'
                        )
                    )
                except exceptions.MissingSyncNode:
                    pass
                except Exception:
                    assert False, 'Did not catch expected exception'

    def test_init_class_restore_file_check(self):
        self.setup_temp_restore_file('restore')
        test_args = self.setup_args_restore_default(override=True)
        test_class = models.Accord(test_args)

        # Change path of file
        test_class.signal_file = 'restore'
        check_return = test_class.check_for_restore()

        self.assertEqual(check_return, True)

    def test_add_restore_file(self):
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                test_class = models.Accord(self.setup_args_backup_default())

        test_class.signal_file = 'restore'
        test_class.add_signal_for_restore()

        if os.path.isfile('restore'):
            pass
        else:
            assert False, 'Did not find restore file'

    def test_cleanup_restore_file(self):
        self.setup_temp_restore_file('restore')
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                test_class = models.Accord(self.setup_args_backup_default())

        test_class.signal_file = 'restore'
        test_class.remove_signal_restore_file()

        if os.path.isfile('restore'):
            assert False, 'restore file was not cleaned up'

    def test_check_for_ssh_sudo_access_exception(self):
        raise_exception = mock.Mock()
        raise_exception.side_effect = subprocess.CalledProcessError
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                with mock.patch(
                    'accord.models.Accord.run_su_command',
                    side_effect=raise_exception
                ):
                    try:
                        models.Accord(
                            self.setup_args_backup_default(
                                sync=True,
                                sync_user='Billdo',
                                sync_node='1.2.3.4'
                            )
                        )
                        assert False, 'Exception was not raised'
                    except exceptions.UnableToSync:
                        pass
                    except Exception:
                        assert False, 'Did not catch proper exception'

    def test_setup_backup_directory(self):
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                test_class = models.Accord(self.setup_args_backup_default())

        test_class.backup_directory = 'anaconda_backup'
        test_class.setup_backup_directory()

        if not os.path.exists('anaconda_backup'):
            assert False, 'Backup directory was not created'

    def test_setup_backup_directory_restore(self):
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                with mock.patch('accord.models.Accord.run_su_command'):
                    test_class = models.Accord(
                        self.setup_args_backup_default(
                            sync=True,
                            sync_user='Billdo',
                            sync_node='1.2.3.4'
                        )
                    )

        test_class.backup_directory = 'anaconda_backup'
        with mock.patch('accord.models.Accord.run_su_command'):
            test_class.setup_backup_directory()

        if not os.path.exists('anaconda_backup'):
            assert False, 'Backup directory was not created'

    @mock.patch('sh.Command')
    def test_grabbing_postgres_docker_container(self, Command):
        mock_response = mock.Mock()
        mock_response.side_effect = [
            model_returns.GET_PODS,
            model_returns.DESCRIBE_POD
        ]
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                test_class = models.Accord(self.setup_args_backup_default())

        Command().side_effect = mock_response
        test_class.get_postgres_docker_container()

        self.assertEqual(
            test_class.postgres_pod,
            'anaconda-enterprise-postgres-58857557d-ctbfs',
            'Did not get expected return value'
        )
        self.assertEqual(
            test_class.docker_cont_id,
            'fd234fad0a538a302ac68d0f260a155950b4b8c7afca3176fcb25d1d799b045e',
            'Did not get expected return value'
        )

    @mock.patch('sh.Command')
    def test_gravity_backup(self, Command):
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                test_class = models.Accord(self.setup_args_backup_default())

        try:
            test_class.gravity_backup_restore('backup')
        except Exception:
            assert False, "Exception occurred"

    @mock.patch('sh.Command')
    def test_gravity_restore(self, Command):
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )

        try:
            test_class.gravity_backup_restore('restore')
        except Exception:
            assert False, "Exception occurred"

    @mock.patch('sh.Command')
    def test_gather_secrets(self, Command):
        expected_output = {
            'kube-system': ['cluster-tls'],
            'default': [
                'anaconda-enterprise-certs',
                'anaconda-config-files',
            ],
            'test_namespace': [
                'anaconda-credentials-user-creds-anaconda-enterprise-3ggji6dp'
            ]
        }
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                test_class = models.Accord(self.setup_args_backup_default())

        Command().return_value = model_returns.GET_SECRETS
        test_class.namespace = 'test_namespace'
        test_class.get_all_secrets()

        self.assertEqual(
            test_class.secret_files,
            expected_output,
            'Returned value is not expected value'
        )

    def test_container_command_exception(self):
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        container = 'test_container'
        command = 'ls'
        mock_response = mock.Mock()
        mock_response.side_effect = subprocess.CalledProcessError(1, 'ls')
        with mock.patch(
            'accord.models.subprocess.run',
            side_effect=mock_response
        ):
            with mock.patch('accord.models.sys.exit'):
                test_class.run_command_on_container(container, command)

    def test_container_command_success_return(self):
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        container = 'test_container'
        command = 'ls'
        try:
            with mock.patch('accord.models.subprocess.run') as r:
                r.return_value.stdout = 'Success'
                results = test_class.run_command_on_container(
                    container,
                    command,
                    True
                )
        except Exception:
            assert False, "Exception occurred"

        self.assertEqual(results, 'Success', 'Did not receive expected value')

    def test_container_command_success_no_return(self):
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        container = 'test_container'
        command = 'ls'
        try:
            with mock.patch('accord.models.subprocess.run'):
                test_class.run_command_on_container(
                    container,
                    command,
                    False
                )
        except Exception:
            assert False, "Exception occurred"

    def test_su_command_exception(self):
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        container = 'test_container'
        command = 'ls'
        mock_response = mock.Mock()
        mock_response.side_effect = subprocess.CalledProcessError(1, 'ls')
        with mock.patch(
            'accord.models.subprocess.run',
            side_effect=mock_response
        ):
            with mock.patch('accord.models.sys.exit'):
                test_class.run_su_command(container, command)

    def test_su_command_success(self):
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        container = 'test_container'
        command = 'ls'
        try:
            with mock.patch('accord.models.subprocess.run'):
                test_class.run_su_command(container, command)
        except Exception:
            assert False, "Exception occurred"

    def test_authenticate_api(self):
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )

        try:
            test_class.authenticate_api()
        except Exception:
            assert False, "Exception occurred"

    def test_launch_deployment(self):
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )

        try:
            test_class.launch_deployment()
        except Exception:
            assert False, "Exception occurred"
