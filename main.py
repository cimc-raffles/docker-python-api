from fastapi import FastAPI, WebSocket, BackgroundTasks, status

import docker
import json
import re
import shlex
import subprocess
import asyncio
import sys
import requests
import os

from typing import Optional, Set, List

from pydantic import BaseModel

from datetime import datetime, time, timedelta

from starlette.endpoints import WebSocket, WebSocketEndpoint


queue: asyncio.Queue = asyncio.Queue()

client = docker.from_env()

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/containers")
def index():
    containers = client.containers.list(all=True)
    result = []
    for c in containers:
        result.append(container2Object(c))
    return result


@app.get("/containers/{id}")
def container(id: str):
    return getContainerObject(id)


@app.get("/containers/{id}/stop")
def stop(id: str):
    c = getContainer(id)
    c.stop()
    return getContainerObject(id)


@app.get("/containers/{id}/start")
def start(id: str):
    c = getContainer(id)
    c.start()
    return getContainerObject(id)


@app.get("/containers/{id}/restart")
def restart(id: str):
    c = getContainer(id)
    c.restart()
    return getContainerObject(id)


@app.get("/containers/{id}/logs")
def logs(id: str, tail: int = 100, follow: bool = False, timestamp: bool = True, since=None, until=None):
    c = getContainer(id)
    result = []
    print("tail {} {}".format(tail, type(tail)))

    for line in c.logs(stream=True, follow=follow, timestamps=timestamp, since=since, until=until, tail=tail):
        foo = line.decode().rstrip()
        matcher = re.match(
            r'(\d{4}-\d{1,2}-\d{1,2}T\d{1,2}:\d{1,2}:\d{1,2}.\d+Z)', foo)
        time = matcher.group()
        message = foo.replace(time, '', 1)
        result.append({'timestamp': time, 'message': message})
    return result


@app.get("/nodes")
def nodes():
    result = client.nodes.list()
    for n in result:
        print(n.__dict__)


class AlertData(BaseModel):
    status: Optional[str] = None
    labels: Optional[dict] = None
    annotations: Optional[dict] = None
    startsAt: Optional[datetime] = None
    endsAt: Optional[datetime] = None
    generatorURL: Optional[str] = None


class AlertMessage(BaseModel):
    version: Optional[str] = None
    groupKey: Optional[str] = None
    truncatedAlerts: Optional[int] = None
    status: Optional[str] = None
    receiver: Optional[str] = None
    groupLabels: Optional[dict] = None
    commonLabels:  Optional[dict] = None
    commonAnnotations: Optional[dict] = None
    externalURL: Optional[str] = None
    alerts:  Optional[List[AlertData]] = None


vxin_hook_url = os.getenv('VXIN_HOOK_URL')


@app.post("/alerts")
def messages(message: AlertMessage):
    if not message.alerts:
        return
    text = ''
    for alert in message.alerts:
        text += '%s \n ' % (alert.annotations['summary'])
    data = {
        "msgtype": "markdown",
        "markdown": {
            "content": re.sub(u'\u0000', "", text)
        }
    }
    print(type(text), json.dumps(data))
    result = requests.post(vxin_hook_url, json.dumps(data))
    print(result.text)


@app.websocket_route("/logs")
class ShellWSEndpoint(WebSocketEndpoint):
    async def on_connect(self, websocket):
        await websocket.accept()
        while True:
            try:
                command = await websocket.receive_text()
                command = shlex.split(command)
                proc = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT)
                self.proc = proc
                while True:
                    data = await proc.stdout.readline()
                    line = data.decode().strip()
                    if not line or not len(line):
                        code = await proc.wait()
                        self.code = code
                        break
                    await websocket.send_text(line)
            except BaseException as e:  # asyncio.TimeoutError and ws.close()
                if hasattr(self, 'proc'):
                    self.proc.kill()
                await websocket.send_text(str(e))
                break
            finally:
                pass
        await websocket.close()

    async def on_disconnect(self, websocket, close_code):
        await websocket.close()
        if hasattr(self, 'proc'):
            self.proc.kill()


def getContainer(parameter):
    return client.containers.get(parameter)


def getContainerObject(parameter):
    return container2Object(getContainer(parameter))


def container2Object(container):
    return {'id': container.short_id, 'name': container.name, 'status': container.status, 'image': container.image.tags, 'labels': container.labels}
