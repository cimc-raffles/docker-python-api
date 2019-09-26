
from django.http import JsonResponse,HttpResponse

# Create your views here.

import docker, json , re

client = docker.from_env()

def index(request):
    list = client.containers.list(all=True)
    result = []
    for c in list:
        foo = { 'id' : c.short_id , 'name' : c.name , 'status' : c.status , 'image' : c.image.tags , 'labels' : c.labels }
        result.append( foo)
    return JsonResponse( result ,safe=False)

def container(request,id):
    c = getContainer( id)
    foo = { 'id' : c.short_id , 'name' : c.name , 'status' : c.status , 'image' : c.image.tags , 'labels' : c.labels }
    return JsonResponse( foo)

def stop(request,id):
    c = getContainer( id)
    c.stop()
    return HttpResponse(content_type='application/json',status=204)

def start(request,id):
    c = getContainer( id)
    c.start()
    return HttpResponse(content_type='application/json',status=200)

def restart(request,id):
    c = getContainer( id)
    c.restart()
    return HttpResponse(content_type='application/json',status=200)

def logs(request,id):
    size = request.GET.get('size')
    if not size:
        size = 20
    c = getContainer(id)
    result = []
    for line in c.logs(follow=False,tail=int(size),timestamps=True,stream=True):
        foo = line.decode()
        matcher = re.match(r'(\d{4}-\d{1,2}-\d{1,2}T\d{1,2}:\d{1,2}:\d{1,2}.\d+Z)' , foo)
        time = matcher.group()
        message = foo.replace( time , '' , 1).strip()
        result.append( {'timestamp' : time , 'message': message})
    return JsonResponse( result, safe=False)

def getContainer( parameter):
    return client.containers.get( parameter)