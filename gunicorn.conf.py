bind = '127.0.0.1:8010'

# restart workers after x requests
# defends against memory leaks
max_requests = 500

timeout = 30

workers = 2

worker_class = 'sync'

