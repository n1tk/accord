Accord
======

Python package to help facilitate the backup and restore your Anaconda Enterprise 5 install.

### Setup conda environment and install accord
```sh
# Get miniconda and install it
curl -O https://repo.anaconda.com/miniconda/Miniconda2-4.6.14-Linux-x86_64.sh
bash Miniconda2-4.6.14-Linux-x86_64.sh  # Accept the license and take the defaults

# Source bashrc to pick up conda paths
source ~/.bashrc

# Create profile, and preflight package
conda create -n python37 python=3.7 -y
conda activate python37
conda install -c aeadmin accord -y
```

### Syncing
For backups you have the option to sync the backup files to another Anaconda Enterprise cluster. In order for the process to work a user is specified to do the sync, and must meet the following criteria.
- Use must exist on both systems
- Ability to sudo to root as the specified user without a password
- Can SSH to the destination system with passwordless sudo

**Note:** During the initialization of the backup a test of the connectivity between the two systems will be done in order to confirm that passwordless SSH is working before any backup or sync is attempted. As part of that test the destination directory will be created which is where the restore files will be placed.

### Backup
To backup the system the package will need to be installed on the AE master node in the cluster. The backup does not interfere with the running system, and can be safely done while users are using the system.

**Note:** Any file(s) that has not been saved and committed in a running project will **not** be backed up.

Once installed you can run the following command to perform a backup.

```sh
accord -a backup
```

By default this will store all files for the backup in /opt/anaconda_backup directory which includes the following files.

- Postgres dump of the database
- Gravity backup
- All secrets and config files used in the system stored in [BACKUP_DIRECTORY]/secrets
- Object store which includes all project data

You can change the default backup location by passing the **-d** or **--directory** option in the command followed by the desired path.

An additional option for backup is to backup **only** the Anaconda Enterprise repositories that have been mirrored from one cluster to another. Instead of mirroring on all installed clusters it is possible to mirror to one AE5 cluster, and then backup/restore the repositories across all AE5 clusters in an environment.

To do this you would need to ensure you include the following options in your command line call.

```sh
accord -a backup --repos-only -u <SYNC USER> -n <SYNC NODE>
```

*--repos-only* : Only backup the repository database and sync the repositories on the
                 running cluster to another cluster

*-u* : Username to use for the sync operation. For the sync the user should have
       passwordless ssh setup in order to complete the rsync of the file.

*-n* : Node to sync the repositories and database backup to. This would be the AE5
       master on the target cluster.

**Note:** During the backup process a 0 byte file named *restore* is placed in the backup directory. This is checked by the restore process before running the restore.

### Restore

To restore the files from a backup on the same cluster or in a DR setup you do the following.

```sh
accord -a restore
```

This will use the files located in the backup directory that was specified during the backup. Be default this will be in */opt/anaconda_backup* directory.

If you need to change the directory were the backup files are located you can change the location with the *-d* or *--directory* option followed by the desired location

If during the backup you chose to only backup the mirrored repositories, then you need to pass the a repo only option to the restore command accordingly as follows.

```sh
accord -a restore --repos-only
```

During the restore process the platform configuration file is replaced using the backup config map from the source cluster. However if you do not want the platform config file to be replaced during a restore, then you can pass a no config option to the restore command seen in the example below..

```sh
accord -a restore --no-config
```

During a backup a 0 byte file named *restore* is placed in the backup directory. During initialization of the restore process a check is made to ensure that file is there, and it signals that a backup was completed that has not been restored. Once the restore has completed that file is removed from the backup directory location.

If you would like to do a restore and the 0 byte restore file is not in the backup directory location, you must pass an override flag to run the restore process as seen below.

```sh
accord -a restore --override
```
