
from accord.models import Accord
from accord import exceptions


import argparse
import datetime
import pathlib
import json
import time
import yaml
import sys
import os
import sh


def backup_postgres_database(process):
    process.get_postgres_docker_container()
    backup_command = (
        "su - postgres -c 'pg_dumpall -U postgres --clean -f "
        f"{process.postgres_container_backup_path}'"
    )
    # Check for existing sql file and if there remove it
    if os.path.isfile(process.postgres_system_backup_path):
        os.remove(process.postgres_system_backup_path)

    # Backup the repository
    process.run_command_on_container(process.docker_cont_id, backup_command)

    # Check for the file and ensure it is there
    if not os.path.isfile(process.postgres_system_backup_path):
        raise exceptions.NoPostgresBackup(
            'Could not find backup file for postgres'
        )

    # Move the backup to the backup directory
    sh.mv(
        process.postgres_system_backup_path,
        f'{process.backup_directory}/'
    )


def backup_repository_db(process):
    process.get_postgres_docker_container()
    backup_command = (
        "su - postgres -c 'pg_dump -U postgres -F t anaconda_repository > "
        f"{process.postgres_container_repo_backup_path}'"
    )
    # Check for existing backup file and if there remove it
    if os.path.isfile(f'{process.postgres_system_repo_backup_path}'):
        os.remove(f'{process.postgres_system_repo_backup_path}')

    # Backup the repository
    process.run_command_on_container(process.docker_cont_id, backup_command)

    # Check for file path and ensure that it created
    if not os.path.isfile(f'{process.postgres_system_repo_backup_path}'):
        raise exceptions.NoPostgresBackup(
            'Could not find backup file for postgres'
        )

    # Move the backup to the backup directory
    sh.mv(
        f'{process.postgres_system_repo_backup_path}',
        f'{process.backup_directory}/'
    )


def restore_postgres_database(process):
    process.get_postgres_docker_container()

    # Copy SQL backup to the DB directory so the container can see it
    sh.mv(
        f'{process.backup_directory}/{process.postgres_backup_name}',
        process.postgres_system_backup_path
    )

    # Change permissions on the backup
    sh.chown(
        'polkitd:input',
        process.postgres_system_backup_path
    )
    restore_command = (
        "su - postgres -c 'psql -U postgres < "
        f"{process.postgres_container_backup_path}'"
    )
    process.run_command_on_container(process.docker_cont_id, restore_command)


def file_backup_restore(process, action):
    if action == 'backup':
        with sh.pushd('/opt/anaconda'):
            sh.tar(
                "--exclude=storage/pgdata",
                "--exclude=storage/object/anaconda-repository",
                "-czvf",
                process.storage_backup_name,
                "storage"
            )

        sh.mv(
            f'/opt/anaconda/{process.storage_backup_name}',
            f'{process.backup_directory}/'
        )
    elif action == 'restore':
        sh.mv(
            f'{process.backup_directory}/{process.storage_backup_name}',
            '/opt/anaconda'
        )
        with sh.pushd('/opt/anaconda'):
            sh.tar(
                '-xzvf',
                f'/opt/anaconda/{process.storage_backup_name}'
            )
            sh.rm(f'{process.storage_backup_name}')


def backup_secrets_config_maps(process):
    secret_path = f'{process.backup_directory}/secrets'
    if not os.path.exists(secret_path):
        pathlib.Path(secret_path).mkdir(parents=True)

    process.get_all_secrets()
    for namespace, secrets in process.secret_files.items():
        for secret in secrets:
            temp_secret_path = f'{secret_path}/{secret}.yaml'
            with open(temp_secret_path, 'w') as fs:
                process.kubectl(
                    'get',
                    'secrets',
                    secret,
                    f'-n {namespace}',
                    '-o yaml',
                    _out=fs
                )

    for namespace, config_maps in process.config_maps.items():
        for cm in config_maps:
            temp_cm_path = f'{secret_path}/{cm}.yaml'
            with open(temp_cm_path, 'w') as fcm:
                process.kubectl(
                    'get',
                    'configmaps',
                    cm,
                    f'-n {namespace}',
                    '-o yaml',
                    _out=fcm
                )


