#!/bin/bash

# Check for the existence of the 'obshell' file in the provided homepath
homepath=$1
appname=$2
system_dir="/etc/systemd/system"

# Retrieve the owner of the 'observer' process configuration files
owner=$(stat -c '%U' $homepath/etc)
echo "Owner of the observer configuration: $owner"

# Construct and output the content for the systemd service unit file
name=obd_seekdb_$appname.service

mkdir -p $homepath/tmp
file=$homepath/tmp/$name

echo "Creating the service unit file at $file..."
# Write the service content to the file
cat << EOF > ${file}
[Unit]
Description=observer
After=network.target
[Service]
User=${owner}
Type=notify
ExecStart=${homepath}/seekdb_systemd_start
ExecStop=${homepath}/seekdb_systemd_stop
PIDFile=${homepath}/run/seekdb.pid
SuccessExitStatus=SIGKILL
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
LimitSTACK=infinity
[Install]
WantedBy=multi-user.target
EOF
echo "The content of the Service unit file is:"
sed 's/^/  /' "$file"

chmod -R o+rwx "$homepath/tmp"
# Deploy the unit configuration file to the system directory
echo "Deploying the service unit file to the system directory"
cp -f $file $system_dir/$name
echo "Updating permissions for the service unit file..."
chmod 644 $system_dir/$name
echo "Reloading the systemd daemon to recognize the new service"
systemctl daemon-reload
systemctl enable $name
echo -e "\033[32m[SUCCEED]\033[0m $name has been installed."