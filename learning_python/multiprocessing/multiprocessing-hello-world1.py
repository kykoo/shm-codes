#!/usr/bin/python3

import multiprocessing

def worker(i):
    """worker function"""
    print('worker {}'.format(i))
    return

if __name__ == '__main__':
    jobs = []
    for i in range(5):
        p = multiprocessing.Process(target=worker,args=(i,))
        jobs.append(p)
        p.start()
        
