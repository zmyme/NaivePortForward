import threading
import queue
import time

class Job():
    stat_waiting = 0
    stat_processing = 1
    stat_finished = 2
    stat_canceled = 3
    def __init__(self, func, args=[], kwargs={}, name=None):
        if name == None:
            name = 'job'

        self.id = None

        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.name = name

        self.results = None
        self.status = Job.stat_waiting

        self.worker = None

        self.running_lock = threading.Lock()
        self.running_lock.acquire()


    def run(self):
        if self.status == Job.stat_waiting:
            self.status = Job.stat_processing
            self.results = self.func(*self.args, **self.kwargs)
            self.status = Job.stat_finished
            self.running_lock.release()

    def set_name(self, name):
        self.name = name

    def set_id(self, jid):
        self.id = jid

    def __call__(self):
        self.run()
class Future():
    def __init__(self, job):
        self.job = job

    def is_finished(self):
        if self.job.status == Job.stat_finished:
            return True
        else:
            return False

    def resolve(self):
        if not self.is_finished():
            # wait for job finish
            self.job.running_lock.acquire()
            self.job.running_lock.release()
        return self.job.results

class Worker(threading.Thread):
    def __init__(self, work_queue):
        super(Worker, self).__init__()
        self.queue = work_queue
        self.terminate = False
        self.daemon=True
        self.free = True
        self.current_task = None

    def stop(self):
        self.terminate = True

    def run(self):
        while not self.terminate:
            try:
                self.current_task = self.queue.get(timeout=1)
                self.free = False
                self.current_task.worker = self
                self.current_task.run()
                self.current_task.worker = None
                self.current_task = None
                self.queue.task_done()
                self.free = True
            except queue.Empty:
                pass
            except KeyboardInterrupt:
                pass
class ParallelHost():
    def __init__(self, initial_threads=32, max_threads=16384, grow_speed=32, grow_thresh=16, recycle_thresh=64, watch_dog_interval=10):
        self.initial_threads = initial_threads
        self.max_threads = max_threads
        self.grow_thresh = grow_thresh
        self.grow_speed = grow_speed
        self.recycle_thresh = recycle_thresh
        self.workers = []
        self.tasks = queue.Queue()
        self.id = 0
        self.lock = threading.Lock()
        for i in range(self.initial_threads):
            worker = Worker(self.tasks)
            self.workers.append(worker)
        for worker in self.workers:
            worker.start()

        self.add_job(
            self.watch_dog,
            kwargs={"running_interval":watch_dog_interval},
            name="watchdog"
        )

    def join(self, timeout=None):
        self.tasks.join() # wait for all job finish.
        for worker in self.workers:
            worker.stop()
            worker.join(timeout)

    def watch_dog(self, running_interval=10):
        while True:
            # sleep running_interval time.
            time.sleep(running_interval)

            num_free, num_busy, num_all = self.status()

            # create new threads if not enough
            if num_free < self.grow_thresh:
                num_new = self.grow_speed
                if num_all + num_new > self.max_threads:
                    num_new = self.max_threads - num_all

                hangged_task = self.tasks.qsize()
                if hangged_task > 0:
                    num_new = num_new if num_new > hangged_task else hangged_task
                for i in range(num_new):
                    worker = Worker(self.tasks)
                    worker.start()
                    self.workers.append(worker)

            # release free threads if already too much.
            if num_free > self.recycle_thresh:
                # recycle_num = int((num_free - self.recycle_thresh)*0.3)
                recycle_num = num_free - self.recycle_thresh
                recycled = 0

                # mark worker as terminated
                terminated = []
                for i, worker in enumerate(self.workers):
                    if worker.free:
                        worker.stop()
                        terminated.append(worker)
                        recycled += 1
                        if recycle_num <= recycled:
                            break
                # wait for all work that is really terminated.
                for worker in terminated:
                    worker.join()
                # delete all terminated worker.
                alive_workers = []
                for worker in self.workers:
                    if worker.is_alive():
                        alive_workers.append(worker)
                self.workers = alive_workers
                # num_workers = len(self.workers)
                # i = 0
                # while i < num_workers:
                #     if not self.workers[i].is_alive():
                #         del self.workers[i]
                #         num_workers -= 1
                #     else:
                #         i += 1

            # print('loop end.')
        print('watch dog exited.')

    def status(self):
        num_free = sum([1 if worker.free else 0 for worker in self.workers])
        num_all = len(self.workers)
        num_busy = num_all - num_free
        return num_free, num_busy, num_all

    def commit(self, job):
        self.lock.acquire()
        self.id += 1
        job.set_id(self.id)
        self.tasks.put(job)
        self.lock.release()
        return Future(job)

    def add_job(self, func, args=[], kwargs={}, name=None):
        job = Job(func, args, kwargs, name)
        return self.commit(job)

daemon = ParallelHost(watch_dog_interval=1.0)

if __name__ == '__main__':
    # host = ParallelHost()
    from logger import Logger
    logger = Logger('test.log')
    host = daemon
    def loop_print(info, num):
        for i in range(num):
            # print(info + ':' + str(i))
            time.sleep(1)
        return info

    def print_stat(daemon):
        num_free, num_busy, num_all = daemon.status()
        print('free: {0} | busy: {1} | all: {2}'.format(num_free, num_busy, num_all))

    print('Initial Status:', end=' ')
    print_stat(daemon)

    handler1 = host.add_job(loop_print, ["test_future_{0}".format(1), 4], name="test_future_{0}".format(1))
    handler2 = host.add_job(loop_print, ["test_future_{0}".format(2), 6], name="test_future_{0}".format(2))
    print('Result for job 1:', handler1.resolve())
    print('Result for job 2:', handler2.resolve())


    print('Commiting 32 long-time job...')
    for i in range(32):
        host.add_job(loop_print, ["loop_print_{0}".format(i), 50000], name="loop_print_{0}".format(i))

    time.sleep(3)
    print('Current Status:', end=' ')
    print_stat(daemon)

    def brust_job(number):
        print('Commiting {0} short-time job...'.format(number))
        start_time = time.time()
        handlers = []
        for i in range(number):
            handler = host.add_job(loop_print, ["loop_print_{0}".format(i), 5], name="loop_print_{0}".format(i))
            handlers.append(handler)

        print('Waiting for job done.')
        for handler in handlers:
            handler.resolve()
        print('{0} short_job which taken 5s for each finished at {1} s'.format(number, time.time()-start_time))

    brust_job(2000)
    brust_job(4000)
    brust_job(5000)
    brust_job(1000)
    time.sleep(10)
    brust_job(5000)
    time.sleep(10)
    brust_job(100)

    for i in range(10):
        print('Current Status:', end=' ')
        print_stat(daemon)
        time.sleep(0.5)


    # time.sleep(10)
    # host.terminate('kill')
