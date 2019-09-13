import re
import subprocess
import time
from typing import List

from bauh.commons.system import new_root_subprocess, run_cmd, new_subprocess

BASE_CMD = 'snap'


def is_installed():
    version = get_snapd_version()
    return False if version is None else True


def get_version():
    res = run_cmd('{} --version'.format(BASE_CMD), print_error=False)
    return res.split('\n')[0].split(' ')[-1].strip() if res else None


def get_snapd_version():
    res = run_cmd('{} --version'.format(BASE_CMD), print_error=False)

    if not res:
        return None
    else:
        lines = res.split('\n')

        if lines and len(lines) >= 2:
            version = lines[1].split(' ')[-1].strip()
            return version if version and version.lower() != 'unavailable' else None
        else:
            return None


def app_str_to_json(app: str) -> dict:
    app_data = [word for word in app.split(' ') if word]
    app_json = {
        'name': app_data[0],
        'version': app_data[1],
        'rev': app_data[2],
        'tracking': app_data[3],
        'publisher': app_data[4] if len(app_data) >= 5 else None,
        'notes': app_data[5] if len(app_data) >= 6 else None
    }

    return app_json


def get_info(app_name: str, attrs: tuple = None):
    full_info_lines = run_cmd('{} info {}'.format(BASE_CMD, app_name))

    data = {}

    if full_info_lines:
        re_attrs = r'\w+' if not attrs else '|'.join(attrs)
        info_map = re.findall(r'({}):\s+(.+)'.format(re_attrs), full_info_lines)

        for info in info_map:
            data[info[0]] = info[1].strip()

        if not attrs or 'description' in attrs:
            desc = re.findall(r'\|\n+((\s+.+\n+)+)', full_info_lines)
            data['description'] = ''.join([w.strip() for w in desc[0][0].strip().split('\n')]).replace('.', '.\n') if desc else None

        if not attrs or 'commands' in attrs:
            commands = re.findall(r'commands:\s*\n*((\s+-\s.+\s*\n)+)', full_info_lines)
            data['commands'] = commands[0][0].replace('-', '').strip().split('\n') if commands else None

    return data


def read_installed() -> List[dict]:
    res = run_cmd('{} list'.format(BASE_CMD), print_error=False)

    apps = []

    if res and len(res) > 0:
        lines = res.split('\n')

        if not lines[0].startswith('error'):
            for idx, app_str in enumerate(lines):
                if idx > 0 and app_str:
                    apps.append(app_str_to_json(app_str))

            info_out = new_subprocess(['cat', *['/var/lib/snapd/snap/{}/current/meta/snap.yaml'.format(a['name']) for a in apps]]).stdout

            idx = -1
            for o in new_subprocess(['grep', '-E', '(summary|type)', '--colour=never'], stdin=info_out).stdout:
                if o:
                    line = o.decode()

                    if line.startswith('summary:'):
                        idx += 1
                        apps[idx]['summary'] = line.split(':')[1].strip()
                    else:
                        apps[idx]['type'] = line.split(':')[1].strip()

    return apps


def search(word: str, exact_name: bool = False) -> List[dict]:
    apps = []

    res = run_cmd('{} find "{}"'.format(BASE_CMD, word), print_error=False)

    if res:
        res = res.split('\n')

        if not res[0].startswith('No matching'):
            for idx, app_str in enumerate(res):
                if idx > 0 and app_str:
                    app_data = [word for word in app_str.split(' ') if word]

                    if exact_name and app_data[0] != word:
                        continue

                    apps.append({
                        'name': app_data[0],
                        'version': app_data[1],
                        'publisher': app_data[2],
                        'notes': app_data[3] if app_data[3] != '-' else None,
                        'summary': app_data[4] if len(app_data) == 5 else '',
                        'rev': None,
                        'tracking': None,
                        'type': None
                    })

                if exact_name and len(apps) > 0:
                    break

    return apps


def uninstall_and_stream(app_name: str, root_password: str):
    return new_root_subprocess([BASE_CMD, 'remove', app_name], root_password)


def install_and_stream(app_name: str, confinement: str, root_password: str) -> subprocess.Popen:

    install_cmd = [BASE_CMD, 'install', app_name]  # default

    if confinement == 'classic':
        install_cmd.append('--classic')

    return new_root_subprocess(install_cmd, root_password)


def downgrade_and_stream(app_name: str, root_password: str) -> subprocess.Popen:
    return new_root_subprocess([BASE_CMD, 'revert', app_name], root_password)


def refresh_and_stream(app_name: str, root_password: str) -> subprocess.Popen:
    return new_root_subprocess([BASE_CMD, 'refresh', app_name], root_password)
