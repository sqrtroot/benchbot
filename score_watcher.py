from threading import Thread
from time import sleep
from consts import SCORE_DIRECTORY
from db import *
import json
import os
from bot import notify_bench_done

if os.name != 'nt':
    import inotify.adapters


class FileWatcher(Thread):
    @staticmethod
    @with_session
    def new_result(session: SessionT, result_file):
        print(f"Processing {result_file}")
        try:
            bench_id = int(os.path.basename(result_file))
        except ValueError:
            print("File naming convention is wrong")
            os.remove(result_file)
            return
        bench: Benchmark = session.query(Benchmark).filter(Benchmark.id == bench_id).first()
        if not bench:
            print(f"Non valid benchmark found for file {result_file}")
            os.remove(result_file)
            return
        if bench.error or bench.avg_time:
            print(f"This benchmark was already processed NANI")
            os.remove(result_file)
            return
        with open(result_file, 'r') as f:
            try:
                out = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding json {e}")
                return
        if err := out.get('error'):
            bench.error = err
        else:
            bench.avg_time = out.get('avg')
            bench.min_time = out.get('min')
            bench.max_time = out.get('max')
        print(bench.result_format())
        notify_bench_done(bench.contender_id, bench.challenge.name, bench.result_format())
        os.remove(result_file)

    def run_linux(self):
        for file in os.listdir(SCORE_DIRECTORY):
            self.new_result(result_file=f"{SCORE_DIRECTORY}/{file}")
        i = inotify.adapters.Inotify()
        i.add_watch(SCORE_DIRECTORY)
        while event := i.event_gen(yield_nones=False):
            (_, type_names, path, filename) = event
            if 'IN_CLOSE_WRITE' in type_names:
                self.new_result(result_file=f"{SCORE_DIRECTORY}/{filename}")


    def run_windows(self):
        while True:
            for file in os.listdir(SCORE_DIRECTORY):
                self.new_result(result_file=f"{SCORE_DIRECTORY}/{file}")
                sleep(2)

    def run(self):
        if os.name == 'nt':
            self.run_windows()
        else:
            self.run_linux()
