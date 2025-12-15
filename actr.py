"""
This file implements a connection to the ACT-R remote interface
and defines functions which can call the ACT-R commands that are
used in the tasks from the ACT-R tutorial.

The call_command function can be used to call ACT-R commands
for which a corresponding function has not been provided.

It is not "the" ACT-R interface in Python.  It is only an interface
which is sufficient for using the ACT-R tutorial tasks from Python.

There are some assumptions about how the connection is implemented
and processed which may not be suitable for other purposes.  Also,
a simpler interface may be more useful in other cases when speed of
operation is important.

There is an example of a simpler interface that implements only a 
specific set of commands being made available to ACT-R in the file:

examples/creating-modules/external/goal_complete.py

There are of course many other ways one could also handle the
communication process.

"""

import json
import threading
import socket
import time
import os
import sys
import __main__
import importlib

class request():
    def __init__(self,id):
        self.id = id
        self.lock = threading.Lock()
        self.cv = threading.Condition(self.lock)
        self.complete = False

    def notify_result(self):
        self.cv.acquire()
        self.complete = True
        self.cv.notify()
        self.cv.release()


locals = threading.local()

class actr():
    
    def __init__(self,host,port):
        self.interface = interface(host, port)
        if self.interface.connected :
            self.interface.echo_output()

    def evaluate (self, *params):
        
        try:
            m = locals.model_name
        except AttributeError:
            m = False
     
        p = list(params)

        p.insert(1,m)    

        r = self.interface.send ("evaluate", *p)
        
        if r[0] == False:
            print("Error evaluating",p[0],": ",end="")

            for e in r[1:]:
                print (e)

            return False
        else:
            return r[1:]

    def evaluate_single(self,*params):
        r = self.evaluate(*params)

        if r:
            return r[0]
        else:
            return False

    def add_command(self,name,function,documentation="No documentation provided.",single=True,actr_name=None,encoded=False):
        if name in self.interface.commands.keys():
            if self.interface.commands[name] == function:
                print("Command ",name," already exists for function ",function)
            else:
                print("Command ",name," already exists and is now being replaced by ",function)
                self.interface.add_command(name,function)
 
        existing = self.interface.send("check",name)

        if function :
            call_name = name
        else:
            call_name = None

        if existing[0] == True:
            if existing[1] == None:
                result = self.interface.send("add",name,call_name,documentation,single,actr_name,encoded)
                if result[0]:
                    self.interface.add_command(name,function)
                    return result[1]
                else:
                    print(result[1])
                    return False
            elif existing[2] == None:
                print("Cannot add command ",name, " because it has already been added by a different owner.")
                return False
            else:
                return True
        
        else:
            print("Invalid command name ",name," cannot be added.")
            return False




    def monitor_command(self,original,monitor):
        r = self.interface.send("monitor",original,monitor)

        if r[0] == False:
            for e in r[1:]:
                print (e)

            return False
        else:
            return r[1:]

 
    def remove_command_monitor(self,original,monitor):
        r = self.interface.send("remove-monitor",original,monitor)

        if r[0] == False:
            for e in r[1:]:
                print (e)

            return False
        else:
            return r[1:]       

    def remove_command(self,name):
        if name not in self.interface.commands.keys():
            r = self.interface.send('remove',name)

            if r[0] == False:
                for e in r[1:]:
                    print (e)

                return False
            else:
                return True

        else:
            del self.interface.commands[name]
            r = self.interface.send("remove",name)
            
            if r[0] == False:
                for e in r[1:]:
                    print (e)

                return False
            else:
                return True

    def current_model():
        try:
            m = locals.model_name
        except AttributeError:
            m = self.evaluate_single('current-model')
        return m

    def set_current_model(name):
        if name.lower() in (x.lower() for x in mp_models()):
            locals.model_name = name
        else:
            print("%s is not one of the currently available models: %s"%(name,mp_models()))


    def reset (self,):
        return self.evaluate_single("reset")

    def reload (self,compile=False):
        return self.evaluate_single("reload",compile)

    def run (self,time, real_time=False):
        return self.evaluate("run", time, real_time)

    def run_full_time (self,time, real_time=False):
        return self.evaluate("run-full-time", time, real_time)

    def run_until_time (self,time, real_time=False):
        return self.evaluate("run-until-time", time, real_time)

    def run_n_events (self,event_count, real_time=False):
        return self.evaluate("run-n-events", event_count, real_time)

    def run_until_condition(self,condition,real_time=False):
        return self.evaluate("run-until-condition", condition, real_time)

    def buffer_chunk (self,*params):
        return self.evaluate_single("buffer-chunk", *params)

    def whynot (self,*params):
        return self.evaluate_single("whynot", *params)

    def whynot_dm (self,*params):
        return self.evaluate_single("whynot-dm", *params)


    def penable (self,*params):
        return self.evaluate_single("penable", *params)

    def pdisable (self,*params):
        return self.evaluate_single("pdisable", *params)

    def load_act_r_model (self,path):
        return self.evaluate_single("load-act-r-model",path)

    def load_act_r_code (self,path):
        return self.evaluate_single("load-act-r-code",path)

    def goal_focus (self,goal=None):
        return self.evaluate_single("goal-focus",goal)

    def clear_exp_window(self,win=None):
        return self.evaluate_single("clear-exp-window",win)


    def open_exp_window(self,title,visible=True,width=300,height=300,x=300,y=300):
        return self.evaluate_single("open-exp-window", title, [["visible", visible], ["width", width],
                                                                             ["height", height], ["x", x], ["y", y]])

    def add_text_to_exp_window(self,window,text,x=0,y=0,color='black',height=20,width=75,font_size=12):
        return self.evaluate_single("add-text-to-exp-window", window, text,[["color", color], ["width", width],
                                                                                          ["height", height], ["x", x], ["y", y], 
                                                                                          ["font-size", font_size]])

    def add_button_to_exp_window(self,window,text="",x=0,y=0,action=None,height=20,width=75,color='gray'):
        return self.evaluate_single("add-button-to-exp-window",window,[["color", color], ["width", width],
                                                                                     ["height", height], ["x", x], ["y", y], 
                                                                                     ["text", text], ["action", action]])

    def remove_items_from_exp_window(self,window,*items):
        return self.evaluate_single("remove-items-from-exp-window",window,*items)


    def install_device(self,device):
        return self.evaluate_single("install-device",device)

    def print_warning(self,warning):
        self.evaluate("print-warning",warning)

    def act_r_output(self,output):
        self.evaluate("act-r-output",output)

    def random(vself,alue):
        return self.evaluate_single("act-r-random",value)


