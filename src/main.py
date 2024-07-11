"""main.py"""

import logging
import json
from tempfile import mkdtemp

import boto3
from botocore.exceptions import ClientError

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions

logger = logging.getLogger(__name__)


def initialise_driver():
    """
    Initialise Chrome driver
    """
    print("Initialising driver")
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

    print(f"Have put '{data}' into object '{object_key}'")

    object_list = ObjectWrapper.list(bucket)
    print(f"Object keys are: {', '.join(o.key for o in object_list)}")


def lambda_handler(event, context):
    """
    AWS Lambda handler
    """
    print(f"Entered `lambda_handler()` with '{event}' and {context}")

    test_url = event.get("test-url", "")
    print(f"Init driver and getting url '{test_url}'")
    driver = initialise_driver()
    driver.get(test_url)
    print(f"Page title: '{driver.title}'")

    body = {"title": driver.title}

    response = {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }

    s3_bucket = event.get("s3-bucket", "")
    s3_object_key = event.get("s3-object-key", "")
    print(f"Putting '{test_url}' into object '{s3_object_key}' in bucket '{s3_bucket}'")
    put_object(test_url, s3_bucket, s3_object_key)

    return response


class ObjClientExceptions(ClientError):
    """Encapsulates boto client exceptions"""


class ObjectWrapper:
    """Encapsulates S3 object actions"""

    def __init__(self, s3_object):
        """
        Args:
            s3_object: A Boto3 object resource
        """
        self.object = s3_object
        self.key = self.object.key

    def put(self, data):
        """
        Upload data to the object

        Args:
            data: The data (bytes or string) to upload. When this is a string,
            it is interpreted as a file name, which is  opened in read bytes
            mode.
        """
        put_data = data
        if isinstance(data, str):
            try:
                put_data = open(data, "rb")
            except IOError:
                logger.exception("Expected file name or binary data, got '%s'.", data)
                raise

        try:
            self.object.put(Body=put_data)
            self.object.wait_until_exists()
            print(
                f"Put object '{self.object.key}' to bucket '{self.object.bucket_name}'."
            )
        except ObjClientExceptions:
            logger.exception(
                "Couldn't put object '%s' to bucket '%s'.",
                self.object.key,
                self.object.bucket_name,
            )
            raise
        finally:
            if getattr(put_data, "close", None):
                put_data.close()

    def get(self):
        """
        Gets the object

        Return:
            The object data in bytes.
        """
        try:
            body = self.object.get()["Body"].read()
            print(
                "Got object '%s' from bucket '%s'.",
                self.object.key,
                self.object.bucket_name,
            )
        except ObjClientExceptions:
            logger.exception(
                "Couldn't get object '%s' from bucket '%s'.",
                self.object.key,
                self.object.bucket_name,
            )
            raise
        else:
            return body

    @staticmethod
    def list(bucket, prefix=None):
        """
        Lists the objects in a bucket, optionally filtered by a prefix.

        Args:
            bucket: The Boto3 bucket to query
            prefix: When specified, only objects that start with this prefix are
            listed.

        Return:
            The list of objects.
        """
        try:
            if not prefix:
                objects = list(bucket.objects.all())
            else:
                objects = list(bucket.objects.filter(Prefix=prefix))
            print(
                "Got objects %s from bucket '%s'", [o.key for o in objects], bucket.name
            )
        except ObjClientExceptions:
            logger.exception("Couldn't get objects for bucket '%s'.", bucket.name)
            raise
        else:
            return objects

    def delete(self):
        """
        Deletes the object
        """
        try:
            self.object.delete()
            self.object.wait_until_not_exists()
            print(
                "Deleted object '%s' from bucket '%s'.",
                self.object.key,
                self.object.bucket_name,
            )
        except ObjClientExceptions:
            logger.exception(
                "Couldn't delete object '%s' from bucket '%s'.",
                self.object.key,
                self.object.bucket_name,
            )
            raise

    @staticmethod
    def delete_objects(bucket, object_keys):
        """
        Removes a list of objects from a bucket. This operation is done as a
        batch in a single request.

        Args:
            bucket: The Boto3 bucket that contains the objects
            object_keys: The list of keys that identify the objects to remove
        Return:
            The response that contains data about which objects were and were
            not deleted
        """
        try:
            response = bucket.delete_objects(
                Delete={"Objects": [{"Key": key} for key in object_keys]}
            )
            if "Deleted" in response:
                print(
                    "Deleted objects '%s' from bucket '%s'.",
                    [del_obj["Key"] for del_obj in response["Deleted"]],
                    bucket.name,
                )
            if "Errors" in response:
                logger.warning(
                    "Could not delete objects '%s' from bucket '%s'.",
                    [
                        f"{del_obj['Key']}: {del_obj['Code']}"
                        for del_obj in response["Errors"]
                    ],
                    bucket.name,
                )
        except ObjClientExceptions:
            logger.exception("Couldn't delete any objects from bucket %s.", bucket.name)
            raise
        else:
            return response

    @staticmethod
    def empty_bucket(bucket):
        """
        Remove all objects from a bucket

        Args:
            bucket: The Boto3 bucket to empty
        """
        try:
            bucket.objects.delete()
            print("Emptied bucket '%s'.", bucket.name)
        except ObjClientExceptions:
            logger.exception("Couldn't empty bucket '%s'.", bucket.name)
            raise
