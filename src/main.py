"""main.py"""

import logging
import json
from tempfile import mkdtemp

import boto3

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions

from src.objectwrapper import ObjectWrapper

logger = logging.getLogger(__name__)


def initialise_driver():
    """
    Initialise Chrome driver
    """
    logger.info("`initialise_driver`")
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-tools")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument(f"--user-data-dir={mkdtemp()}")
    chrome_options.add_argument(f"--data-path={mkdtemp()}")
    chrome_options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    chrome_options.add_argument("--remote-debugging-pipe")
    chrome_options.add_argument("--verbose")
    chrome_options.add_argument("--log-path=/tmp")
    chrome_options.binary_location = "/opt/chrome/chrome-linux64/chrome"

    service = Service(
        executable_path="/opt/chrome-driver/chromedriver-linux64/chromedriver",
        service_log_path="/tmp/chromedriver.log",
    )

    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver


def put_object(data, bucket, object_key):
    """
    AWS Lambda handler
    """
    s3_resource = boto3.resource("s3")
    bucket = s3_resource.Bucket(bucket)

    obj_wrapper = ObjectWrapper(bucket.Object(object_key))
    obj_wrapper.put(data)

    logger.info("Have put '%s' into object '%s'", data, object_key)


def lambda_handler(event, context):
    """
    AWS Lambda handler
    """
    logger.info("Entered `lambda_handler` with %s and %s", event, context)

    test_url = event.get("test-url", "")
    logger.info("Init driver and getting url '%s'", test_url)
    driver = initialise_driver()
    driver.get(test_url)
    logger.info("Page title: '%s'", driver.title)

    body = {"title": driver.title}

    response = {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }

    s3_bucket = event.get("s3-bucket", "")
    s3_object_key = event.get("s3-object-key", "")

    logger.info(
        "Putting '%s' into object '%s' in bucket '%s'",
        test_url,
        s3_object_key,
        s3_bucket,
    )

    return response
