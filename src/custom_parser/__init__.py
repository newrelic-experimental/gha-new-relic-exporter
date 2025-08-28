import time
from pyrfc3339 import parse
import os
import json
from fastcore.xtras import obj2dict
import re


def sanitize_filename(name: str) -> str:
    name = str(name)
    # Replace only forbidden/special characters, preserve spaces
    name = name.replace("/", " _ ")
    name = re.sub(r'[\\:*?"<>|]', "_", name)
    name = name.strip()
    return name


def do_fastcore_decode(obj):
    newobj = obj2dict(obj)
    return json.dumps(newobj)


def do_time(string):
    return int(round(time.mktime(parse(string).timetuple())) * 1000000000)


def do_time_ms(string):
    if string is None or string == "":
        return None
    return int(round(time.mktime(parse(string).timetuple())) * 1000)


def do_string(string):
    return str(string).lower().replace(" ", "")


def do_parse(string):
    return string != "" and string is not None and string != "None"


def check_env_vars():
    keys = ("NEW_RELIC_LICENSE_KEY", "GHA_TOKEN")
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


def parse_attributes(obj, att_to_drop, otype):
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
    # Calculate ms values for created_at, started_at, completed_at early
    created_at_ms = do_time_ms(obj.get("created_at"))
    started_at_val = obj.get("started_at")
    started_at_ms = do_time_ms(started_at_val) if started_at_val else None
    completed_at_ms = do_time_ms(obj.get("completed_at"))

    # Fallback for started_at if None
    if started_at_val is None or started_at_val == "":
        started_at_val = obj.get("created_at")
        started_at_ms = created_at_ms

    # Detect job reuse
    job_reused = False
    if (
        started_at_ms is not None
        and created_at_ms is not None
        and started_at_ms < created_at_ms
    ):
        job_reused = True
        started_at_val = obj.get("created_at")
        started_at_ms = created_at_ms
    # Add ms fields and job_reused flag
    if obj.get("created_at") is not None:
        obj_atts["created_at"] = obj.get("created_at")
        obj_atts["created_at_ms"] = created_at_ms
    if started_at_val is not None:
        obj_atts["started_at"] = started_at_val
        obj_atts["started_at_ms"] = started_at_ms
    if obj.get("completed_at") is not None:
        obj_atts["completed_at"] = obj.get("completed_at")
        obj_atts["completed_at_ms"] = completed_at_ms
    obj_atts["job_reused"] = job_reused

    # Calculate queue_time and duration
    if job_reused:
        obj_atts["queue_time_ms"] = 0
        obj_atts["duration_ms"] = 0
    else:
        if started_at_ms is not None and created_at_ms is not None:
            obj_atts["queue_time_ms"] = max(0, started_at_ms - created_at_ms)
        if started_at_ms is not None and completed_at_ms is not None:
            obj_atts["duration_ms"] = max(0, completed_at_ms - started_at_ms)

    # Continue with normal attribute parsing
    for attribute in list(obj):
        attribute_name = str(attribute).lower()
        # Skip already handled fields
        if attribute_name in ["created_at", "started_at", "completed_at"]:
            continue
        if attribute_name.endswith("_at"):
            new_Att_name = attribute_name + "_ms"
            obj_atts[new_Att_name] = do_time_ms(obj[attribute])

        if attribute_name not in attributes_to_drop:
            if do_parse(obj[attribute]):
                if type(obj[attribute]) is dict:
                    for sub_att in obj[attribute]:
                        attribute_name = do_string(attribute) + "." + do_string(sub_att)
                        if attribute_name not in attributes_to_drop:
                            if type(obj[attribute][sub_att]) is dict:
                                for att in obj[attribute][sub_att]:
                                    attribute_name = (
                                        do_string(attribute)
                                        + "."
                                        + do_string(sub_att)
                                        + "."
                                        + do_string(att)
                                    )
                                    if attribute_name not in attributes_to_drop:
                                        obj_atts[attribute_name] = str(
                                            obj[attribute][sub_att][att]
                                        )
                                        if attribute_name.endswith("_at"):
                                            new_Att_name = attribute_name + "_ms"
                                            obj_atts[new_Att_name] = do_time_ms(
                                                obj[attribute][sub_att][att]
                                            )

                            elif type(obj[attribute][sub_att]) is list:
                                for key in obj[attribute][sub_att]:
                                    if type(key) is dict:
                                        for att in key:
                                            if do_parse(key[att]):
                                                attribute_name = (
                                                    do_string(attribute)
                                                    + "."
                                                    + do_string(sub_att)
                                                    + "."
                                                    + do_string(att)
                                                )
                                                if (
                                                    attribute_name
                                                    not in attributes_to_drop
                                                ):
                                                    obj_atts[attribute_name] = str(
                                                        key[att]
                                                    )
                                                    if attribute_name.endswith("_at"):
                                                        new_Att_name = (
                                                            attribute_name + "_ms"
                                                        )
                                                        obj_atts[new_Att_name] = (
                                                            do_time_ms(key[att])
                                                        )

                                    else:
                                        attribute_name = (
                                            do_string(attribute)
                                            + "."
                                            + do_string(sub_att)
                                        )
                                        if attribute_name not in attributes_to_drop:
                                            obj_atts[attribute_name] = str(key)
                                            if attribute_name.endswith("_at"):
                                                new_Att_name = attribute_name + "_ms"
                                                obj_atts[new_Att_name] = do_time_ms(key)

                            else:
                                attribute_name = (
                                    do_string(attribute) + "." + do_string(sub_att)
                                )
                                if attribute_name not in attributes_to_drop:
                                    obj_atts[attribute_name] = str(
                                        obj[attribute][sub_att]
                                    )
                                    if attribute_name.endswith("_at"):
                                        new_Att_name = attribute_name + "_ms"
                                        obj_atts[new_Att_name] = do_time_ms(
                                            obj[attribute][sub_att]
                                        )

                elif type(obj[attribute]) is list:
                    for key in obj[attribute]:
                        if type(key) is dict:
                            for att in key:
                                if do_parse(key[att]):
                                    attribute_name = (
                                        do_string(attribute) + "." + do_string(att)
                                    )
                                    if attribute_name not in attributes_to_drop:
                                        obj_atts[attribute_name] = str(key[att])
                                        if attribute_name.endswith("_at"):
                                            new_Att_name = attribute_name + "_ms"
                                            obj_atts[new_Att_name] = do_time_ms(
                                                key[att]
                                            )
                else:
                    if do_parse(obj[attribute]):
                        attribute_name = do_string(attribute)
                        if attribute_name not in attributes_to_drop:
                            obj_atts[attribute_name] = str(obj[attribute])
                            if attribute_name.endswith("_at"):
                                new_Att_name = attribute_name + "_ms"
                                obj_atts[new_Att_name] = do_time_ms(obj[attribute])
    return obj_atts
