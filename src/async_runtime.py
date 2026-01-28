from collections import deque

class Future:
    def __init__(self):
        self.done = False
        self.result = None
        self.waiters = []
    
    def __repr__(self):
        return f"future '{hex(id(self))}'"

    def set_result(self, value):
        if self.done:
            return
        self.done = True
        self.result = value
        for w in self.waiters:
            w(self)

    def add_waiter(self, waiter):
        if self.done:
            waiter(self)
        else:
            self.waiters.append(waiter)

class Task:
    def __init__(self, frame, loop):
        self.frame = frame
        self.loop = loop
        self.future = Future()
        self.loop.ready.append(self)

    def step(self, value=None):
        try:
            if value is None:
                yielded = self.frame.run(None)
            else:
                yielded = self.frame.run(value)
            if isinstance(yielded, Future):
                yielded.add_waiter(lambda fut: self.loop.ready.append(self))
            else:
                self.loop.ready.append(self)
        except StopIteration as stop:
            self.future.set_result(stop.value)

class EventLoop:
    def __init__(self):
        self.ready = deque()

    def create_task(self, frame):
        task = Task(frame, self)
        return task.future

    def run(self):
        while self.ready:
            task = self.ready.popleft()
            task.step()

loop = EventLoop()