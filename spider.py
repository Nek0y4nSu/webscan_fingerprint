from email import header
from importlib import import_module
import json
import threading
import requests
import queue
import os
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

proxies = {
  "http": "http://127.0.0.1:1080",
  "https": "http://127.0.0.1:1080",
}
q = queue.Queue()
thread_list  = []
finished_list = []
MAX_THREAD_NUM = 50


class Target:
    def __init__(self,url:str,t_id:int) -> None:
        self.target_url = url
        self.t_id = t_id
        self.success_flag = False
        self.head = ""
        self.html_content = bytes()

def http_get(url:str)->tuple:
    headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"}
    head = ''
    try:
        r = requests.get(url=url,headers=headers,proxies=proxies,verify=False,timeout=5)
        for k in r.headers.keys():
            head += "{}: {}\n".format(k, r.headers[k])
        return (r.content,head)
    except BaseException as e:
        return False


def get_content_loop():
    while q.empty() == False:
        try:
            target = q.get(block=False,timeout=2)
        except BaseException as e:
            continue
        
        print("[+]Get url: %s,id: %d " % (target.target_url,target.t_id))
        _r = http_get(target.target_url)
        if _r == False:
            finished_list.append(target)
            continue
        
        target.success_flag = True
        target.html_content = _r[0]
        target.head = _r[1]

        finished_list.append(target)
    
    print("[-]Thread exit")
        
if __name__ == "__main__":
    ##start
    start_time = time.time()

    #load url from txt file
    #split by line
    url_list = []
    try: 
        f = open("url.txt",'r')
        for line in f.readlines():
            line=line.strip('\n')
            url_list.append(line)
    except BaseException as e:
        print(e)
        os._exit(0)

    i = 0
    for u in url_list:
        target = Target(u,i)
        q.put(target)
        i += 1
    
    print("[+]Load %d url for file" %q.qsize())
    print("[+]start threads...")
    for i in range(0,MAX_THREAD_NUM):
        t = threading.Thread(target=get_content_loop)
        thread_list.append(t)
        t.start()
    
    for t in thread_list:
        t.join()
        
    print("[*]All threads finished!")
    #save results to file
    result_list = []
    for x in finished_list:
        _r = {
            'id': x.t_id,
            'url': x.target_url,
            'success':x.success_flag,
            'head' :x.head
        }
        result_list.append(_r)
        with open("./html_data/%d.html" % x.t_id ,'wb') as f:
            f.write(x.html_content)
        
    json_text = json.dumps(result_list)
    with open("./html_data/result.json",'w') as f:
        f.write(json_text)

    end_time = time.time()
    print("Total: {:.2f} seconds".format(end_time - start_time))