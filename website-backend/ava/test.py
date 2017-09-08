
# testing django
def application(env, start_response):
    start_response('200 OK', [('Content-type', 'text/html')])
    return ["hello prod!"]

