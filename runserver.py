import queue
import subprocess
import threading
import time


class Runserver:

    outq = None

    def __init__(self):
        self.pid = None
        self.proc = None
        self.outq = queue.Queue()
        self.has_terminated = threading.Event()

    def output_reader(self):
        print('output_reader starting')
        for line in iter(self.proc.stdout.readline, ''):
            # print(f'read {line}')
            self.outq.put(line)

    def process_poller(self):
        print('process_poller starting')
        while True:
            if self.proc.poll() is not None:
                print('process has terminated!')
                self.has_terminated.set()
                break
            time.sleep(0.05)

    def start(self, args=[]):
        print(f'spawning {" ".join(args)}')
        self.proc = subprocess.Popen(args,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     encoding='utf-8')
        print(f'proc spawned with pid {self.proc.pid}')
        self.reader_thread = threading.Thread(target=self.output_reader)
        self.reader_thread.start()
        self.poller_thread = threading.Thread(target=self.process_poller)
        self.poller_thread.start()
        time.sleep(0.1)

    def write(self, message):
        if self.has_terminated.is_set():
            return
        print(f' => {message}')
        self.proc.stdin.write(message + '\n')
        self.proc.stdin.flush()
        time.sleep(0.1)

    def read(self):
        try:
            line = self.outq.get(block=False)
            print(f' <= {line.rstrip()}')
            return line
        except queue.Empty:
            return None

    def stop(self):
        print('terminating')
        if not self.has_terminated.is_set():
            self.proc.terminate()
        self.reader_thread.join()
        self.poller_thread.join()


if __name__ == '__main__':

    r = Runserver()
    r.start(['bc', '-i'])

    while (r.read() is not None):
        pass

    r.write('1 + 2')
    print(r.read())

    r.write('quit')
    r.write('3 + 4')
    print(r.read())

    r.stop()
