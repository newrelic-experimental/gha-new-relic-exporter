import time
from pyrfc3339 import parse
import os
import ast
import json
from fastcore.xtras import obj2dict

def do_fastcore_decode(obj):
    newobj = obj2dict(obj)
    return json.dumps(newobj)

def do_time(string):
    return (int(round(time.mktime(parse(string).timetuple())) * 1000000000))

def do_string(string):
    return str(string).lower().replace(" ", "")

def do_parse(string):
    return string != "" and string is not None and string != "None"

def check_env_vars():
    keys = ("NEW_RELIC_LICENSE_KEY","GHA_TOKEN")
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

def parse_attributes(obj,att_to_drop):
    obj_atts = {}
    attributes_to_drop = []
    # todo
    # if "GHA_ATTRIBUTES_DROP" in os.environ:
    #     try:
    #         if os.getenv("GHA_ATTRIBUTES_DROP") != "":
    #             user_attributes_to_drop =str(os.getenv("GHA_ATTRIBUTES_DROP")).lower().split(",")
    #             for attribute in user_attributes_to_drop:
    #                 attributes_to_drop.append(attribute)
    #     except:
    #         print("Unable to parse GHA_ATTRIBUTES_DROP, check your configuration")

    for attribute in list(obj):
        attribute_name = str(attribute).lower()
        if attribute_name.endswith("_at"):
            new_Att_name=attribute_name+"_ms"
            obj[new_Att_name]=do_time(obj[attribute])
            print(attribute_name,do_time(obj[attribute])[:-6])
        
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
