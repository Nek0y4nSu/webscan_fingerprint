import os
import json
import re
import time
import multiprocessing


class HtmlParser:
    def __init__(self,html_text:str) -> None:
        self.html = html_text
        
    def get_title(self)->str:
        r = re.search("title([\s\S]*?)</title>",self.html)
        if r != None:
            return r.groups()[0]
        else:
            ''

    def get_body_content(self):
        r = re.search("<body([\s\S]*?)</body>",self.html)
        if r != None:
            return r.groups()[0]
        else:
            ''

class Rule:
    def __init__(self) -> None:
        self.name = ""
        self.matches = []
        self.condition = ""

    def load_from_json(self,json_path:str)->bool:
        try:
            f = open(json_path,'r')
            text = f.read()
            json_obj = json.loads(text)
            self.name = json_obj['name']
            self.matches = json_obj['matches']
            if 'condition' in json_obj:
                self.condition = json_obj['condition']
        except BaseException as e:
            print(e)
            return False
        finally:
            f.close()

        return True
    
    def match_content(self,headers:str,title:str,body:str)->tuple:
        result = []
        for m in self.matches:
            search_field = m['search']
            if 'text' in m:
                signature = m['text']
                if search_field == "headers":
                    if headers.find(signature) != -1:
                        result.append(True)
                    else:
                        result.append(False)

                if search_field == "title":
                    if title.find(signature) != -1:
                        result.append(True)
                    else:
                        result.append(False)

                if search_field == "body":
                    if body.find(signature) != -1:
                        result.append(True)
                    else:
                        result.append(False)

            if 'regexp' in m:
                pat = re.compile(m['regexp'])
                if search_field == "headers":
                    if re.search(pat,headers) != None:
                        result.append(True)
                    else:
                        result.append(False)

                if search_field == "title":
                    if re.search(pat,title) != None:
                        result.append(True)
                    else:
                        result.append(False)

                if search_field == "body":
                    if re.search(pat,body) != None:
                        result.append(True)
                    else:
                        result.append(False)
            
        if len(result) == len(self.matches):
            return tuple(result)
        else:
            raise Exception('[ERR] Match function error!')
        
    def result_with_exp(self,result:tuple)->bool:
        ####result = (False,True,True)
        exp_list = list(self.condition)
        ##check expression and result 
        count = 0
        for c in exp_list:
            if c.isdigit():
                count += 1
        if len(result) != count:
            raise Exception("[ERR] index in expression error!!")
        ##gen expression
        for i in range(0,len(exp_list)):
            if exp_list[i].isdigit():
                exp_list[i] = str(result[int(exp_list[i])])
        
        exp = ''.join(exp_list)
        #print(exp)
        r = eval(exp)
        return r

    def match(self,header,html_text:str)->bool:
        try:
            h = HtmlParser(html_text)
        except BaseException as e:
            return False

        r = self.match_content(header,'hget_title','hget_body_content')

        if self.condition == "":
            if True in r:
                return True
            else:
                return False
            
        if self.condition != "":
            return self.result_with_exp(r)

def load_rules(rules_dir:str)->list:
    rule_list = []
    for r_name in os.listdir(rules_dir):
        rule = Rule()
        if rule.load_from_json("./rules/%s" % r_name) == True:
            rule_list.append(rule)

    return rule_list


def match_all_rules(header:str,html_text:str,rules:list)->list:
    matched_names = []
    for rule in rules:
        ##print(rule.name)
        if rule.match(header,html_text):
            matched_names.append(rule.name)

    return matched_names

def match_loop_all_targets(q,r_list,rules):
    #Process loop 
    #get target from queue
    while q.empty() == False:
        try:
            target = q.get(block=False,timeout=0.5)
        except BaseException as e:
            continue

        result = ""
        tid = target['id']
        head = target['head']
        url  = target['url']
        start_time = time.time()
        try:
            with open("./html_data/%d.html" % tid,'rb') as f:
                html = f.read().decode()
            result = str(match_all_rules(head,html,rules))
        except BaseException as e:
            result = "ERROR"

        end_time = time.time()
        
        result = "ID:%d,url:%s \n %s ,time spend:%d \n\n" % (tid,url,result,end_time - start_time)
        print(result)
        r_list.append(result)

    print("[-]Target consumer: Process Exit..")


def main():
    ###start
    start_time = time.time()
    
    ##multi process manager
    mgr = multiprocessing.Manager()
    results_list = mgr.list()
    target_queue = mgr.Queue()
    ##laod all rules
    rules_list = load_rules("./rules/")
    print("[+] load rules: %d" % len(rules_list))
    ##load all targets from json file
    with open("./html_data/result.json",'r') as f:
        target_list = json.load(f)

    for target in target_list:
        target_queue.put(target)

    ##multi process task
    process_list = []
    for i in range(3):
        p = multiprocessing.Process(target=match_loop_all_targets,args=(target_queue,results_list,rules_list))
        p.start()
        process_list.append(p)

    for p in process_list:
        p.join()

    print('[*]All process done.')
    print("[*]results: %d" % len(results_list))
    ##save all results to file
    with open("./results.txt",'w') as f:
        f.writelines(results_list)
    ###end
    end_time = time.time()
    print("Time spend total: {:.2f} seconds".format(end_time - start_time))

if __name__ == "__main__":
    main()
