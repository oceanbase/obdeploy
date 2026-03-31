# coding: utf-8
# Copyright (c) 2025 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

def generate_conf_and_systemd(plugin_context, *args, **kwargs):
    new_cluster_config = kwargs.get('new_cluster_config')
    cluster_config = plugin_context.cluster_config

    if new_cluster_config:
        old_config = cluster_config.get_server_conf_with_default(cluster_config.servers[0])
        new_config = new_cluster_config.get_server_conf_with_default(cluster_config.servers[0])
        enable_start_value = new_config['enable_auto_start']
        if enable_start_value == old_config['enable_auto_start'] or enable_start_value == False:
            return plugin_context.return_true()

    clients = plugin_context.clients
    stdio = plugin_context.stdio

    stdio.start_loading('Generate conf and systemd scripts')

    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)

        home_path = server_config.get('home_path')
        data_dir = server_config.get('data_dir')
        redo_dir = server_config.get('redo_dir')
        mysql_port = server_config.get('mysql_port')

        # Generate seekdb_systemd_start content
        start_script_content = """#!/bin/bash
# SeekDB start script
# This script reads configuration from {home_path}/seekdb.cnf and starts seekdb

CONFIG_FILE="{home_path}/seekdb.cnf"
BASE_DIR="{home_path}"
SYSTEMD_PID_FILE="$BASE_DIR/run/seekdb.pid"

export LD_LIBRARY_PATH='{home_path}/lib:'


# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file $CONFIG_FILE not found"
    exit 1
fi

# Initialize additional parameters
ADDITIONAL_PARAMS=""
DATA_DIR=""
REDO_DIR=""

# Function to read configuration file and build command line arguments
read_config() {{
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

        key="${{line%%=*}}"
        value="${{line#*=}}"

        # Trim whitespace
        key="$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        value="$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

        case "$key" in
            "port")
                ADDITIONAL_PARAMS="$ADDITIONAL_PARAMS --port=$value"
                ;;
            "base-dir")
                BASE_DIR="$value"
                ;;
            "data-dir")
                ADDITIONAL_PARAMS="$ADDITIONAL_PARAMS --data-dir=$value"
                DATA_DIR="$value"
                ;;
            "redo-dir")
                ADDITIONAL_PARAMS="$ADDITIONAL_PARAMS --redo-dir=$value"
                REDO_DIR="$value"
                ;;
            *)
                ADDITIONAL_PARAMS="$ADDITIONAL_PARAMS --parameter $key=$value"
                ;;
        esac
    done < "$CONFIG_FILE"
}}

# Check if data-dir is specified and not empty
read_config

if [ -z "$DATA_DIR" ]; then
    DATA_DIR="$BASE_DIR/data"
fi

if [ -z "$REDO_DIR" ]; then
    REDO_DIR="$BASE_DIR/redo"
fi

CMD="$BASE_DIR/bin/seekdb --base-dir=$BASE_DIR"

echo "Starting seekdb with command: $CMD"
echo "Configuration loaded from: $CONFIG_FILE"

$CMD
CMD_EXIT_CODE=$?

# Create softlink for PID file to systemd expected location
SEEKDB_PID_FILE="$BASE_DIR/run/seekdb.pid"
if [ -f "$SEEKDB_PID_FILE" ] && [ "$SEEKDB_PID_FILE" != "$SYSTEMD_PID_FILE" ]; then
    # Create target directory if it doesn't exist
    mkdir -p "$(dirname "$SYSTEMD_PID_FILE")"
    # Remove existing link or file if exists
    rm -f "$SYSTEMD_PID_FILE"
    # Create softlink
    ln -s "$SEEKDB_PID_FILE" "$SYSTEMD_PID_FILE"
fi

# Check if command executed successfully
OBSHELL_BINARY="$BASE_DIR/bin/obshell"
if [ $CMD_EXIT_CODE -eq 0 ]; then
    # Start obshell agent (ignore errors)
    echo "SeekDB started successfully, starting obshell agent..."
    if [ -f "$OBSHELL_BINARY" ]; then
        sleep 1
        "$OBSHELL_BINARY" agent start --seekdb --base-dir=$BASE_DIR || true
    else
        echo "Warning: "$OBSHELL_BINARY" not found, skipping obshell agent start"
    fi
else
    echo "SeekDB failed to start with exit code: $CMD_EXIT_CODE"
fi

exit $CMD_EXIT_CODE
""".format(home_path=home_path)

        # Generate seekdb_systemd_stop content
        stop_script_content = """#!/bin/bash
CONFIG_FILE="{home_path}/seekdb.cnf"
BASE_DIR="{home_path}"

# Function to read base-dir from configuration file (consistent with start script)
read_base_dir_from_config() {{
    if [ -f "$CONFIG_FILE" ]; then
        while IFS= read -r line; do
            # Skip empty lines and comments
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

            key="${{line%%=*}}"
            value="${{line#*=}}"

            # Trim whitespace
            key="$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
            value="$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

            if [ "$key" = "base-dir" ]; then
                BASE_DIR="$value"
                echo "Using base-dir from config: $BASE_DIR"
                return 0
            fi
        done < "$CONFIG_FILE"
    fi
    return 1
}}

read_base_dir_from_config

if [ -f "$BASE_DIR/run/daemon.pid" ]; then
    pid=$(cat "$BASE_DIR/run/daemon.pid")
    kill -9 "$pid" 2>/dev/null || true
fi

if [ -f "$BASE_DIR/run/obshell.pid" ]; then
    pid=$(cat "$BASE_DIR/run/obshell.pid")
    kill -9 "$pid" 2>/dev/null || true
fi

if [ -f "$BASE_DIR/run/seekdb.pid" ]; then
    pid=$(cat "$BASE_DIR/run/seekdb.pid")
    kill -9 "$pid" 2>/dev/null || true
fi

systemd-notify "STATUS=seekdb is down"
""".format(home_path=home_path)

        # Generate seekdb.cnf content
        cnf_content = """base-dir={home_path}
data-dir={data_dir}
redo-dir={redo_dir}

# These parameters are valid only during initialization
port={mysql_port}
""".format(home_path=home_path, data_dir=data_dir, redo_dir=redo_dir, mysql_port=mysql_port)

        start_script_path = "{}/seekdb_systemd_start".format(home_path)
        stop_script_path = "{}/seekdb_systemd_stop".format(home_path)
        cnf_path = "{}/seekdb.cnf".format(home_path)

        # Write start script
        res = client.write_file(start_script_content, start_script_path)
        if not res:
            stdio.error("Failed to write {} to {}".format(start_script_path, server.ip))
            stdio.stop_loading('fail')
            return plugin_context.return_false()
            
        res = client.execute_command("chmod +x {}".format(start_script_path))
        if not res:
            stdio.error("Failed to set executable permission on {} on {}".format(start_script_path, server.ip))
            stdio.stop_loading('fail')
            return plugin_context.return_false()

        # Write stop script
        res = client.write_file(stop_script_content, stop_script_path)
        if not res:
            stdio.error("Failed to write {} to {}".format(stop_script_path, server.ip))
            stdio.stop_loading('fail')
            return plugin_context.return_false()
            
        res = client.execute_command("chmod +x {}".format(stop_script_path))
        if not res:
            stdio.error("Failed to set executable permission on {} on {}".format(stop_script_path, server.ip))
            stdio.stop_loading('fail')
            return plugin_context.return_false()

        # Write cnf
        res = client.write_file(cnf_content, cnf_path)
        if not res:
            stdio.error("Failed to write {} to {}".format(cnf_path, server.ip))
            stdio.stop_loading('fail')
            return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
