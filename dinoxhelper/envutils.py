import os
import pickle
from subprocess import PIPE, Popen

PYTHON_DUMP_ENVIRON = """\
import sys
import os
import pickle
data = pickle.dumps(dict(os.environ))
stdout = os.fdopen(sys.stdout.fileno(), "wb")
stdout.write(data)
"""


def source_bash_file(path):
    bash_cmds = [
        "source '%s'" % path,
        "python -c '%s'" % PYTHON_DUMP_ENVIRON,
    ]
    p = Popen(['bash', '-c', '&&'.join(bash_cmds)], stdout=PIPE)
    stdout, _ = p.communicate()
    if stdout:
        environ = pickle.loads(stdout)
        for k, v in environ.items():
            os.environ[k] = v
