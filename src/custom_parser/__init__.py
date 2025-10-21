import time
from pyrfc3339 import parse
import os
import json
from fastcore.xtras import obj2dict
import re
from pathlib import Path


def sanitize_filename(name: str) -> str:
    name = str(name)
    # Normalize spaces around slashes, then replace '/' with ' _ '
    name = re.sub(r"\s*/\s*", "/", name)
    name = name.replace("/", " _ ")
    # Replace problematic characters but NOT < and > since GitHub Actions preserves them
    name = re.sub(r'[\\:*?"|]', "_", name)
    name = name.strip()
    return name


def find_log_file(logs_base_dir: str, job_name: str, step_number: int, step_name: str) -> str:
    """
    Find a log file in the extracted logs directory.

    GitHub Actions log structure can vary - files may be in a job-specific subdirectory
    or at the root level. This function searches multiple possible locations.

    Args:
        logs_base_dir: Base directory where logs are extracted (e.g., "./logs")
        job_name: Name of the job (will be sanitized)
        step_number: Step number
        step_name: Name of the step (will be sanitized)

    Returns:
        Full path to the log file if found, or None if not found
    """
    sanitized_job_name = sanitize_filename(job_name)
    sanitized_step_name = sanitize_filename(step_name)
    step_filename = f"{step_number}_{sanitized_step_name}.txt"

    # Primary location: in job-specific subdirectory
    primary_path = os.path.join(logs_base_dir, sanitized_job_name, step_filename)
    if os.path.exists(primary_path):
        return primary_path

    # Fallback location: at root level of logs directory
    fallback_path = os.path.join(logs_base_dir, step_filename)
    if os.path.exists(fallback_path):
        return fallback_path

    # Additional fallback: search for the file recursively in case structure differs
    # This handles unexpected directory structures
    try:
        for root, dirs, files in os.walk(logs_base_dir):
            if step_filename in files:
                return os.path.join(root, step_filename)
    except Exception:
        pass

    # File not found - return the primary path for error reporting
    return primary_path


def find_system_log_file(logs_base_dir: str, job_name: str) -> str:
    """
    Find a system.txt log file in the extracted logs directory.

    Similar to find_log_file, this handles variable directory structures.

    Args:
        logs_base_dir: Base directory where logs are extracted (e.g., "./logs")
        job_name: Name of the job (will be sanitized)

    Returns:
        Full path to the system log file if found, or None if not found
    """
    sanitized_job_name = sanitize_filename(job_name)
    system_filename = "system.txt"

    # Primary location: in job-specific subdirectory
    primary_path = os.path.join(logs_base_dir, sanitized_job_name, system_filename)
    if os.path.exists(primary_path):
        return primary_path

    # Fallback location: at root level of logs directory
    fallback_path = os.path.join(logs_base_dir, system_filename)
    if os.path.exists(fallback_path):
        return fallback_path

    # Additional fallback: search recursively
    try:
        for root, dirs, files in os.walk(logs_base_dir):
            if system_filename in files:
                # Only return if this is within the job-specific directory
                if sanitized_job_name in root or root == logs_base_dir:
                    return os.path.join(root, system_filename)
    except Exception:
        pass

    # File not found
    return None


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
