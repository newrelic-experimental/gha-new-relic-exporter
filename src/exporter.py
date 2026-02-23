from ghapi.all import GhApi
from custom_parser import (
    do_time,
    do_fastcore_decode,
    parse_attributes,
    check_env_vars,
    sanitize_filename,
    find_log_file,
    find_system_log_file,
)
import json
import logging
import os
from opentelemetry import trace
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.trace import Status, StatusCode
from otel import get_logger, get_tracer, create_resource_attributes
import requests
import zipfile
import dateutil.parser as dp

# Check if compulsory env variables are configured
check_env_vars()

# Configure env variables
GHA_TOKEN = os.getenv("GHA_TOKEN")
NEW_RELIC_LICENSE_KEY = os.getenv("NEW_RELIC_LICENSE_KEY")
OTEL_EXPORTER_OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTEL_ENDPOINT")
GHA_RUN_ID = os.getenv("GHA_RUN_ID")
GHA_RUN_NAME = os.getenv("GHA_RUN_NAME")
GITHUB_API_URL = os.getenv("GITHUB_API_URL")

if "GHA_EXPORT_LOGS" in os.environ and os.getenv("GHA_EXPORT_LOGS").lower() == "false":
    GHA_EXPORT_LOGS = False
    print("INFO: Not configured to send logs to backend")
else:
    print("INFO: Configured to send logs to backend")
    GHA_EXPORT_LOGS = True

if "GHA_REPOSITORY" in os.environ:
    GHA_SERVICE_NAME = os.getenv("GHA_REPOSITORY")
else:
    GHA_SERVICE_NAME = os.getenv("GITHUB_REPOSITORY")

if "GHA_REPOSITORY_OWNER" in os.environ:
    GITHUB_REPOSITORY_OWNER = os.getenv("GHA_REPOSITORY_OWNER")
else:
    GITHUB_REPOSITORY_OWNER = os.getenv("GITHUB_REPOSITORY_OWNER")


# Check if debug is set
if "GHA_DEBUG" in os.environ and os.getenv("GHA_DEBUG").lower() == "true":
    print("Running on DEBUG mode")
    import http.client as http_client

    http_client.HTTPConnection.debuglevel = 1
    LoggingInstrumentor().instrument(set_logging_format=True, log_level=logging.DEBUG)
    logging.getLogger().setLevel(logging.DEBUG)


if OTEL_EXPORTER_OTEL_ENDPOINT in (None, ""):
    if NEW_RELIC_LICENSE_KEY and NEW_RELIC_LICENSE_KEY.startswith("eu"):
        OTEL_EXPORTER_OTEL_ENDPOINT = "https://otlp.eu01.nr-data.net:4318"
    else:
        OTEL_EXPORTER_OTEL_ENDPOINT = "https://otlp.nr-data.net:4318"

endpoint = "{}".format(OTEL_EXPORTER_OTEL_ENDPOINT)
headers = "api-key={}".format(NEW_RELIC_LICENSE_KEY)

# Github API client
api = GhApi(
    owner=GITHUB_REPOSITORY_OWNER,
    repo=GHA_SERVICE_NAME.split("/")[1],
    token=str(GHA_TOKEN),
)

# Github API calls
get_workflow_run_by_run_id = do_fastcore_decode(
    api.actions.get_workflow_run(GHA_RUN_ID)
)
get_workflow_run_jobs_by_run_id = do_fastcore_decode(
    api.actions.list_jobs_for_workflow_run(GHA_RUN_ID, page=1, per_page=100)
)

# Set OTEL resources
global_attributes = {
    SERVICE_NAME: GHA_SERVICE_NAME,
    "workflow_run_id": GHA_RUN_ID,
    "github.source": "github-exporter",
    "github.resource.type": "span",
}

# Example: GHA_CUSTOM_ATTS: '{"mycustomattributea":"test", "mycustomattributeb":10, "mycustomattributec":"My custom attribute"}'
# Check for custom attributes
if "GHA_CUSTOM_ATTS" in os.environ:
    GHA_CUSTOM_ATTS = os.environ["GHA_CUSTOM_ATTS"]
else:
    GHA_CUSTOM_ATTS = ""


if GHA_CUSTOM_ATTS != "":
    try:
        global_attributes.update(json.loads(GHA_CUSTOM_ATTS))
    except:
        print(
            "Error parsing GHA_CUSTOM_ATTS check your configuration, continuing without custom attributes"
        )
        pass

# Set workflow level tracer and logger
global_resource = Resource(attributes=global_attributes)
tracer = get_tracer(endpoint, headers, global_resource, "tracer")


# Ensure we don't export data for new relic exporters
workflow_run = json.loads(get_workflow_run_jobs_by_run_id)
job_lst = []
for job in workflow_run["jobs"]:
    if str(job["name"]).lower() not in ["new-relic-exporter"]:
        job_lst.append(job)

if len(job_lst) == 0:
    print(
        "No data to export, assuming this github action workflow job is a new relic exporter"
    )
    exit(0)