#     def add_command(self,name,function=None,documentation="No documentation provided.",single=True,local_name=None,encoded=False):
#         return self.add_command(name,function,documentation,single,local_name,encoded)

#     def monitor_command(self,original,monitor):
#         return self.monitor_command(original,monitor)

#     def remove_command_monitor(self,original,monitor):
#         return self.remove_command_monitor(original,monitor)

#     def remove_command(self,name):
#         return self.remove_command(name)

    def print_visicon(self,):
        return self.evaluate_single("print-visicon")

    def mean_deviation(self,results,data,output=True):
        return self.evaluate_single("mean-deviation",results,data,output)

    def correlation(self,results,data,output=True):
        return self.evaluate_single("correlation",results,data,output)

    def get_time(self,model_time=True):
        return self.evaluate_single("get-time",model_time)

    def buffer_status (self,*params):
        return self.evaluate_single("buffer-status", *params)

    def buffer_read (self,buffer):
        return self.evaluate_single("buffer-read", buffer)

    def clear_buffer (self,buffer):
        return self.evaluate_single("clear-buffer", buffer)

    def new_tone_sound (self,freq, duration, onset=False, time_in_ms=False):
        return self.evaluate_single("new-tone-sound", freq, duration, onset, time_in_ms)

    def new_word_sound (self,word, onset=False, location='external', time_in_ms=False):
        return self.evaluate_single("new-word-sound", word, onset, location, time_in_ms)

    def new_digit_sound (self,digit, onset=False, time_in_ms=False):
        return self.evaluate_single("new-digit-sound", digit, onset, time_in_ms)

    def define_chunks (self,*chunks):
        return self.evaluate_single("define-chunks", *chunks)

    def define_chunks_fct (self,chunks):
        return self.evaluate_single("define-chunks", *chunks)

    def add_dm (self,*chunks):
        return self.evaluate_single("add-dm", *chunks)

    def add_dm_fct (self,chunks):
        return self.evaluate_single("add-dm-fct", chunks)

    def pprint_chunks (self,*chunks):
        return self.evaluate_single("pprint-chunks", *chunks)

    def chunk_slot_value (self,chunk_name, slot_name):
        return self.evaluate_single("chunk-slot-value", chunk_name, slot_name)

    def buffer_slot_value (self,buffer_name, slot_name):
        return self.evaluate_single("buffer-slot-value", buffer_name, slot_name)

    def set_chunk_slot_value (self,chunk_name, slot_name, new_value):
        return self.evaluate_single("set-chunk-slot-value", chunk_name, slot_name, new_value)

    def mod_chunk (self,chunk_name, *mods):
        return self.evaluate_single("mod-chunk", chunk_name, *mods)

    def mod_focus (self,*mods):
        return self.evaluate_single("mod-focus", *mods)

    def chunk_p (self,chunk_name):
        return self.evaluate_single("chunk-p",chunk_name)

    def copy_chunk (self,chunk_name):
        return self.evaluate_single("copy-chunk",chunk_name)

    def extend_possible_slots (self,slot_name, warn=True):
        return self.evaluate_single("extend-possible-slots",slot_name,warn)

    def model_output (self,output_string):
        return self.evaluate_single("model-output",output_string)


    def set_buffer_chunk (self,buffer_name, chunk_name, requested=True):
        return self.evaluate_single("set-buffer-chunk",buffer_name,chunk_name,requested)

    def add_line_to_exp_window (self,window, start, end, color = False):
        if color:
            return self.evaluate_single("add-line-to-exp-window",window,start,end,color)
        else:
            return self.evaluate_single("add-line-to-exp-window",window,start,end)

    def modify_line_for_exp_window (self,line, start, end, color = False):
        if color:
            return self.evaluate_single("modify-line-for-exp-window",line,start,end,color)
        else:
            return self.evaluate_single("modify-line-for-exp-window",line,start,end)

    def start_hand_at_mouse (self,):
        return self.evaluate_single("start-hand-at-mouse")

    def schedule_event (self,time, action, params=None, module=':NONE', priority=0, maintenance=False, destination=None, details=None,output=True,time_in_ms=False,precondition=None):
        return self.evaluate_single("schedule-event",time,action,[["params", params],["module", module],
                                                                                ["priority", priority],["maintenance", maintenance],
                                                                                ["destination", destination], ["details", details],
                                                                                ["output", output],["time-in-ms", time_in_ms],
                                                                                ["precondition", precondition]])

    def schedule_event_now (self,action, params=None, module=':NONE', priority=0, maintenance=False, destination=None, details=None,output=True,precondition=None):
        return self.evaluate_single("schedule-event-now",action,[["params", params],["module", module],
                                                                                       ["priority", priority],["maintenance", maintenance],
                                                                                       ["destination", destination], ["details", details],
                                                                                       ["output", output], ["precondition", precondition]])

    def schedule_event_relative (self,time_delay, action, params=None, module=':NONE', priority=0, maintenance=False, destination=None, details=None,output=True,time_in_ms=False,precondition=None):
        return self.evaluate_single("schedule-event-relative",time_delay,action,[["params", params],["module", module],
                                                                            ["priority", priority],["maintenance", maintenance],
                                                                            ["destination", destination], ["details", details],
                                                                            ["output", output],["time-in-ms", time_in_ms],
                                                                            ["precondition", precondition]])

    def schedule_event_after_module (self,after_module, action, params=None, module=':NONE', maintenance=False, destination=None, details=None, output=True, precondition=None, dynamic=False, delay=True, include_maintenance=False):
        return self.evaluate("schedule-event-after-module",after_module,action,[["params", params],["module", module],
                                                                            ["maintenance", maintenance],
                                                                            ["destination", destination], ["details", details],
                                                                            ["output", output],["delay", delay], ["dynamic", dynamic],
                                                                            ["precondition", precondition],["include-maintenance", include_maintenance]])


    def schedule_break_relative (self,time_delay,time_in_ms=False, priority=":max", details=None):
        return self.evaluate_single("schedule-break-relative",time_delay,[["time-in-ms", time_in_ms],["priority", priority],["details",details]])

    def mp_show_queue(self,indicate_traced=False):
        return self.evaluate_single("mp-show-queue",indicate_traced)

    def print_dm_finsts(self,):
        return self.evaluate_single("print-dm-finsts")

    def spp (self,*params):
        return self.evaluate_single("spp", *params)

    def mp_models(self,):
        return self.evaluate_single("mp-models")

    def all_productions(self,):
        return self.evaluate_single("all-productions")

    def buffers(self,):
        return self.evaluate_single("buffers")

    def printed_visicon(self,):
        return self.evaluate_single("printed-visicon")

    def print_audicon(self,):
        return self.evaluate_single("print-audicon")

    def printed_audicon(self,):
        return self.evaluate_single("printed-audicon")

    def printed_parameter_details(self,param):
        return self.evaluate_single("printed-parameter-details",param)

    def sorted_module_names(self,):
        return self.evaluate_single("sorted-module-names")

    def modules_parameters(self,module):
        return self.evaluate_single("modules-parameters",module)

    def modules_with_parameters(self,):
        return self.evaluate_single("modules-with-parameters")

    def used_production_buffers(self,):
        return self.evaluate_single("used-production-buffers")

    def record_history(self,*params):
        return self.evaluate_single("record-history",*params)

    def stop_recording_history(self,*params):
        return self.evaluate_single("stop-recording-history",*params)

    def get_history_data(self,history,*params):
        return self.evaluate_single("get-history-data",history,*params)

    def history_data_available(self,history,file=False,*params):
        return self.evaluate_single("history-data-available",history,file,*params)

    def process_history_data(self,processor,file=False,data_params=None,processor_params=None):
        return self.evaluate_single("process-history-data",processor,file,data_params,processor_params)

    def save_history_data(self,history,file,comment="",*params):
        return self.evaluate_single("save-history-data",history,file,comment,*params)


    def dm (self,*params):
        return self.evaluate_single("dm", *params)

    def sdm (self,*params):
        return self.evaluate_single("sdm", *params)


    def get_parameter_value(self,param):
        return self.evaluate_single("get-parameter-value",param)

    def set_parameter_value(self,param,value):
        return self.evaluate_single("set-parameter-value",param,value)


    def get_system_parameter_value(self,param):
        return self.evaluate_single("get-system-parameter-value",param)

    def set_system_parameter_value(self,param,value):
        return self.evaluate_single("set-system-parameter-value",param,value)


    def sdp (self,*params):
        return self.evaluate_single("sdp", *params)


    def simulate_retrieval_request (self,*spec):
        return self.evaluate_single("simulate-retrieval-request", *spec)

    def saved_activation_history (self,):
        return self.evaluate_single("saved-activation-history")

    def print_activation_trace (self,time, ms = True):
        return self.evaluate_single("print-activation-trace",time,ms)

    def print_chunk_activation_trace (self,chunk, time, ms = True):
        return self.evaluate_single("print-chunk-activation-trace",chunk,time,ms)

    def pp (self,*params):
        return self.evaluate_single("pp", *params)

    def trigger_reward(self,reward,maintenance=False):
        return self.evaluate_single("trigger-reward",reward,maintenance)


    def define_chunk_spec (self,*spec):
        return self.evaluate_single("define-chunk-spec", *spec)

    def chunk_spec_to_chunk_def(self,spec_id):
        return self.evaluate_single("chunk-spec-to-chunk-def", spec_id)

    def release_chunk_spec(self,spec_id):
        return self.evaluate_single("release-chunk-spec-id", spec_id)



    def schedule_simple_set_buffer_chunk (self,buffer, chunk, time, module='NONE', priority=0, requested=True):
        return self.evaluate_single("schedule-simple-set-buffer-chunk",buffer,chunk,time,module,priority,requested)

    def schedule_simple_mod_buffer_chunk (self,buffer, mod_list_or_spec, time, module='NONE', priority=0):
        return self.evaluate_single("schedule-simple-mod-buffer-chunk",buffer,mod_list_or_spec,time,module,priority)


    def schedule_set_buffer_chunk (self,buffer, chunk, time, module=':NONE', priority=0, output='low',time_in_ms=False,requested=True):
        return self.evaluate_single("schedule-set-buffer-chunk",buffer,chunk,time,[["module", module],
                                                                            ["priority", priority],["output", output],["time-in-ms", time_in_ms],
                                                                            ["requested", requested]])

    def schedule_mod_buffer_chunk (self,buffer, mod_list_or_spec, time, module=':NONE', priority=0, output='low',time_in_ms=False):
        return self.evaluate_single("schedule-mod-buffer-chunk",buffer,mod_list_or_spec,time,[["module", module],
                                                                            ["priority", priority],["output", output],["time-in-ms", time_in_ms]])


    def undefine_module(self,name):
        return self.evaluate_single("undefine-module", name)


    def delete_chunk(self,name):
        return self.evaluate_single("delete-chunk", name)

    def purge_chunk(self,name):
        return self.evaluate_single("purge-chunk", name)



    def define_module (self,name, buffers,params,interface=None):
        return self.evaluate_single("define-module", name, buffers, params, interface)


    def command_output(self,string):
        return self.evaluate_single("command-output",string)

    def chunk_copied_from(self,chunk_name):
        return self.evaluate_single("chunk-copied-from",chunk_name)


    def mp_time (self,):
        return self.evaluate_single("mp-time")

    def mp_time_ms (self,):
        return self.evaluate_single("mp-time-ms")

    def predict_bold_response(self,start=None,end=None,output=None):
        if start == None:
            return self.evaluate_single("predict-bold-response")
        elif end == None:
            return self.evaluate_single("predict-bold-response", start)
        elif output == None:
            return self.evaluate_single("predict-bold-response", start, end)
        else:
            return self.evaluate_single("predict-bold-response", start, end, output)

    def pbreak (self,*params):
        return self.evaluate_single("pbreak", *params)

    def punbreak (self,*params):
        return self.evaluate_single("punbreak", *params)

    def create_image_for_exp_window(self,window,text,file,x=0,y=0,width=50,height=50,action=None,clickable=True):
        return self.evaluate_single("create-image-for-exp-window", window, text, file,
                                                  [['x', x],['y', y],['width', width],['height', height],['action', action],['clickable',clickable]])

    def add_image_to_exp_window(self,window,text,file,x=0,y=0,width=50,height=50,action=None,clickable=True):
        return self.evaluate_single("add-image-to-exp-window", window, text, file,
                                                  [['x', x],['y', y],['width', width],['height', height],['action', action],['clickable',clickable]])

    def add_items_to_exp_window(self,window, *items):
        return self.evaluate_single("add-items-to-exp-window",window, *items)


    def add_visicon_features(self,*features):
        return self.evaluate_single("add-visicon-features",*features)

    def delete_visicon_features(self,*features):
        return self.evaluate_single("delete-visicon-features",*features)

    def delete_all_visicon_features(self,):
        return self.evaluate_single("delete-all-visicon-features")

    def modify_visicon_features(self,*features):
        return self.evaluate_single("modify-visicon-features",*features)

    def running(self,):
        return self.evaluate_single("act-r-running-p")


    def stop_output(self,):
        self.interface.no_output()

    def resume_output(self,):
        self.interface.echo_output()

    def hide_output(self,):
        self.interface.show_output = False

    def unhide_output(self,):
        self.interface.show_output = True


    def no_output(self,command,*params):
        return self.evaluate_single("no-output",command,*params)


    def visible_virtuals_available(self,):
        return self.evaluate_single("visible-virtuals-available?")

    def process_events(self,):
        time.sleep(0)

    def permute_list(self,l):

        indexes = list(range(len(l)))
        new_indexes = self.evaluate_single("permute-list",indexes)
        result = []
        for i in new_indexes:
            result.append(l[i])
        return result

    def call_command(self,command,*parameters):
        return self.evaluate_single(command,*parameters)


