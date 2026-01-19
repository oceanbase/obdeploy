from __future__ import absolute_import, division, print_function

import os

from _errno import EC_FAIL_TO_INIT_PATH, InitDirFailedErrorMessage, EC_COMPONENT_DIR_NOT_EMPTY


def path_has_content(path, client):
    """Return True if path exists and is non-empty."""
    ret = client.execute_command('ls -A {0} 2>/dev/null'.format(path))
    return bool(ret and ret.stdout.strip())


def clean_path(path, client):
    """Remove all content under path."""
    return client.execute_command('rm -fr %s' % path, timeout=-1)


def init(plugin_context, source_option=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    deploy_name = plugin_context.deploy_name
    global_conf = cluster_config.get_global_conf()
    home_path = global_conf.get('home_path')
    volume_mount = global_conf.get('volume_mount')
    global_ret = True
    force = getattr(plugin_context.options, 'force', False)
    stdio.start_loading('Initializes powerrag mount path')

    if not home_path or not volume_mount:
        missing = []
        if not home_path:
            missing.append('home_path')
        if not volume_mount:
            missing.append('volume_mount')
        stdio.stop_loading('fail')
        stdio.error('missing config: %s' % ','.join(missing))
        return plugin_context.return_false()

    need_init_paths = [home_path,
                       volume_mount,
                        f"{volume_mount}/dify/storage",
                        f"{volume_mount}/plugin_daemon",
                        f"{volume_mount}/ragflow/logs",
                        f"{volume_mount}/ragflow/history_data_agent",
                        f"{volume_mount}/ragflow/conf",
                        f"{volume_mount}/powerrag/logs",
                        f"{volume_mount}/powerrag/storage"]

    for server in cluster_config.servers:
        client = clients[server]
        for target_path in need_init_paths:
            has_content = path_has_content(target_path, client)
            if has_content:
                if force:
                    ret = clean_path(target_path, client)
                    if not ret:
                        global_ret = False
                        stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='path', msg=ret.stderr))
                else:
                    global_ret = False
                    stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='path', msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=target_path)))
                    source_option == "deploy" and stdio.error(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)

            if global_ret and not client.execute_command("bash -c 'mkdir -p {0}'".format(os.path.join(target_path))):
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='path', msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=target_path)))
                global_ret = False

            if global_ret and target_path == volume_mount:
                client.execute_command('chmod u+rw %s' % target_path)
            if global_ret:
                can_access = client.execute_command(f"[ -r '{target_path}' ] && [ -w '{target_path}' ] && echo true || echo false").stdout.strip() == "true"
                if not can_access:
                    stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='path', msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=target_path)))
                    global_ret = False

    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    stdio.stop_loading('fail')
    return plugin_context.return_false()