# Trace parent
workflow_run_atts = json.loads(get_workflow_run_by_run_id)
atts = parse_attributes(workflow_run_atts, "", "workflow")
print("Processing Workflow ->", GHA_RUN_NAME, "run id ->", GHA_RUN_ID)
p_parent = tracer.start_span(
    name=str(GHA_RUN_NAME),
    attributes=atts,
    start_time=do_time(workflow_run_atts["run_started_at"]),
    kind=trace.SpanKind.INTERNAL,
)

# Download logs
# Have to use python requests due to known issue with ghapi -> https://github.com/fastai/ghapi/issues/119
bearer = "Bearer " + GHA_TOKEN
req_headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": "Bearer " + GHA_TOKEN,
    "X-GitHub-Api-Version": "2022-11-28",
}

url1 = (
    GITHUB_API_URL
    + "/repos/"
    + GHA_SERVICE_NAME.split("/")[0]
    + "/"
    + GHA_SERVICE_NAME.split("/")[1]
    + "/actions/runs/"
    + str(GHA_RUN_ID)
    + "/logs"
)
r1 = requests.get(url1, headers=req_headers)
with open("log.zip", "wb") as output_file:
    output_file.write(r1.content)

with zipfile.ZipFile("log.zip", "r") as zip_ref:
    zip_ref.extractall("./logs")

# Jobs trace span
# Set Jobs tracer and logger
pcontext = trace.set_span_in_context(p_parent)
import os


def print_log_folder_structure():
    if GHA_DEBUG:
        print("DEBUG: Folder structure under ./logs:")
        for root, dirs, files in os.walk("./logs"):
            level = root.replace("./logs", "").count(os.sep)
            indent = " " * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = " " * 2 * (level + 1)
            for f in files:
                print(f"{subindent}{f}")