def sanitize_secrets_config_maps(process):
    metadata_to_clear = [
        "creationTimestamp",
        "resourceVersion",
        "selfLink",
        "uid"
    ]
    for namespace, secrets in process.secret_files.items():
        for secret in secrets:
            temp_secret = f'{process.backup_directory}/secrets/{secret}.yaml'
            with open(temp_secret, 'r') as f:
                data = yaml.load(f, Loader=yaml.FullLoader)

            for label in metadata_to_clear:
                del data['metadata'][label]

            with open(temp_secret, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)

    for namespace, config_maps in process.config_maps.items():
        for cm in config_maps:
            temp_cm = f'{process.backup_directory}/secrets/{cm}.yaml'
            with open(temp_cm, 'r') as f:
                data = yaml.load(f, Loader=yaml.FullLoader)

            for label in metadata_to_clear:
                del data['metadata'][label]

            with open(temp_cm, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)


def sync_files(process):
    # Set permissions to rsync user for all of the backup directory
    sh.chown(
        '-R',
        f'{process.sync_user}:{process.sync_user}',
        f'{process.backup_directory}'
    )

    # Run the rsync to the sync server
    rsync_command = (
        f'rsync -avrq {process.backup_directory}/ '
        f'{process.sync_user}@{process.sync_node}:{process.backup_directory}'
    )
    process.run_su_command(process.sync_user, rsync_command)


def sync_repositories(process):
    # Change permissions for the repo directories
    user_perms_command = (
        f'/bin/ssh -t -q {process.sync_user}@{process.sync_node}'
        f' \'sudo chown -R {process.sync_user}:{process.sync_user} '
        f'{process.repository}\''
    )
    process.run_su_command(process.sync_user, user_perms_command)

    # Run the rsync for all of the repository directories
    rsync_command = (
        f'rsync -avrq {process.repository}/ '
        f'{process.sync_user}@{process.sync_node}:{process.repository}'
    )
    process.run_su_command(process.sync_user, rsync_command)

    # Change the permissions back after the rsync
    root_perms_command = (
        f'/bin/ssh -t -q {process.sync_user}@{process.sync_node}'
        f' \'sudo chown -R root:root '
        f'{process.repository}\''
    )
    process.run_su_command(process.sync_user, root_perms_command)


def scale_postgres_pod(process, pod_number):
    if pod_number not in [1, 0]:
        raise exceptions.InvalidReplicaCount(
            'Invalid replica count to scale for postgres'
        )

    process.kubectl(
        'scale',
        'deploy',
        f'--replicas={pod_number}',
        'anaconda-enterprise-postgres'
    )
    success = False
    while success is False:
        if pod_number == 1:
            try:
                sh.grep(
                    sh.grep(
                        process.kubectl('get', 'pods'),
                        'postgres'
                    ),
                    'Running'
                )
                success = True
            except sh.ErrorReturnCode_1:
                pass
                """
                Exception will be thrown as no results will be given and
                it is running then it will exit properly
                """
        else:
            try:
                sh.grep(process.kubectl('get', 'pods'), 'postgres')
            except sh.ErrorReturnCode_1:
                """
                Exception will be thrown as no results will be given which
                is the desired result on the scale down
                """
                success = True

        # Waiting for postgres pod to complete scale
        time.sleep(2)

    return


def cleanup_and_restore_files(process):
    timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H%M%S')
    # Compress and timestamp the existing files minus the repos
    with sh.pushd('/opt/anaconda'):
        sh.tar(
            "--exclude=storage/object/anaconda-repository",
            "-czvf",
            f"git_pgdata.snapshot_{timestamp}.tar.gz",
            "storage"
        )

    # Cleanup directories as things will get restored
    sh.rm('-Rf', '/opt/anaconda/storage/git')
    sh.rm('-Rf', '/opt/anaconda/storage/pgdata')
    sh.rm('-Rf', '/opt/anaconda/storage/object/anaconda-objects')
    sh.rm('-Rf', '/opt/anaconda/storage/object/anaconda-projects')

    # Restore the files
    file_backup_restore(process, 'restore')

    # Recreate the postgres directory and set permissions
    sh.mkdir(process.postgres_system_backup)
    sh.chown('polkitd:root', f'{process.postgres_system_backup}')
    sh.chmod('700', f'{process.postgres_system_backup}')

    return


