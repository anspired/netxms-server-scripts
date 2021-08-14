#!/usr/bin/env nxpython
#
# Utility script to run multiple python scripts using the same Jython instance.
# Useful because nxshell takes a long time to connect.
#

import os
import sys
import json


def _readconfig():
    config_file = os.path.join(os.getcwd(), 'crontab-script.json')
    if os.path.exists(config_file):
        fh = open(config_file, 'r')
        for script in json.load(fh):
            yield script
        fh.close()
    else:
        sys.stderr.write('Unable to load config: %s\n' % config_file)
        sys.exit(1)


def _runscript(python_code, filename=None, comment=None):
    script = compile(python_code+'\n', filename or 'crontab-script.py', 'exec')
    if filename: print 'Running: %s' % filename
    if comment: print comment
    exec script in {
        'session': session,
        's': s,
        'objects': objects
    }


def _runscriptfile(script_name):
    script_path = os.path.join(os.getcwd(), script_name)
    if os.path.exists(script_path):
        fh = open(script_path, 'r')
        lines = fh.readlines()
        for idx, line in enumerate(lines):
            if line.startswith('session.disconnect'):
                lines[idx] = '#' + lines[idx]
            lines[idx] = lines[idx].rstrip()
        fh.close()
        _runscript('\n'.join(lines), script_path)


for script in _readconfig():
    if script.get('enabled', False) is True:
        _runscriptfile(script['filename'])

_runscript('session.syncObjects()', 'sync objects')
_runscript('session.disconnect()', 'disconnect from session')
sys.exit(0)
