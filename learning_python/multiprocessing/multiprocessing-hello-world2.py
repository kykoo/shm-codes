#!/usr/bin/python3

import multiprocessing
import multiprocessing_import_worker


if __name__ == '__main__':
    jobs = []
    for i in range(5):
        p = multiprocessing.Process(target=multiprocessing_import_worker.worker,args=(i,))
        jobs.append(p)
        p.start()
        
