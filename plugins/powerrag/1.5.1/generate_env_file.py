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


import os
import re
import stat

from const import COMPS_OB


def generate_env_file(plugin_context, *args, **kwargs):
    def parse_set_on_and_strategy(comment):
        set_on = ""
        strategy = ""

        m_set = re.search(r"SET_ON\(([^)]*)\)", comment)
        if m_set:
            inner = m_set.group(1).strip()
            set_on = inner if inner else "MUST_SET"

        m_strat = re.search(r"STRATEGY\(([^)]*)\)", comment)
        if m_strat:
            strategy = m_strat.group(1).strip()

        return set_on, strategy

    def should_handle_variable(set_on, global_config):
        set_on = set_on.strip()
        if not set_on:
            return False

        if "," in set_on:
            cond_var, cond_val = [x.strip() for x in set_on.split(",", 1)]
            if not cond_var:
                return False

            actual = global_config.get(cond_var.lower())
            if actual is None:
                return False

            return str(actual).lower() == cond_val.lower()

        if set_on == "MUST_SET":
            return True

        return False

    def replace_env_vars_in_default(value, global_config, env_map):
        """Expand $VAR / ${VAR} in default value (variable substitution only, no command execution)."""
        if not value:
            return value

        # Handle $VAR form
        pattern_dollar = re.compile(r"\$([a-zA-Z_][a-zA-Z0-9_]*)")
        while True:
            m = pattern_dollar.search(value)
            if not m:
                break
            var_name = m.group(1)
            # Try env_map first, then global_config (convert key to lowercase)
            var_val = env_map.get(var_name) if var_name in env_map else global_config.get(var_name.lower(), "")
            value = value.replace(f"${var_name}", str(var_val))

        # Handle ${VAR} form
        pattern_brace = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
        while True:
            m = pattern_brace.search(value)
            if not m:
                break
            var_name = m.group(1)
            # Try env_map first, then global_config (convert key to lowercase)
            var_val = env_map.get(var_name) if var_name in env_map else global_config.get(var_name.lower(), "")
            value = value.replace(f"${{{var_name}}}", str(var_val))

        return value

    def handle_default_setting(var_name, description, has_default, default_value, nullable, global_config, stdio, env_map):
        """Generic variable handling (includes NULLABLE and normal default value scenarios)."""
        if description:
            stdio.verbose(f"{var_name}: {description}")

        # Get value from global_config first (convert key to lowercase)
        config_value = global_config.get(var_name.lower())
        if config_value is not None:
            user_input = str(config_value)
            env_map[var_name] = user_input
        elif has_default:
            user_input = default_value
            env_map[var_name] = user_input
        else:
            if nullable:
                stdio.warn(f"Variable {var_name} is empty")
                user_input = ""
                env_map[var_name] = user_input
            else:
                stdio.error(f"Required variable {var_name} is not set in global_config")
                raise ValueError(f"Required variable {var_name} is not set")

        if user_input == "" and has_default:
            user_input = default_value
            env_map[var_name] = user_input

        if "<HOST-IP>" in user_input:
            HOST_IP = client.config.host
            user_input = user_input.replace("<HOST-IP>", HOST_IP)
            env_map[var_name] = user_input
            stdio.verbose(f"Replaced <HOST-IP> with: {HOST_IP}")

        return user_input

    def handle_port_strategy(var_name, description, has_default, default_value, global_config, stdio, env_map):
        if description:
            stdio.verbose(f"{var_name}: {description}")

        # Get value from global_config first (convert key to lowercase)
        config_value = global_config.get(var_name.lower())
        if config_value is not None:
            user_input = str(config_value)
            env_map[var_name] = user_input
        elif has_default:
            user_input = default_value
            env_map[var_name] = user_input
        else:
            stdio.warn(f"Port {var_name} is not set, will be disabled")
            env_map[var_name] = ""
            return ""

        if user_input == "":
            stdio.warn(f"Port {var_name} is not set, will be disabled")
            env_map[var_name] = ""
            return ""

        return user_input

    def handle_system_set_secret_strategy(var_name, description, global_config, stdio, env_map):
        import secrets

        if description:
            stdio.verbose(f"{var_name}: {description}")

        # Get value from global_config first (convert key to lowercase)
        config_value = global_config.get(var_name.lower())
        if config_value is not None:
            user_input = str(config_value)
            env_map[var_name] = user_input
            return user_input

        generated_secret = ""
        # Try openssl first to mimic bash
        try:
            result = client.execute_command("openssl rand -base64 42")
            if result and result.stdout.strip():
                generated_secret = result.stdout.strip()
                stdio.verbose("Generated random secret using openssl")
        except FileNotFoundError:
            stdio.warn("openssl command not found, will use Python to generate random secret")

        if not generated_secret:
            generated_secret = secrets.token_urlsafe(42)
            stdio.verbose("Generated random secret using Python")

        env_map[var_name] = generated_secret
        return generated_secret

    def handle_volume_prefix_strategy(var_name, description, has_default, default_value, global_config, stdio, env_map):
        if description:
            stdio.verbose(f"{var_name}: {description}")

        # Get value from global_config first (convert key to lowercase)
        if var_name == 'VOLUME_PREFIX':
            config_value = global_config.get("home_path")
        else:
            config_value = global_config.get(var_name.lower())
        if config_value is not None:
            user_input = str(config_value)
            env_map[var_name] = user_input
        elif has_default:
            user_input = default_value
            env_map[var_name] = user_input
        else:
            stdio.error(f"Required variable {var_name} is not set in global_config")
            raise ValueError(f"Required variable {var_name} is not set")

        if user_input == "":
            stdio.error(f"Invalid value for {var_name}")
            raise ValueError(f"Invalid value for {var_name}")

        return user_input

    def handle_compose_project_strategy(var_name, description, has_default, default_value, global_config, stdio, env_map):
        if description:
            stdio.verbose(f"{var_name}: {description}")

        # Get value from global_config first (convert key to lowercase)
        config_value = global_config.get(var_name.lower())
        if config_value is not None:
            user_input = str(config_value)
            env_map[var_name] = user_input
        elif has_default:
            user_input = default_value
            env_map[var_name] = user_input
        else:
            stdio.error(f"Required variable {var_name} is not set in global_config")
            raise ValueError(f"Required variable {var_name} is not set")

        if user_input == "":
            stdio.error(f"Invalid value for {var_name}")
            raise ValueError(f"Invalid value for {var_name}")

        return user_input

    def apply_strategy(strategy, var_name, description, has_default, default_value, global_config, stdio, env_map):
        """Apply corresponding strategy based on STRATEGY, return final variable value."""
        strategies = [s.strip() for s in strategy.split(",") if s.strip()]
        for item in strategies:
            if item == "NULLABLE":
                return handle_default_setting(
                    var_name, description, has_default, default_value, True, global_config, stdio, env_map
                )
            if item == "PORT":
                return handle_port_strategy(
                    var_name, description, has_default, default_value, global_config, stdio, env_map
                )
            if item == "SYSTEM_SET_SECRET":
                return handle_system_set_secret_strategy(var_name, description, global_config, stdio, env_map)
            if item == "VOLUME_PREFIX":
                return handle_volume_prefix_strategy(
                    var_name, description, has_default, default_value, global_config, stdio, env_map
                )
            if item == "COMPOSE_PROJECT":
                return handle_compose_project_strategy(
                    var_name, description, has_default, default_value, global_config, stdio, env_map
                )
            if item == "REPLACE_HOST_IP":
                # handled in default-setting via <HOST-IP> replacement
                continue

            stdio.warn(f"Unknown strategy: {item}")

        # No applicable strategy – fall back to normal (non-nullable) input
        return handle_default_setting(
            var_name, description, has_default, default_value, False, global_config, stdio, env_map
        )

    def extract_pure_comment(comment_block):
        """
        Extract "pure comment content" from a group of comment lines (starting with #):
        - Remove leading # and extra whitespace
        - Remove tags like SET_ON/STRATEGY/UPDATE_IN_UPGRADE
        - Keep user description text
        """
        if not comment_block:
            return ""

        # Join and then strip the leading '#'
        text = "\n".join(line.lstrip("#").strip() for line in comment_block)
        # Remove SET_ON(...) / STRATEGY(...) / UPDATE_IN_UPGRADE() like tags from the start
        text = re.sub(r"SET_ON\([^)]*\)", "", text)
        text = re.sub(r"STRATEGY\([^)]*\)", "", text)
        text = re.sub(r"UPDATE_IN_UPGRADE\([^)]*\)", "", text)
        text = text.strip()
        return text

    stdio = plugin_context.stdio
    stdio.start_loading('Generate powerrag .env file')
    cluster_config = plugin_context.cluster_config
    global_config = cluster_config.get_global_conf_with_default()

    # get_oceanbase_config
    for comp in COMPS_OB:
        if comp in cluster_config.depends:
            ob_servers = cluster_config.get_depend_servers(comp)
            ob_config = cluster_config.get_depend_config(comp, ob_servers[0])
            db_host = ob_servers[0].ip
            db_port = ob_config.get('mysql_port')
            ob_sye_password = ob_config.get('root_password')
            global_config['db_host'] = db_host
            global_config['db_port'] = db_port
            global_config['ob_sys_password'] = ob_sye_password
            powerrag_tenant_password = global_config.get('ob_tenant_password') or ob_config.get('powerrag_tenant_password')
            if not global_config.get('ob_tenant_password'):
                global_config['ob_tenant_password'] = powerrag_tenant_password

    servers = cluster_config.servers
    clients = plugin_context.clients
    env_map = plugin_context.get_variable('env_map')
    for server in servers:
        client = clients[server]
        example_env_file = os.path.join(global_config.get('home_path'), '.env.example')
        if not client.execute_command('ls %s' % example_env_file):
            stdio.stop_loading('fail')
            stdio.error('{} not found'.format(example_env_file))
            return plugin_context.return_false()

        import tempfile

        try:
            current_comments = []
            with open(example_env_file, 'r') as src:
                with tempfile.NamedTemporaryFile(delete=False, prefix="powerrag", suffix=".env", mode="w", encoding="utf-8") as dst:
                    for raw_line in src:
                        line = raw_line.rstrip("\n")

                        # Comment line
                        if re.match(r"^\s*#", line):
                            current_comments.append(line)
                            # Comments are written only when we decide about the variable line
                            continue

                        # Blank line
                        if line.strip() == "":
                            if current_comments:
                                for c in current_comments:
                                    dst.write(c + "\n")
                                current_comments = []
                            dst.write("\n")
                            continue

                        # Variable line with '='
                        if "=" in line:
                            var_name, var_value_raw = line.split("=", 1)
                            var_name = var_name.strip()
                            var_value_raw = var_value_raw.strip()

                            # Strip inline comment part from value
                            if "#" in var_value_raw:
                                before_hash, _after_hash = var_value_raw.split("#", 1)
                                var_value_raw = before_hash.rstrip()

                            # Determine set_on and strategy from comments
                            comment_text = "\n".join(current_comments)
                            set_on, strategy = parse_set_on_and_strategy(comment_text)

                            # Decide whether to handle variable interactively
                            if should_handle_variable(set_on, global_config):
                                # Prepare default value with env variable expansion
                                default_value = var_value_raw
                                has_default = default_value != ""
                                if has_default:
                                    default_value = replace_env_vars_in_default(default_value, global_config, env_map)

                                description = extract_pure_comment(current_comments)
                                # Apply strategy or default handler
                                try:
                                    final_value = (
                                        apply_strategy(
                                            strategy, var_name, description, has_default, default_value, global_config, stdio, env_map
                                        )
                                        if strategy
                                        else handle_default_setting(
                                            var_name,
                                            description,
                                            has_default,
                                            default_value,
                                            False,
                                            global_config,
                                            stdio,
                                            env_map,
                                        )
                                    )
                                except ValueError as e:
                                    stdio.stop_loading('fail')
                                    stdio.error(f'Failed to get value for {var_name}: {e}')
                                    return plugin_context.return_false()

                                # Write comments (if any) then var line
                                if current_comments:
                                    for c in current_comments:
                                        dst.write(c + "\n")
                                if final_value is bool:
                                    final_value = str(final_value).lower()
                                dst.write(f"{var_name}={final_value}\n\n")
                            else:
                                # No interactive handling – write comments and original line,
                                # but still expand env variables for internal usage.
                                if current_comments:
                                    for c in current_comments:
                                        dst.write(c + "\n")
                                if global_config.get(var_name.lower()):
                                    var_value_raw = global_config.get(var_name.lower())
                                if final_value is bool:
                                    final_value = str(final_value).lower()
                                dst.write(f"{var_name}={var_value_raw}\n\n")

                            current_comments = []
                        else:
                            # Non-empty, non-comment, no '=' – just write it through
                            if current_comments:
                                for c in current_comments:
                                    dst.write(c + "\n")
                                current_comments = []
                            dst.write(line + "\n")
                    settings = global_config.get('settings')
                    if settings:
                        for k, v in settings.items():
                            dst.write(f"{k.upper()}={v}\n")
            os.chmod(dst.name, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            client.execute_command('mv %s %s' % (dst.name, os.path.join(global_config.get('home_path'), '.env')))
        except Exception as e:
            stdio.stop_loading('fail')
            stdio.error('generate .env file failed: {}'.format(e))
            return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()