GHA_DEBUG = "GHA_DEBUG" in os.environ and os.getenv("GHA_DEBUG").lower() == "true"
print_log_folder_structure()
for job in job_lst:
    try:
        print("Processing job ->", job["name"])
        child_0 = tracer.start_span(
            name=str(job["name"]),
            context=pcontext,
            start_time=do_time(job["started_at"]),
            kind=trace.SpanKind.CONSUMER,
        )
        child_0.set_attributes(
            create_resource_attributes(
                parse_attributes(job, "steps", "job"), GHA_SERVICE_NAME
            )
        )
        p_sub_context = trace.set_span_in_context(child_0)

        # Steps trace span
        for index, step in enumerate(job["steps"]):
            try:
                print("Processing step ->", step["name"], "from job", job["name"])
                # Set steps tracer and logger
                resource_attributes = {
                    SERVICE_NAME: GHA_SERVICE_NAME,
                    "github.source": "github-exporter",
                    "github.resource.type": "span",
                    "workflow_run_id": GHA_RUN_ID,
                }
                # Add custom attributes if they exist
                if GHA_CUSTOM_ATTS != "":
                    try:
                        resource_attributes.update(json.loads(GHA_CUSTOM_ATTS))
                    except:
                        print(
                            "Error parsing GHA_CUSTOM_ATTS check your configuration, continuing without custom attributes"
                        )
                        pass
                resource_log = Resource(attributes=resource_attributes)

                step_tracer = get_tracer(endpoint, headers, resource_log, "step_tracer")

                resource_attributes.update(
                    create_resource_attributes(
                        parse_attributes(step, "", "step"), GHA_SERVICE_NAME
                    )
                )
                resource_log = Resource(attributes=resource_attributes)
                job_logger = get_logger(endpoint, headers, resource_log, "job_logger")

                if step["conclusion"] == "skipped" or step["conclusion"] == "cancelled":
                    if index >= 1:
                        # Start time should be the previous step end time
                        step_started_at = job["steps"][index - 1]["completed_at"]
                    else:
                        step_started_at = job["started_at"]
                else:
                    step_started_at = step["started_at"]

                child_1 = step_tracer.start_span(
                    name=str(step["name"]),
                    start_time=do_time(step_started_at),
                    context=p_sub_context,
                    kind=trace.SpanKind.CONSUMER,
                )
                child_1.set_attributes(
                    create_resource_attributes(
                        parse_attributes(step, "", "job"), GHA_SERVICE_NAME
                    )
                )
                with trace.use_span(child_1, end_on_exit=False):
                    # Parse logs
                    log_path = find_log_file("./logs", job["name"], step["number"], step["name"])
                    try:
                        with open(log_path) as f:
                            for line in f.readlines():
                                try:
                                    # Remove BOM and leading whitespace
                                    clean_line = line.lstrip("\ufeff").lstrip()
                                    line_to_add = clean_line[29:-1].strip()
                                    len_line_to_add = len(line_to_add)
                                    timestamp_to_add = clean_line[0:23]
                                    if len_line_to_add > 0:
                                        try:
                                            parsed_t = dp.isoparse(timestamp_to_add)
                                        except ValueError as e:
                                            print(
                                                f"Line does not start with a date. Skip for now: {line.strip()}"
                                            )
                                            continue
                                        unix_timestamp = parsed_t.timestamp() * 1000
                                        if line_to_add.lower().startswith("##[error]"):
                                            child_1.set_status(
                                                Status(
                                                    StatusCode.ERROR, line_to_add[9:]
                                                )
                                            )
                                            child_0.set_status(
                                                Status(
                                                    StatusCode.ERROR,
                                                    "STEP: "
                                                    + str(step["name"])
                                                    + " failed",
                                                )
                                            )
                                            if GHA_EXPORT_LOGS:
                                                job_logger._log(
                                                    level=logging.ERROR,
                                                    msg=line_to_add,
                                                    extra={
                                                        "log.timestamp": unix_timestamp,
                                                        "log.time": timestamp_to_add,
                                                    },
                                                    args="",
                                                )
                                        elif line_to_add.lower().startswith(
                                            "##[warning]"
                                        ):
                                            if GHA_EXPORT_LOGS:
                                                job_logger._log(
                                                    level=logging.WARNING,
                                                    msg=line_to_add,
                                                    extra={
                                                        "log.timestamp": unix_timestamp,
                                                        "log.time": timestamp_to_add,
                                                    },
                                                    args="",
                                                )
                                        elif line_to_add.lower().startswith(
                                            "##[notice]"
                                        ):
                                            if GHA_EXPORT_LOGS:
                                                job_logger._log(
                                                    level=12,
                                                    msg=line_to_add,
                                                    extra={
                                                        "log.timestamp": unix_timestamp,
                                                        "log.time": timestamp_to_add,
                                                    },
                                                    args="",
                                                )
                                        elif line_to_add.lower().startswith(
                                            "##[debug]"
                                        ):
                                            if GHA_EXPORT_LOGS:
                                                job_logger._log(
                                                    level=logging.DEBUG,
                                                    msg=line_to_add,
                                                    extra={
                                                        "log.timestamp": unix_timestamp,
                                                        "log.time": timestamp_to_add,
                                                    },
                                                    args="",
                                                )
                                        else:
                                            if GHA_EXPORT_LOGS:
                                                job_logger._log(
                                                    level=logging.INFO,
                                                    msg=line_to_add,
                                                    extra={
                                                        "log.timestamp": unix_timestamp,
                                                        "log.time": timestamp_to_add,
                                                    },
                                                    args="",
                                                )
                                except Exception as e:
                                    print("Error exporting log line ERROR: ", e)
                    except IOError as e:
                        if (
                            step["conclusion"] == "skipped"
                            or step["conclusion"] == "cancelled"
                        ):
                            print(
                                "Log file not expected for this step ->",
                                step["name"],
                                "<- because its status is ->",
                                step["conclusion"],
                            )
                        else:
                            if GHA_DEBUG:
                                print(
                                    f"ERROR: Log file does not exist: {sanitize_filename(job['name'])}/{str(step['number'])}_{sanitize_filename(step['name'])}.txt"
                                )
                                print(f"DEBUG: Full path searched: {log_path}")

                if step["conclusion"] == "skipped" or step["conclusion"] == "cancelled":
                    child_1.update_name(name=str(step["name"] + "-SKIPPED"))
                    if index >= 1:
                        # End time should be the previous step end time
                        step_completed_at = job["steps"][index - 1]["completed_at"]
                    else:
                        step_completed_at = job["started_at"]
                else:
                    step_completed_at = step["completed_at"]

                child_1.end(end_time=do_time(step_completed_at))
                if GHA_DEBUG:
                    print(
                        "Finished processing step ->",
                        step["name"],
                        "from job",
                        job["name"],
                    )
            except Exception as e:
                print("Unable to process step ->", step["name"], "<- due to error", e)

        child_0.end(end_time=do_time(job["completed_at"]))
        # Process system.txt for the job if it exists
        system_log_path = find_system_log_file("./logs", job["name"])
        if system_log_path and os.path.exists(system_log_path):
            try:
                with open(system_log_path) as syslog:
                    for line in syslog.readlines():
                        # Try to parse timestamp and message
                        try:
                            timestamp_to_add = line[0:23]
                            line_to_add = line[29:-1].strip()
                            parsed_t = dp.isoparse(timestamp_to_add)
                            unix_timestamp = parsed_t.timestamp() * 1000
                            if GHA_EXPORT_LOGS:
                                job_logger._log(
                                    level=logging.INFO,
                                    msg=line_to_add,
                                    extra={
                                        "log.timestamp": unix_timestamp,
                                        "log.time": timestamp_to_add,
                                    },
                                    args="",
                                )
                        except Exception as e:
                            print("Error exporting system.txt log line ERROR: ", e)
            except Exception as e:
                print(
                    "Unable to process system.txt for job ->",
                    job["name"],
                    "<- due to error",
                    e,
                )
        workflow_run_finish_time = do_time(job["completed_at"])
        if GHA_DEBUG:
            print("Finished processing job ->", job["name"])
    except Exception as e:
        print("Unable to process job ->", job["name"], "<- due to error", e)

p_parent.end(end_time=workflow_run_finish_time)
if GHA_DEBUG:
    print("Finished processing Workflow ->", GHA_RUN_NAME, "run id ->", GHA_RUN_ID)
    print("All data exported to New Relic")
