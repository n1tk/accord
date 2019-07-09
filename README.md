Accord
======

Use this Python package to help facilitate the backup and restore of your Anaconda Enterprise 5 installation.

To backup the system, you'll need to install the ``accord`` package on the master node of the AE cluster. 

### Setup conda environment and install accord
```sh
# Get miniconda and install it
curl -O https://repo.anaconda.com/miniconda/Miniconda2-4.6.14-Linux-x86_64.sh
bash Miniconda2-4.6.14-Linux-x86_64.sh  # Accept the license and take the defaults

# Source bashrc to pick up conda paths
source ~/.bashrc

# Create profile, and install package
conda create -n python37 python=3.7 -y
conda activate python37
conda install -c aeadmin accord -y
```

### Syncing
You have the option to sync the backup files to another Anaconda Enterprise cluster. To do so, the user specified to do the sync must meet the following criteria:
- User must exist on both systems
- User can sudo to root without a password
- User can SSH to the destination system with passwordless sudo

**NOTE:** When performing a backup, connectivity between the two systems will be tested to confirm that passwordless SSH is working before any backup or sync operation is attempted. During that test, the destination directory where the restored files will be placed is also created.

### Backup
The backup process does not interfere with the running system, and therefore can be performed while others are using the platform.

**NOTE:** Any files *in a running project that have not been committed to your version control repository* **will not** be backed up.

Run the following command to perform a backup:

```sh
accord -a backup
```

All files being backed up are placed in the ``/opt/anaconda_backup`` directory by default, which includes the following:

- A dump of the Postgres database
- Gravity
- All secrets and config files used in the system (stored in ``[BACKUP_DIRECTORY]/secrets``)
- The object store, which includes all project data

You can change the default backup location by passing the ``-d`` or ``--directory`` option to the command, followed by the desired path. If you use a different backup location, make note of it, as you'll refer to it when restoring the files from backup.

You can also choose to backup **only** the Anaconda Enterprise repositories that have been mirrored, to move them from one cluster to another. Instead of mirroring on each installed cluster, you can perform the mirror on one AE5 cluster, then backup and restore the repositories across all AE5 clusters in an environment.

In this case, include the following options with the ``backup`` command:

```sh
accord -a backup --repos-only -u <SYNC USER> -n <SYNC NODE>
```

Where:

* ``--repos-only`` = Backup the repository database only, and sync the repository on the running cluster to another cluster.

* ``-u`` = The username to use for the sync operation described above. The user must have passwordless ssh setup to successfully ``rsync`` file.

* ``-n`` = The node to sync the repository and database backup to (i.e., the AE5 master node on the target cluster).

### Restore

Run the following command to restore the backup files from the default directory ``/opt/anaconda_backup``, whether on the same cluster or in a DR setup.

```sh
accord -a restore
```

If you specified an alternate directory to store the backup files, specify the location to restore the files from using the ``-d`` or ``--directory`` option, followed by directory that was specified during the backup operation.

If during the backup you chose to backup only the mirrored repositories, pass the a ``--repdo-only`` option to the restore command:

```sh
accord -a restore --repos-only
```

**NOTE:** During the restore process, the platform configuration file is replaced by the config map that was backed up from the source cluster. If you don't want the platform config file to be replaced during the restore, you can pass a ``--no-config`` option to the command:

```sh
accord -a restore --no-config
```

**Note:** During the backup process, a 0 byte file named ``restore`` is placed in the backup directory. This file signals that a backup was completed, but has not been restored. The restore process checks for the presence of this file before running the restore operation described below. When the restore process has completed, it removes that file from the backup directory. 

If you want to restore the backup files and the 0 byte ``restore`` file is not in the backup directory location, you must pass an ``--override`` flag to run the restore process:

```sh
accord -a restore --override
```
