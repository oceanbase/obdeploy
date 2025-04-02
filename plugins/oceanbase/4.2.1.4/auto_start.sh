#!/bin/bash

# Check for the existence of the 'obshell' file in the provided homepath
homepath=$1
appname=$2
obshell="$homepath/bin/obshell"
if [ ! -f "$obshell" ]; then
    echo -e "\033[31m[ERROR]\033[0m Sorry, [$obshell] does not exist."
    echo "You may need to upgrade the obcluster. Please consult the developers for assistance."
    exit 1
fi

system_dir="/etc/systemd/system"

# Retrieve the owner of the 'observer' process configuration files
owner=$(stat -c '%U' $homepath/etc)
echo "Owner of the observer configuration: $owner"

# Construct and output the content for the systemd service unit file
name=obd_oceanbase_$appname.service

mkdir -p $homepath/tmp
file=$homepath/tmp/$name


start_cmd="${homepath}/bin/obshell cluster start"
V4231="4.2.3.1"
version=`${homepath}/bin/obshell version`
if printf '%s\n' "$V4231" "$version" | sort -CV; then
    start_cmd="${homepath}/bin/obshell admin start --takeover 0 --ob"
fi

echo "Creating the service unit file at $file..."
# Write the service content to the file
cat << EOF > ${file}
[Unit]
Description=observer
After=network.target
[Service]
User=${owner}
Type=forking
KillSignal=SIGKILL
ExecStart=${start_cmd}
ExecStop=${homepath}/bin/obshell admin stop
PIDFile=${homepath}/run/observer.pid
Restart=on-failure
RestartSec=10
SuccessExitStatus=SIGKILL
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