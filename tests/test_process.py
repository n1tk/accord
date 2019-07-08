
from .fixtures import process_returns
from unittest import TestCase


from accord import exceptions
from accord import process
from accord import models


import pathlib
import mock
import os
import sh


class TestProcess(TestCase):
    def setUp(self):
        self.time_patcher = mock.patch('accord.process.time.sleep')
        self.time_patcher.start()

    def tearDown(self):
        self.time_patcher.stop()
        temp_files = ['restore', 'test_backup.sql']
        for tf in temp_files:
            if os.path.isfile(tf):
                os.remove(tf)

        if os.path.exists('anaconda_backup'):
            os.rmdir('anaconda_backup')

        temp_secrets = ['secrets/test-secret.yaml', 'secrets/test-cm.yaml']
        for ts in temp_secrets:
            if os.path.isfile(ts):
                os.remove(ts)

        if os.path.exists('secrets'):
            os.rmdir('secrets')

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

    def setup_temp_file(self, temp_path):
        open(temp_path, 'a').close()

    def setup_secrets(self):
        if not os.path.exists('secrets'):
            pathlib.Path('secrets').mkdir(parents=True)

        # Write things to temp files
        with open('secrets/test-secret.yaml', 'w') as f:
            for line in process_returns.SECRET_BACKUP_FILE:
                f.write(f'{line}\n')

        with open('secrets/test-cm.yaml', 'w') as f:
            for line in process_returns.CM_BACKUP_FILE:
                f.write(f'{line}\n')

    # Test main()
    @mock.patch('accord.models.pathlib')
    @mock.patch('sh.Command')
    def test_main_backup(self, mock_pathlib, Command):
        with mock.patch(
            'accord.process.argparse.ArgumentParser.parse_args'
        ) as args:
            args.return_value = self.setup_args_backup_default(
                directory=''
            )
            with mock.patch('accord.process.backup_postgres_database'):
                with mock.patch('accord.process.sync_repositories'):
                    with mock.patch('accord.process.file_backup_restore'):
                        with mock.patch(
                            'accord.process.backup_secrets_config_maps'
                        ):
                            with mock.patch(
                                'accord.process.sanitize_secrets_config_maps'
                            ):
                                process.main()

        if not os.path.isfile('restore'):
            assert False, 'restore file was not added'

    @mock.patch('accord.models.pathlib')
    def test_main_backup_repos_only(self, mock_pathlib):
        with mock.patch(
            'accord.process.argparse.ArgumentParser.parse_args'
        ) as args:
            args.return_value = self.setup_args_backup_default(
                repos_only=True,
                directory=''
            )
            with mock.patch('accord.process.backup_repository_db'):
                process.main()

        if not os.path.isfile('restore'):
            assert False, 'restore file was not added'

    @mock.patch('accord.models.pathlib')
    @mock.patch('sh.Command')
    def test_main_backup_sync_files(self, mock_pathlib, Command):
        with mock.patch(
            'accord.process.argparse.ArgumentParser.parse_args'
        ) as args:
            args.return_value = self.setup_args_backup_default(
                repos_only=True,
                directory='',
                sync_user='test',
                sync_node='1.2.3.4',
                sync=True
            )
            with mock.patch('accord.models.Accord.run_su_command'):
                with mock.patch('accord.process.backup_repository_db'):
                    with mock.patch('accord.process.sync_repositories'):
                        with mock.patch('accord.process.sync_files'):
                            process.main()

        if not os.path.isfile('restore'):
            assert False, 'restore file was not added'

    def test_main_restore_no_config(self):
        self.setup_temp_file('restore')
        with mock.patch(
            'accord.process.argparse.ArgumentParser.parse_args'
        ) as args:
            args.return_value = self.setup_args_restore_default(
                no_config=True,
                directory=''
            )
            with mock.patch('accord.process.cleanup_sessions_deployments'):
                with mock.patch('accord.process.scale_postgres_pod'):
                    with mock.patch(
                        'accord.process.cleanup_and_restore_files'
                    ):
                        with mock.patch('accord.process.scale_postgres_pod'):
                            with mock.patch(
                                'accord.process.restore_postgres_database'
                            ):
                                with mock.patch(
                                    'accord.process.cleanup_postgres_database'
                                ):
                                    with mock.patch(
                                        'accord.process.restart_pods'
                                    ):
                                        process.main()

        if os.path.isfile('restore'):
            assert False, 'restore file was not cleaned up'

    def test_main_restore_start_deployments(self):
        self.setup_temp_file('restore')
        with mock.patch(
            'accord.process.argparse.ArgumentParser.parse_args'
        ) as args:
            args.return_value = self.setup_args_restore_default(
                start_deployments=True,
                directory=''
            )
            with mock.patch('accord.process.cleanup_sessions_deployments'):
                with mock.patch('accord.process.scale_postgres_pod'):
                    with mock.patch(
                        'accord.process.cleanup_and_restore_files'
                    ):
                        with mock.patch('accord.process.scale_postgres_pod'):
                            with mock.patch(
                                'accord.process.restore_postgres_database'
                            ):
                                with mock.patch(
                                    'accord.process.cleanup_postgres_database'
                                ):
                                    with mock.patch(
                                        'accord.process.restoring_config_files'
                                    ):
                                        with mock.patch(
                                            'accord.process.restart_pods'
                                        ):
                                            process.main()

        if os.path.isfile('restore'):
            assert False, 'restore file was not cleaned up'

    def test_main_restore_repos(self):
        self.setup_temp_file('restore')
        with mock.patch('accord.process.Accord.setup_backup_directory'):
            with mock.patch(
                'accord.process.argparse.ArgumentParser.parse_args'
            ) as args:
                args.return_value = self.setup_args_restore_default(
                    repos_only=True,
                    directory=''
                )

                with mock.patch('accord.process.restore_repo_db'):
                    process.main()

        if os.path.isfile('restore'):
            assert False, 'restore file was not cleaned up'

    @mock.patch('accord.process.argparse')
    def test_main_restore_exception(self, mock_args):
        raise_exception = mock.Mock()
        raise_exception.side_effect = exceptions.RestoreSignal
        with mock.patch('accord.process.Accord', side_effect=raise_exception):
            with self.assertRaises(SystemExit):
                process.main()

    # Postgres - Backup
    @mock.patch('sh.Command')
    @mock.patch('sh.mv', create=True)
    def test_backup_postgres_database(self, Command, mv):
        test_class = None
        self.setup_temp_file('test_backup.sql')
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                with mock.patch('accord.models.Accord.test_sync_to_backup'):
                    test_class = models.Accord(
                        self.setup_args_backup_default()
                    )

        test_class.postgres_system_backup_path = 'test_backup.sql'
        with mock.patch('accord.process.os.remove'):
            with mock.patch('accord.models.Accord.run_command_on_container'):
                process.backup_postgres_database(test_class)

        if not os.path.isfile('test_backup.sql'):
            assert False, 'Did not clean up original file'

    @mock.patch('sh.Command')
    @mock.patch('sh.mv', create=True)
    def test_backup_postgres_database_exception(self, Command, mv):
        test_class = None
        self.setup_temp_file('test_backup.sql')
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                with mock.patch('accord.models.Accord.test_sync_to_backup'):
                    test_class = models.Accord(
                        self.setup_args_backup_default()
                    )

        test_class.postgres_system_backup_path = 'test_backup.sql'
        with mock.patch('accord.models.Accord.run_command_on_container'):
            try:
                process.backup_postgres_database(test_class)
                assert False, 'Exception should have been thrown'
            except exceptions.NoPostgresBackup:
                pass
            except Exception:
                assert False, 'Exception thrown that was not expected'

        if os.path.isfile('test_backup.sql'):
            assert False, 'Did not clean up original file'

    # Postgres - Restore
    @mock.patch('sh.Command')
    @mock.patch('sh.mv', create=True)
    @mock.patch('sh.chown', create=True)
    def test_restore_database(self, Command, mv, chown):
        self.setup_temp_file('test_backup.sql')
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )

        test_class.postgres_system_repo_backup_path = 'test_backup.sql'
        with mock.patch('accord.process.os.remove'):
            with mock.patch('accord.models.Accord.run_command_on_container'):
                process.restore_postgres_database(test_class)

        if not os.path.isfile('test_backup.sql'):
            assert False, 'Did not cleanup the original file'

    # Postgres - Repos
    @mock.patch('sh.Command')
    @mock.patch('sh.mv', create=True)
    def test_backup_postgres_repos_exception(self, Command, mv):
        test_class = None
        self.setup_temp_file('test_backup.sql')
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                with mock.patch('accord.models.Accord.test_sync_to_backup'):
                    test_class = models.Accord(
                        self.setup_args_backup_default()
                    )

        test_class.postgres_system_repo_backup_path = 'test_backup.sql'
        with mock.patch('accord.models.Accord.run_command_on_container'):
            try:
                process.backup_repository_db(test_class)
                assert False, 'Exception should have been thrown'
            except exceptions.NoPostgresBackup:
                pass
            except Exception:
                assert False, 'Exception thrown that was not expected'

        if os.path.isfile('test_backup.sql'):
            assert False, 'Did not clean up original file'

    @mock.patch('sh.Command')
    @mock.patch('sh.mv', create=True)
    def test_backup_postgres_repos(self, Command, mv):
        test_class = None
        self.setup_temp_file('test_backup.sql')
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                with mock.patch('accord.models.Accord.test_sync_to_backup'):
                    test_class = models.Accord(
                        self.setup_args_backup_default()
                    )

        test_class.postgres_system_repo_backup_path = 'test_backup.sql'
        with mock.patch('accord.process.os.remove'):
            with mock.patch('accord.models.Accord.run_command_on_container'):
                process.backup_repository_db(test_class)

        if not os.path.isfile('test_backup.sql'):
            assert False, 'Did not cleanup the original file'

    # File - Backup
    @mock.patch('sh.pushd', create=True)
    @mock.patch('sh.tar', create=True)
    @mock.patch('sh.mv', create=True)
    def test_file_backup(self, pushd, tar, mv):
        test_class = None
        self.setup_temp_file('test_backup.sql')
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                with mock.patch('accord.models.Accord.test_sync_to_backup'):
                    test_class = models.Accord(
                        self.setup_args_backup_default()
                    )

        process.file_backup_restore(test_class, 'backup')

    # File - Restore
    @mock.patch('sh.pushd', create=True)
    @mock.patch('sh.tar', create=True)
    @mock.patch('sh.mv', create=True)
    def test_file_restore(self, pushd, tar, mv):
        self.setup_temp_file('test_backup.sql')
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )

        test_class.storage_backup_name = 'test_backup.sql'
        process.file_backup_restore(test_class, 'restore')

        if os.path.isfile('test_backup.sql'):
            assert False, 'Did not cleanup the original file'

    # Secrets
    @mock.patch('sh.Command')
    def test_backup_secrets_cm(self, Command):
        test_class = None
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                with mock.patch('accord.models.Accord.test_sync_to_backup'):
                    test_class = models.Accord(
                        self.setup_args_backup_default()
                    )

        test_class.backup_directory = '.'
        test_class.secret_files = {'default': ['test-secret']}
        test_class.config_maps = {'default': ['test-cm']}
        with mock.patch('accord.models.Accord.get_all_secrets'):
            process.backup_secrets_config_maps(test_class)

        if not os.path.exists('secrets'):
            assert False, 'Did not automatically create the directory'

        if not os.path.exists('secrets/test-secret.yaml'):
            assert False, 'Did not create the secret'

        if not os.path.exists('secrets/test-cm.yaml'):
            assert False, 'Did not create the secret'

    # Sanitize
    def test_sanitize_secret_cm(self):
        test_class = None
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                with mock.patch('accord.models.Accord.test_sync_to_backup'):
                    test_class = models.Accord(
                        self.setup_args_backup_default()
                    )

        test_class.backup_directory = '.'
        test_class.secret_files = {'default': ['test-secret']}
        test_class.config_maps = {'default': ['test-cm']}

        self.setup_secrets()

        with mock.patch('accord.models.Accord.get_all_secrets'):
            process.sanitize_secrets_config_maps(test_class)

        if not os.path.exists('secrets'):
            assert False, 'Did not automatically create the directory'

        if not os.path.exists('secrets/test-secret.yaml'):
            assert False, 'Did not create the secret'

        if not os.path.exists('secrets/test-cm.yaml'):
            assert False, 'Did not create the secret'

        cm_diff = []
        with open('secrets/test-cm.yaml', 'r') as results:
            for line in results:
                if line not in process_returns.CM_EXPECTED:
                    cm_diff.append(line)

        self.assertEquals(
            cm_diff,
            [],
            'Differences were found in the config map from what is expected'
        )

        secret_diff = []
        with open('secrets/test-secret.yaml', 'r') as results:
            for line in results:
                if line not in process_returns.SECRECT_EXPECTED:
                    secret_diff.append(line)

        self.assertEquals(
            secret_diff,
            [],
            'Differences were found in the secret from what is expected'
        )

    # Sync - Files
    @mock.patch('sh.chown', create=True)
    def test_sync_files(self, chown):
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                with mock.patch('accord.models.Accord.test_sync_to_backup'):
                    test_class = models.Accord(
                        self.setup_args_backup_default(
                            sync_user='test',
                            sync_node='1.2.3.4',
                            sync=True
                        )
                    )

        with mock.patch('accord.process.Accord.run_su_command'):
            process.sync_files(test_class)

    # Sync - Repositories
    @mock.patch('sh.chown', create=True)
    def test_sync_repositories(self, chown):
        with mock.patch('accord.models.Accord.setup_backup_directory'):
            with mock.patch('accord.models.Accord.remove_signal_restore_file'):
                with mock.patch('accord.models.Accord.test_sync_to_backup'):
                    test_class = models.Accord(
                        self.setup_args_backup_default(
                            sync_user='test',
                            sync_node='1.2.3.4',
                            sync=True,
                            repos_only=True
                        )
                    )

        mock_response = mock.Mock()
        mock_response.side_effect = ['', '', '']
        with mock.patch(
            'accord.process.Accord.run_su_command',
            side_effect=mock_response
        ):
            process.sync_repositories(test_class)

    # Scale pod
    def test_scale_pod_invalid_count(self):
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        try:
            process.scale_postgres_pod(test_class, 99)
            assert False, 'Exception should have been raised'
        except exceptions.InvalidReplicaCount:
            pass
        except Exception:
            assert False, 'Invalid exception thrown'

    @mock.patch('sh.Command')
    @mock.patch('sh.grep', create=True)
    def test_scale_up_pod_success(self, Command, grep):
        grep().side_effect = [
            'kubectl',
            sh.ErrorReturnCode_1(
                'grep',
                'out'.encode('utf-8'),
                'error'.encode('utf-8')
            ),
            ''
        ]
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        process.scale_postgres_pod(test_class, 1)

    @mock.patch('sh.Command')
    @mock.patch('sh.grep', create=True)
    def test_scale_down_pod_success(self, Command, grep):
        Command().side_effect = [
            '',
            process_returns.RUNNING_PODS
        ]
        grep().side_effect = [
            'NAME'.encode('utf-8'),
            sh.ErrorReturnCode_1(
                'grep',
                'out'.encode('utf-8'),
                'error'.encode('utf-8')
            )
        ]
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        process.scale_postgres_pod(test_class, 0)

    # Restart Pods
    @mock.patch('sh.Command')
    @mock.patch('sh.grep', create=True)
    def test_restart_pods(self, Command, grep):
        Command().side_effect = [
            '',
            process_returns.RUNNING_PODS
        ]
        grep().side_effect = [
            'kubectl',
            'NAME'.encode('utf-8'),
            sh.ErrorReturnCode_1(
                'grep',
                'out'.encode('utf-8'),
                'error'.encode('utf-8')
            )
        ]
        # grep().return_value = sh.ErrorReturnCode_1
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        process.restart_pods(test_class)

    # Cleanup/Restore Files
    @mock.patch('sh.pushd', create=True)
    @mock.patch('sh.tar', create=True)
    @mock.patch('sh.rm', create=True)
    @mock.patch('sh.mkdir', create=True)
    @mock.patch('sh.chown', create=True)
    @mock.patch('sh.chmod', create=True)
    def test_cleanup_restore_files(self, pushd, tar, rm, mkdir, chown, chmod):
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        with mock.patch('accord.process.file_backup_restore'):
            process.cleanup_and_restore_files(test_class)

    # Cleanup - Sessions/Deployments
    @mock.patch('sh.Command')
    @mock.patch('sh.grep', create=True)
    @mock.patch('sh.awk', create=True)
    def test_cleanup_sessions_none(self, Command, grep, awk):
        awk().side_effect = [
            sh.ErrorReturnCode_1(
                'grep',
                'out'.encode('utf-8'),
                'error'.encode('utf-8')
            )
        ]
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        process.cleanup_sessions_deployments(test_class)

    @mock.patch('sh.awk', create=True)
    @mock.patch('sh.grep', create=True)
    @mock.patch('sh.Command')
    def test_cleanup_sessions_success(self, Command, grep, awk):
        mock_command = mock.Mock()
        mock_command.return_value = ['deployment_to_grab']
        mock_grep = mock.Mock()
        mock_grep.return_value = mock_command.return_value
        awk.return_value = mock_grep.return_value
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        process.cleanup_sessions_deployments(test_class)

    # Cleanup - Database
    def test_cleanup_postgres_db(self):
        mock_response = mock.Mock()
        mock_response.side_effect = [
            '',
            process_returns.DEPLOYMENTS_POSTGRES,
            ''
        ]
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        with mock.patch('accord.models.Accord.get_postgres_docker_container'):
            with mock.patch(
                'accord.models.Accord.run_command_on_container',
                side_effect=mock_response
            ):
                process.cleanup_postgres_database(test_class)

        self.assertEquals(
            len(test_class.to_start),
            1,
            'Incorrect number of deployments'
        )

    # Config Files - Restore
    @mock.patch('sh.Command')
    def test_restore_secrets_failed(self, Command):
        Command().return_value = ''
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )

        process.restoring_config_files(test_class)

    @mock.patch('sh.Command')
    def test_restore_secrets_success(self, Command):
        Command().return_value = ''
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )

        process.restoring_config_files(test_class)

    # Secrets - Restore
    def test_restore_secrets(self):
        """ Not in place yet so leaving as a placeholder """
        pass

    # Restore repository database
    @mock.patch('sh.chown', create=True)
    @mock.patch('sh.mv', create=True)
    def test_restore_repository_db(self, chown, mv):
        test_class = models.Accord(
            self.setup_args_restore_default(override=True)
        )
        with mock.patch('accord.models.Accord.get_postgres_docker_container'):
            with mock.patch('accord.models.Accord.run_command_on_container'):
                process.restore_repo_db(test_class)