def restart_pods(process):
    # Restart all the pods after the restore
    process.kubectl('delete', '--all', 'pods')

    # Watch the pods and make sure they come back up
    success = False
    while success is False:
        try:
            sh.grep(
                sh.grep(
                    process.kubectl('get', 'pods'),
                    '-v',
                    'Running'
                ),
                '-v',
                'NAME'
            )
        except sh.ErrorReturnCode_1:
            success = True

        # Waiting for postgres pod to complete scale
        time.sleep(2)


def cleanup_sessions_deployments(process):
    # Grab all sessions and deployments and remove them
    deployments = []
    try:
        deployments = sh.awk(
            sh.grep(
                process.kubectl('get', 'deployments'),
                'anaconda-app-\|anaconda-session-'  # noqa
            ),
            '{print $1}'
        )
    except Exception:
        # Ok if exception thrown as it means nothing was found
        pass

    for deploy in deployments:
        process.kubectl('delete', 'deployment', deploy.strip())

    return


def cleanup_postgres_database(process):
    # Get the docker container IDs
    process.get_postgres_docker_container()

    # Cleanup the sessions so there are no running sessions in the DB
    session_cleanup = (
        "su - postgres -c 'psql -U postgres -d "
        "anaconda_workspace -c \\\"delete from sessions;\\\"'"
    )
    process.run_command_on_container(process.docker_cont_id, session_cleanup)

    """
    After DB restore grab all deployments that are in a started state. This
    will allow for deployments to be started after everything has been
    restored properly
    """
    deployments_gather = (
        "su - postgres -c 'psql -t -U postgres -d anaconda_deploy "
        "-c \\\"select row_to_json(t) from(select * from deployments) t;\\\"'"
    )
    return_select = process.run_command_on_container(
        process.docker_cont_id,
        deployments_gather,
        return_value=True
    )
    rows = return_select.decode('utf-8').split('\n')
    for row in rows:
        if row != '':
            temp_row = json.loads(row)
            if temp_row.get('status_text', None) == 'Started':
                process.to_start.append(temp_row)

    # Cleanup the deployments so there are no running deployments in the DB
    deployments_cleanup = (
        "su - postgres -c 'psql -U postgres -d "
        "anaconda_deploy -c \\\"truncate deployments cascade;\\\"'"
    )
    process.run_command_on_container(
        process.docker_cont_id,
        deployments_cleanup
    )
    return


def restoring_config_files(process):
    # Restart all the pods after the restore
    command_return = process.kubectl(
        'replace',
        '-f',
        f'{process.backup_directory}/secrets/'
        'anaconda-enterprise-anaconda-platform.yml'
    )
    if 'replaced' not in command_return:
        print('ERROR: Could not restore the platform config file')


def restore_secrets(process):
    """
    This is accomplished when doing the gravity restore. Leaving as a
    placeholder as a reference.
    """


def restore_repo_db(process):
    process.get_postgres_docker_container()

    # Copy backup to the DB directory so the container can see it
    sh.mv(
        f'{process.backup_directory}/{process.repository_db_name}',
        f'{process.postgres_system_backup}/{process.repository_db_name}'
    )

    # Change permissions on the backup
    sh.chown(
        'polkitd:input',
        f'{process.postgres_system_backup}/{process.repository_db_name}'
    )
    restore_command = (
        "su - postgres -c 'pg_restore -U postgres --clean -d "
        f"anaconda_repository {process.postgres_container_backup}/"
        f"{process.repository_db_name}'"
    )
    # Restore the repository DB
    process.run_command_on_container(process.docker_cont_id, restore_command)


def restore_deployments(process):
    """
    This is specific request and is not implemented in the general code
    """
    pass