def start(host,port):
    try:
        a = actr(host=host,port=port)
    except:
        print("Failed to connect to ACT-R with exception",sys.exc_info())

    if a.interface.connected :
        a.interface.send("set-name","ACT-R Tutorial Python interface")
        return a
    else:
        print("ACT-R connection NOT established, but no exception detected or already handled.")


def stop(c):
    print("Closing down ACT-R connection.")
    c.interface.connected = False
    c.interface.sock.close()
    c = None

class interface():
    def __init__(self,host,port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:

            self.sock.connect((host, port))
        except:
            self.connected = False
            print("Error trying to connect to ACT-R at",host,":",port,"with exception",sys.exc_info())
        else:
            self.connected = True
            self.cmd_id = 1
            self.actions = {}
            self.stream_lock = threading.Lock() 
            self.buffer = []
            self.commands = {}
            self.data_collector = threading.Thread(target=self.collect_data)
            self.data_collector.daemon = True
            self.data_collector.start()       
            self.id_lock = threading.Lock()
            self.echo_count = 0
            self.echo = False
            self.show_output = True

    def send(self,method,*params):
        d = {}
        r = request(self.cmd_id)
        self.actions[self.cmd_id] = r

        d['method'] = method
        self.id_lock.acquire()
        d['id'] = self.cmd_id
        self.cmd_id += 1
        self.id_lock.release()
        d['params'] = params
        
        message = json.dumps(d) + chr(4)
        
        r.lock.acquire()
        
        self.stream_lock.acquire()
        self.sock.sendall(message.encode('utf-8'))
        self.stream_lock.release()
        
        while not r.complete:
          r.cv.wait()

        return [r.success] + r.results


    def add_command(self,name,function):
        self.commands[name] = function

    def collect_data(self):
        buffer= ''
        c = True
        while c:
            try:
                data = self.sock.recv(4096)
                buffer += data.decode('utf-8')
                while not chr(4) in buffer:
                    data = self.sock.recv(4096)
                    buffer += data.decode('utf-8')
                while chr(4) in buffer:
                    pos = buffer.find(chr(4))
                    message = buffer[0:pos]
                    pos += 1
                    buffer = buffer[pos:]
                    self.process_message(json.loads(message))
            except:
                if self.connected:
                    print("ACT-R connection error connection no longer available.")
                c = False

    def process_message (self,d):
        if 'result' in d.keys():
            id =d['id']
            r = self.actions[id]
            if d['error'] is None:
                r.success = True
                r.results = d['result']
            else:
                r.success = False
                errors=d['error']
                r.results = [errors['message']]

            self.actions.pop(id,None)
            r.notify_result()
        else:
            if d['method'] == "evaluate" and d['params'][0] in self.commands.keys():
                thread = threading.Thread(target=self.run_command,args=[self.commands[d['params'][0]],d['params'][0],d['params'][1],d['id'],d['params'][2:]])
                thread.daemon = True
                thread.start()
            else:
                f={}
                f['id'] = d['id']
                f['result'] = None
                e={}
                e['message'] = "Invalid method name" + d['params'][0]
                f['error'] = e
                message = json.dumps(f) + chr(4)
                self.stream_lock.acquire()
                self.sock.sendall(message.encode('utf-8'))
                self.stream_lock.release()

    def run_command (self,command,command_name,model,id,params):

        locals.model_name = model

        try:
            if command:
                if params == None:
                    result = command()
                else:
                    result = command(*params)
            else:
                result = True
        except:
            error = True
            problem = sys.exc_info()
        else:
            error = None

        f={}
        f['id'] = id

        if error:
            f['result'] = None
            f['error'] = {'message': "Error %s while evaluating a command in Python for command: %s, model: %s, parameters: %s"%(problem,command_name,model,params)}

        elif ((result is False) or (result is None)):

            f['result']= [None]
            f['error']= None

        else:
            if isinstance(result,tuple):
                f['result']= result
            else:
                f['result']= [result]
            f['error']= None

        message = json.dumps(f) + chr(4)
        self.stream_lock.acquire()
        self.sock.sendall(message.encode('utf-8'))
        self.stream_lock.release()
        
    def output_monitor(self,string):
        if self.show_output:
            print(string.rstrip())
        return True

    def echo_output(self):
        if not(self.echo): 
            if 'echo' not in self.commands.keys():
                self.add_command("echo",self.output_monitor)

            ready = False

            while not(ready):
                existing = self.send("check",'python-echo'+str(self.echo_count))

                if existing[1] == None:
                    self.send("add","python-echo"+str(self.echo_count),"echo","Trace monitor for python client.  Do not call directly.",True)
                    ready = True
                else:
                    self.echo_count += 1

        
            self.send("monitor","model-trace","python-echo"+str(self.echo_count))
            self.send("monitor","command-trace","python-echo"+str(self.echo_count))
            self.send("monitor","warning-trace","python-echo"+str(self.echo_count))
            self.send("monitor","general-trace","python-echo"+str(self.echo_count))
            self.echo = True
            return True

        else:
            print("echo_output called when output was already on.")
            return False

    def no_output(self):
    
        if self.echo:
            self.send("remove-monitor","model-trace","python-echo"+str(self.echo_count))
            self.send("remove-monitor","command-trace","python-echo"+str(self.echo_count))
            self.send("remove-monitor","warning-trace","python-echo"+str(self.echo_count))
            self.send("remove-monitor","general-trace","python-echo"+str(self.echo_count))
            self.send("remove","python-echo"+str(self.echo_count))
            self.echo = False
        else:
            print("no_output called when output was already off.")




def import_from_path(fullpath):
    """ 
    Import a file with full path specification. Allows one to
    import from anywhere, something __import__ does not do. 
    Will reload the module if it already exists in sys.modules.
    """
    path, filename = os.path.split(fullpath)
    filename, ext = os.path.splitext(filename)
    module = ''

    if ext == '.py':
    
        try:
            if filename in sys.modules:
                module = importlib.reload(sys.modules[filename])
            else:
                sys.path.insert(0, path)
                module = __import__(filename)
                del sys.path[0]
            return module
        except:
            return(str(sys.exc_info()[1]))
    else:
        return False


def env_loader(path):
    """
    Ugly solution to something probably not necessary,
    but seems some novice ACT-R users that wanted to use
    Python wanted to use the 'load ACT-R code' button for
    the Python files too.  So, this provides a way that
    such a button could be implemented and make the module
    available directly from the interactive prompt from which
    actr was imported so that it would still match the tutorial
    descriptions.
    """
    global __main__  

    try:
        module=import_from_path(path)
     
        if type(module) == str:
            return module
        elif module:
            setattr(__main__,module.__name__,module)
            return True
        else:
            return "Only a .py file can be imported"
    except:
      print("Problem with trying to import from ",path)
      print(sys.exc_info())
      return str(sys.exc_info()[1])


from pathlib import Path

starting_dir = Path(__file__).parent.absolute()

def env_loader_no_path(file):
    """
    Add the current file's path to the file name given and then
    pass it off to env_loader
    """

    return(env_loader(starting_dir.joinpath(file)))


# add_command("Python-import-from-file",env_loader,"Import a Python module and make it available directly from the interactive prompt. Params: pathname")
    
# add_command("load-python-module-html",env_loader_no_path,"Import a python module from the directory containing the actr.py module and make it available directly from the interactive prompt. Params: filename")


"""
07/31/2025
This is a patch to change the way that output from background threads
in Jupyter is displayed.  In newer versions of Jupyter all of the output
from a background thread goes to the cell where the thread is running.
In older versions it went to whatever cell was last executed, which
works better for seeing the output from running a model or calling an
ACT-R command -- it shows up where it is run.

This patch depends upon the internal details of the ipykernel.iostream.OutStream
class to determine if it has the newer output mechanism and to change how
it operates.  Therefore it may not work with future updates to the ipykernel.

If you want all of the ACT-R output to go to the single cell where the
connection is initiated, then you can comment this out to prevent the
change.
"""


try:
    __IPYTHON__
    in_jupyter = True
except NameError:
    in_jupyter = False

if in_jupyter:
    import ipykernel.iostream

    if hasattr(ipykernel.iostream.OutStream,"_flush_buffers") and not hasattr(ipykernel.iostream.OutStream,"_ACTR_hack"):
        # The old mechanism just had a parent_header attribute
        # that was changed, but the new one has a property to
        # replace that to get the new operation.  The "fix" is
        # to just replace the property attributes of the class
        # so that it works like the old one.
        # The _flush_buffers method was added with the threaded
        # output change so that's a test to see if it needs to be
        # patched. 

        ipykernel.iostream.OutStream._ACTR_hack = True

        def hack_cell_getter(self):
            return self._parent_header_global

        def hack_cell_setter(self,value):
            self._parent_header_global = value
            return self._parent_header_global

        ipykernel.iostream.OutStream.parent_header = ipykernel.iostream.OutStream.parent_header.setter(hack_cell_setter)
        ipykernel.iostream.OutStream.parent_header = ipykernel.iostream.OutStream.parent_header.getter(hack_cell_getter)
