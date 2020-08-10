"""
* Copyright 2019 EPAM Systems
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
* http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
"""

import logging
import logging.config
import os
import schedule
import time
from commons import metrics_gatherer, es_client
import datetime
from flask import Flask
from flask_cors import CORS
from utils import utils

APP_CONFIG = {
    "esHost":            os.getenv("ES_HOST", "http://localhost:9202"),
    "kibanaHost":        os.getenv("KIBANA_HOST", "http://localhost:5602"),
    "logLevel":          os.getenv("LOGGING_LEVEL", "DEBUG"),
    "postgresUser":      os.getenv("POSTGRES_USER", ""),
    "postgresPassword":  os.getenv("POSTGRES_PASSWORD", ""),
    "postgresDatabase":  os.getenv("POSTGRES_DB", "reportportal"),
    "postgresHost":      os.getenv("POSTGRES_HOST", "localhost"),
    "postgresPort":      os.getenv("POSTGRES_PORT", 5432),
    "allowed_start_time": os.getenv("ALLOWED_START_TIME", "22:00"),
    "allowed_end_time":   os.getenv("ALLOWED_END_TIME", "08:00"),
}


def create_application():
    """Creates a Flask application"""
    _application = Flask(__name__)
    return _application


def start_metrics_gathering():
    _es_client = es_client.EsClient(APP_CONFIG)
    if not utils.is_the_time_for_task_starting(APP_CONFIG["allowed_start_time"],
                                               APP_CONFIG["allowed_end_time"]):
        logger.debug("Starting of tasks is allowed only from %s to %s",
                     APP_CONFIG["allowed_start_time"],
                     APP_CONFIG["allowed_end_time"])
        return
    if not _es_client.is_the_date_metrics_calculated(datetime.datetime.now()):
        _es_client.bulk_task_done_index([{
            "gather_date": datetime.datetime.now().date(),
            "started_task_time": datetime.datetime.now()
        }])
        logger.debug("Task started...")
        _metrics = metrics_gatherer.MetricsGatherer(APP_CONFIG)
        _metrics.gather_metrics(datetime.datetime.now(),
                                datetime.datetime.now())
        logger.debug("Task finished...")
    else:
        logger.debug("Task for today was already completed...")


log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf')
logging.config.fileConfig(log_file_path)
if APP_CONFIG["logLevel"].lower() == "debug":
    logging.disable(logging.NOTSET)
elif APP_CONFIG["logLevel"].lower() == "info":
    logging.disable(logging.DEBUG)
else:
    logging.disable(logging.INFO)
logger = logging.getLogger("metricsGatherer")

application = create_application()
CORS(application)
schedule.every().hour.do(start_metrics_gathering)
try:
    while True:
        schedule.run_pending()
        time.sleep(1)
except Exception as e:
    logger.error(e)
    logger.error("Metrics gatherer has finished with errors")
    exit(0)
logger.info("The metrics gatherer has finished")
exit(0)