def handle_arguments():
    description = (
        'Add a description'
    )
    parser = argparse.ArgumentParser(description=description)
    group = parser.add_argument_group('Sync Files', description)
    group.add_argument(
        '-s',
        '--sync',
        required=False,
        default=False,
        action='store_true',
        help=(
            'Transfer backup files to another server. Uses rsync to do this'
            ' and will need to have SSH access and passwordless entry into the'
            ' restore server. Default value is False'
        )
    )
    group.add_argument(
        '-u',
        '--sync-user',
        required=False,
        default='root',
        help=(
            'User to use when doing the sync. Required only if sync is being'
            ' used to transfer the backup files. Default user is root'
        )
    )
    group.add_argument(
        '-n',
        '--sync-node',
        required=False,
        default=None,
        help='Node to sync the files to after the backup is complete'
    )
    parser.add_argument(
        '-a',
        '--action',
        required=False,
        default='backup',
        choices=['backup', 'restore'],
        help=(
            'Action to perform. Default value is backup'
        )
    )
    parser.add_argument(
        '-d',
        '--directory',
        required=False,
        default='/opt/anaconda_backup',
        help=(
            'Backup/Restore directory to use to save or pull files from. '
            'Default path is /opt/anaconda_backup'
        )
    )
    parser.add_argument(
        '--override',
        required=False,
        default=False,
        action='store_true',
        help=(
            'Override restore checks and if the files are present do the '
            'restore anyway. Default is False'
        )
    )
    parser.add_argument(
        '--no-config',
        required=False,
        default=False,
        action='store_true',
        help='Do not restore the config files to the system'
    )
    parser.add_argument(
        '--repos-only',
        required=False,
        default=False,
        action='store_true',
        help='Sync and backup repositories only'
    )
    parser.add_argument(
        '--start-deployments',
        required=False,
        default=False,
        action='store_true',
        help=(
            'Start up deployments that are running on the master system'
        )
    )
    args = parser.parse_args()
    return args


def main():
    arguments = handle_arguments()
    try:
        process = Accord(arguments)
    except exceptions.RestoreSignal:
        print(
            'Signal file for restore not found so not performing '
            'restore of AE5'
        )
        sys.exit(1)

    if process.action == 'backup':
        if process.repos_only:
            # Backup the repository database only
            print('Backing up repository database')
            backup_repository_db(process)
        else:
            # Backup the full database
            print('Backing up postgres database')
            backup_postgres_database(process)

            # Backup gravity
            print('Running gravity backup')
            process.gravity_backup_restore('backup')

            # tar up all of the files
            print('Packaging all of the files with tar')
            file_backup_restore(process, process.action)

            # Backup the secrets
            print('Backing up all secrets')
            backup_secrets_config_maps(process)

            # Clean all of the secrets
            print('Sanitizing secrets')
            sanitize_secrets_config_maps(process)

        # Drop in signal file to indicate good to restore
        print('Adding signal for restore')
        process.add_signal_for_restore()

        # Sync the files if requested
        if process.sync_files:
            # Sync the anaconda repositories
            print('Syncing up repositories to restore cluster')
            sync_repositories(process)
            # Sync the backup files
            print('Syncing all backup files to restore cluster')
            sync_files(process)
    elif process.action == 'restore':
        if process.repos_only:
            # Restore the repository database only
            print('Restoring repositories only')
            restore_repo_db(process)
        else:
            # Cleanup any existing deployments or sessions running
            print('Cleaning up sessions and deployments')
            cleanup_sessions_deployments(process)

            # Scale the postgres pod down to 0 so we can do some work
            print('Scaling down postgres pod for restore')
            scale_postgres_pod(process, 0)

            # Cleanup the existing files and restore the backup
            print('Cleanup and setup directories for restore')
            cleanup_and_restore_files(process)

            # Scale the postgres pod up to 1
            print('Scaling up postgres pod after restore')
            scale_postgres_pod(process, 1)

            # Restore the postgres database
            print('Restoring postgres database')
            restore_postgres_database(process)

            # Cleanup sessions and deployments
            print('Cleaning up postgres database')
            cleanup_postgres_database(process)

            if not process.no_config:
                # Load in anaconda platform file
                print('Restoring AE5 config file')
                restoring_config_files(process)

            # Restore the secrets for the cluster
            print('Restoring secrets')
            restore_secrets(process)

            # Restart the pods
            print('Restarting all pods')
            restart_pods(process)

            if process.start_deployments:
                # Restore deployments
                print('Starting up deployments that should be running')
                restore_deployments(process)

        print('Cleaning up restore file')
        process.remove_signal_restore_file()


if __name__ == '__main__':
    main()
