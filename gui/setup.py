import sys
import subprocess
# implement pip as a subprocess:
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pillow'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'packaging'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'customtkinter'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'sqlite3'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 're'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'asyncio'])
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'bleak'])


# subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'git+https://github.com/airgproducts/pybluez2.git@0.46'])