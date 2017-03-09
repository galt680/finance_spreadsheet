import re
import time

def flatten(container):
    '''flatten nested containers by iterating and recursing on the conatiner'''
    flattened_list  = []
    for thing in container:
        if isinstance(thing, (list,tuple)):
            for subthing in flatten(thing):
                flattened_list.append(subthing)
        else:
            flattened_list.append(thing)
    return flattened_list
    
    
def split_symbols(block_of_text):
    for sublist in range(len(block_of_text)):
        for block in block_of_text[sublist][0].splitlines():
            for individual_symbol in re.split(r''',|''',block):
                for syms in individual_symbol.split():
                    yield syms

                    
def time_dec(func):
    def timed(*args,**kwargs):
        ts = time.time()
        result = func(*args,**kwargs)
        te = time.time()
        print te - ts
        return result
    return timed  
    
