import time
from pyrfc3339 import parse
import os
import ast
import json

def do_fastcore_decode(obj):
    to_str_replace = str(obj).replace("\'", "\"")
    valid_dict = ast.literal_eval(to_str_replace)
    return json.dumps(valid_dict)

def do_time(string):
    return (int(round(time.mktime(parse(string).timetuple())) * 1000000000))

def do_string(string):
    return str(string).lower().replace(" ", "")

def do_parse(string):
    return string != "" and string is not None and string != "None"

def check_env_vars():
    keys = ("GHA_TOKEN","NEW_RELIC_API_KEY")
    keys_not_set = []

    for key in keys:
        if key not in os.environ:
            keys_not_set.append(key)
    else:
        pass

    if len(keys_not_set) > 0: 
        for key in keys_not_set:
            print(key + " not set")
        exit(1)

def grab_env_vars():
    # Grab list enviroment variables to set as span attributes
    try:
        atts = os.environ
        # # Remove unwanted/sensitive attributes
        for att in atts:
            if att.startswith('CONTEXT') | att.startswith('NEW_RELIC') | att.startswith('OTEL') | att.startswith('ACTIONS') | att.startswith('GHA_TOKEN') :
                atts.pop(att,None)

        # atts_to_remove=["OTEL_EXPORTER_OTEL_ENDPOINT"]
        # if "GLAB_ENVS_DROP" in os.environ:
        #     try:
        #         if os.getenv("GLAB_ENVS_DROP") != "": 
        #             user_envs_to_drop =str(os.getenv("GLAB_ENVS_DROP")).split(",")
        #             for attribute in user_envs_to_drop:
        #                 atts_to_remove.append(attribute)
        #     except:
        #         print("Unable to parse GLAB_ENVS_DROP, check your configuration")
                
        # for item in atts_to_remove:
        #     atts.pop(item, None)      
        
    except Exception as e:
        print(e)

    return atts

def parse_attributes(obj,att_to_drop):
    obj_atts = {}
    attributes_to_drop = [att_to_drop]
    if "GHA_ATTRIBUTES_DROP" in os.environ:
        try:
            if os.getenv("GHA_ATTRIBUTES_DROP") != "": 
                user_attributes_to_drop =str(os.getenv("GHA_ATTRIBUTES_DROP")).lower().split(",")
                for attribute in user_attributes_to_drop:
                    attributes_to_drop.append(attribute)
        except:
            print("Unable to parse GHA_ATTRIBUTES_DROP, check your configuration")

    for attribute in obj:
        attribute_name = str(attribute).lower()
        if attribute_name not in attributes_to_drop:
            if do_parse(obj[attribute]):
                if type(obj[attribute]) is dict:
                    for sub_att in obj[attribute]:
                        attribute_name = do_string(attribute)+"."+do_string(sub_att)
                        if attribute_name not in attributes_to_drop:
                            if type(obj[attribute][sub_att]) is dict:
                                for att in obj[attribute][sub_att]:
                                    attribute_name = do_string(attribute)+"."+do_string(sub_att)+"."+do_string(att)
                                    if attribute_name not in attributes_to_drop:
                                        obj_atts[attribute_name]=str(obj[attribute][sub_att][att])

                            elif type(obj[attribute][sub_att]) is list:
                                for key in obj[attribute][sub_att]:
                                    if type(key) is dict:
                                        for att in key:
                                            if do_parse(key[att]):
                                                attribute_name = do_string(attribute)+"."+do_string(sub_att)+"."+do_string(att)
                                                if attribute_name not in attributes_to_drop:
                                                    obj_atts[attribute_name]=str(key[att])
                                    else:
                                        attribute_name = do_string(attribute)+"."+do_string(sub_att)
                                        if attribute_name not in attributes_to_drop:
                                            obj_atts[attribute_name]=str(key)
                            else:
                                attribute_name = do_string(attribute)+"."+do_string(sub_att)
                                if attribute_name not in attributes_to_drop:
                                    obj_atts[attribute_name]=str(obj[attribute][sub_att])

                elif type(obj[attribute]) is list:
                    for key in obj[attribute]:
                        if type(key) is dict:
                            for att in key:
                                if do_parse(key[att]):
                                    attribute_name = do_string(attribute)+"."+do_string(att)
                                    if attribute_name not in attributes_to_drop:
                                        obj_atts[attribute_name]=str(key[att])
                else:
                    if do_parse(obj[attribute]):
                        attribute_name = do_string(attribute)
                        if attribute_name not in attributes_to_drop:
                            obj_atts[attribute_name]=str(obj[attribute])
    return obj_atts
