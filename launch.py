"""Start SpiceScope independently of the terminal and reconnect to an existing server."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get('SPICE_PORT', '8000'))
URL = f'http://127.0.0.1:{PORT}'

def status():
    try:
        with urllib.request.urlopen(URL+'/api/health', timeout=2) as response:
            state=json.load(response)
        with urllib.request.urlopen(URL+'/api/info', timeout=2) as response:
            identity=json.load(response)
        if identity.get('model')!='DINOv3 ViT-B/16':
            raise RuntimeError('Another application is using the selected port.')
        return state
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return None

def runtime():
    candidates=[os.environ.get('SPICE_PYTHON'), str(ROOT/'.venv'/'Scripts'/'python.exe'), r'D:\powder dataset\.venv\Scripts\python.exe', sys.executable]
    probe="import importlib.util,sys;sys.exit(not all(importlib.util.find_spec(m) for m in ['torch','torchvision','transformers','safetensors','cv2','pandas','fastapi','uvicorn','multipart']))"
    for candidate in dict.fromkeys(filter(None,candidates)):
        if Path(candidate).is_file():
            check=subprocess.run([candidate,'-c',probe],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=30)
            if check.returncode==0:return candidate
    raise RuntimeError('No complete model runtime was found. Run Setup_SpiceScope.cmd once.')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    current=status()
    if current is None:
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',PORT))==0:
                raise RuntimeError(f'Port {PORT} is in use by another application.')
        executable=runtime()
        flags=getattr(subprocess,'DETACHED_PROCESS',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)
        with (ROOT/'server-output.log').open('a',encoding='utf-8') as output, (ROOT/'server-error.log').open('a',encoding='utf-8') as error:
            child=subprocess.Popen([executable,'-u',str(ROOT/'app.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=output,stderr=error,close_fds=True,creationflags=flags)
        (ROOT/'server.pid').write_text(str(child.pid),encoding='ascii')
        print('Starting local model. This window can close after startup.',flush=True)
    else:
        child=None
        print('Reconnecting to SpiceScope.',flush=True)
    for _ in range(180):
        current=status()
        if current and current.get('status')=='ready':
            print('SpiceScope ready: '+URL,flush=True)
            if not args.no_browser:webbrowser.open(URL)
            return 0
        if current and current.get('status')=='unavailable':
            raise RuntimeError(current.get('message','Model loading failed.')+' See server-error.log.')
        if child is not None and child.poll() is not None:
            raise RuntimeError('The server stopped during startup. See server-error.log.')
        time.sleep(1)
    raise RuntimeError('Startup is taking longer than expected. See server-error.log, then retry the launcher.')

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print('SpiceScope: '+str(exc),file=sys.stderr)
        sys.exit(1)
