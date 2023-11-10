from ghapi.all import GhApi
from custom_parser import do_time,do_fastcore_decode,parse_attributes,check_env_vars
import json
import logging
import os
from opentelemetry import trace
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.trace import Status, StatusCode
from otel import get_logger,get_tracer,create_resource_attributes
import requests
import zipfile
import dateutil.parser as dp

# Check if compulsory env variables are configured
check_env_vars()

# Configure env variables
GHA_TOKEN = os.getenv('GHA_TOKEN')
NEW_RELIC_LICENSE_KEY = os.getenv('NEW_RELIC_LICENSE_KEY')
GHA_RUN_ID = os.getenv('GHA_RUN_ID')
GHA_SERVICE_NAME=os.getenv('GITHUB_REPOSITORY')
GITHUB_REPOSITORY_OWNER=os.getenv('GITHUB_REPOSITORY_OWNER')
GHA_RUN_NAME=os.getenv('GHA_RUN_NAME')
GITHUB_API_URL=os.getenv('GITHUB_API_URL')

if NEW_RELIC_LICENSE_KEY.startswith("eu"):
    OTEL_EXPORTER_OTEL_ENDPOINT = "https://otlp.eu01.nr-data.net:4318"
else:
    OTEL_EXPORTER_OTEL_ENDPOINT = "https://otlp.nr-data.net:4318"

endpoint="{}".format(OTEL_EXPORTER_OTEL_ENDPOINT)
headers="api-key={}".format(NEW_RELIC_LICENSE_KEY)

# Github API client
api = GhApi(owner=GITHUB_REPOSITORY_OWNER, repo=GHA_SERVICE_NAME.split('/')[1], token=str(GHA_TOKEN))

# Github API calls
get_workflow_run_by_run_id = do_fastcore_decode(api.actions.get_workflow_run(GHA_RUN_ID))
get_workflow_run_jobs_by_run_id = do_fastcore_decode(api.actions.list_jobs_for_workflow_run(GHA_RUN_ID))

#Set OTEL resources
global_attributes={
    SERVICE_NAME: GHA_SERVICE_NAME,
    "workflow_run_id": GHA_RUN_ID,
    "github.source": "github-exporter",
    "github.resource.type": "span"
}

LoggingInstrumentor().instrument()
# debug otel use configuration below
# LoggingInstrumentor().instrument(set_logging_format=True,log_level=logging.DEBUG)
# logging.basicConfig(filename="exporter.log",level=logging.DEBUG)

#Set workflow level tracer and logger
global_resource = Resource(attributes=global_attributes)
tracer = get_tracer(endpoint, headers, global_resource, "tracer")


#Ensure we don't export data for new relic exporters
workflow_run = json.loads(get_workflow_run_jobs_by_run_id)
job_lst=[]
for job in workflow_run['jobs']:
    if str(job['name']).lower() not in ["new-relic-exporter"]:
        job_lst.append(job)

if len(job_lst) == 0:
    print("No data to export, assuming this github action workflow job is a new relic exporter")
    exit(0)

# Trace parent
workflow_run_atts = json.loads(get_workflow_run_by_run_id)
atts=parse_attributes(workflow_run_atts,"")
p_parent = tracer.start_span(name=str(GHA_RUN_NAME) + " - run: "+str(GHA_RUN_ID),attributes=atts,start_time=do_time(workflow_run_atts['run_started_at']),kind=trace.SpanKind.SERVER)

# Download logs
# Have to use python requests due to known issue with ghapi -> https://github.com/fastai/ghapi/issues/119
bearer = "Bearer " + GHA_TOKEN
req_headers = {
    'Accept': 'application/vnd.github+json',
    'Authorization': "Bearer " + GHA_TOKEN,
    'X-GitHub-Api-Version': '2022-11-28'
}

url1=GITHUB_API_URL+"/repos/"+GHA_SERVICE_NAME.split("/")[0]+"/"+GHA_SERVICE_NAME.split("/")[1]+"/actions/runs/"+str(GHA_RUN_ID)+"/logs"
r1=requests.get(url1,headers=req_headers)
with open("log.zip",'wb') as output_file:
    output_file.write(r1.content)

with zipfile.ZipFile("log.zip", 'r') as zip_ref:
    zip_ref.extractall("./logs")

# Jobs trace span
# Set Jobs tracer and logger
pcontext = trace.set_span_in_context(p_parent)
for job in job_lst:
    child_0 = tracer.start_span(name=str(job['name']),context=pcontext,start_time=do_time(job['started_at']), kind=trace.SpanKind.CONSUMER)
    child_0.set_attributes(create_resource_attributes(parse_attributes(job,"steps"),GHA_SERVICE_NAME))
    p_sub_context = trace.set_span_in_context(child_0)

    # Steps trace span
    for step in job['steps']:
        # Set steps tracer and logger
        resource_attributes ={SERVICE_NAME: GHA_SERVICE_NAME,"github.source": "github-exporter","github.resource.type": "span","workflow_run_id": GHA_RUN_ID}
        resource_log = Resource(attributes=resource_attributes)
        step_tracer = get_tracer(endpoint, headers, resource_log, "step_tracer")
        
        resource_attributes.update(create_resource_attributes(parse_attributes(step,""),GHA_SERVICE_NAME))
        resource_log = Resource(attributes=resource_attributes)
        job_logger = get_logger(endpoint,headers,resource_log, "job_logger")
        
        step_started_at=job['started_at']
        if step['conclusion'] == 'success':
            step_started_at=step['started_at']
            
        child_1 = step_tracer.start_span(name=str(step['name']),start_time=do_time(step_started_at),context=p_sub_context,kind=trace.SpanKind.CONSUMER)
        child_1.set_attributes(create_resource_attributes(parse_attributes(step,""),GHA_SERVICE_NAME))
        with trace.use_span(child_1, end_on_exit=False):
            # Parse logs
            try:
                with open ("./logs/"+str(job["name"])+"/"+str(step['number'])+"_"+str(step['name'].replace("/",""))+".txt") as f:
                    for line in f.readlines():
                        try:
                            line_to_add = line[29:-1].strip()
                            len_line_to_add = len(line_to_add)
                            timestamp_to_add = line[0:23]
                            if len_line_to_add > 0:
                                if line_to_add.lower().startswith("##[error]"):
                                    child_1.set_status(Status(StatusCode.ERROR,line_to_add[9:]))
                                    child_0.set_status(Status(StatusCode.ERROR,"STEP: "+str(step['name'])+" failed"))
                                # Convert ISO 8601 to timestamp
                                try:
                                    parsed_t = dp.isoparse(timestamp_to_add)
                                except ValueError as e:
                                    print("Line does not start with a date. Skip for now")
                                    continue
                                unix_timestamp = parsed_t.timestamp()*1000
                                job_logger._log(level=logging.INFO,msg=line_to_add,extra={"log.timestamp":unix_timestamp,"log.time":timestamp_to_add},args="")
                        except Exception as e:
                            print("Error exporting log line ERROR: ", e)
            except IOError as e:
                print("Log file does not exist: "+str(job["name"])+"/"+str(step['number'])+"_"+str(step['name'].replace("/",""))+".txt")

        step_completed_at=job['started_at']
        if step['conclusion'] == 'success':
            step_completed_at=step['completed_at']
        else:
            child_1.update_name(name=str(step['name']+"SKIPPED"))
            
        child_1.end(end_time=do_time(step_completed_at))
    child_0.end(end_time=do_time(job['completed_at']))
    workflow_run_finish_time=do_time(job['completed_at'])
p_parent.end(end_time=workflow_run_finish_time)

print("All data exported to New Relic")
