import boto3
import base64
import hashlib
import logging
from io import BytesIO
from functools import partial


from common.exceptions import ErrorResultException

logger = logging.getLogger(__name__)


class InvalidUploadFormat(ErrorResultException):
    default_message = "invalid_upload_format"


def is_base64(s):
    try:
        return base64.b64encode(base64.b64decode(s)) == s
    except Exception as e:
        logger.info("bad base64 string", str(e), exc_info=True)
        return False


def hash_file(f, block_size=65536):
    hasher = hashlib.md5()
    for buf in iter(partial(f.read, block_size), b""):
        hasher.update(buf)

    f.seek(0)
    return hasher.hexdigest()


def hash_bytes(v):
    return hashlib.md5(v).hexdigest()


class Uploader:
    def __init__(self, **options):

        self.options = options
        self.bucket = options.get("BUCKET", None)

        self.client = boto3.client(
            "s3",
            aws_access_key_id=options["KEY"],
            aws_secret_access_key=options["SECRET"],
            endpoint_url=options["ENDPOINT"],
        )

    def get_bucket(self, bucket=None):
        if not bucket:
            bucket = self.bucket
        if not bucket:
            raise ValueError("Need bucket name")
        return bucket

    def gen_file_url(self, bucket, md5):
        return "%s/%s/%s" % (self.options["ENDPOINT"], bucket, md5)

    def upload_with_base64(self, content, bucket=None):
        bucket = self.get_bucket(bucket)

        content = str.encode(content)
        if not is_base64(content):
            raise TypeError("Upload content must be base64 encode")

        # Unicode-objects must be encoded before hashing
        md5 = hash_bytes(content)
        self.client.upload_fileobj(BytesIO(base64.b64decode(content)), bucket, md5)

        return self.gen_file_url(bucket, md5)

    def upload_files(self, files, bucket=None):
        result_urls = []
        for file_ in files:
            if not file_:
                logger.warn("Failed to get file in multipart")
                continue

            url = self.upload_file(file_, bucket=bucket)
            result_urls.append(url)
        return result_urls

    def upload_file(self, file_, bucket=None):
        bucket = self.get_bucket(bucket)
        with file_.open() as f:
            # NOTE: limit the file size on nginx conf?
            buf = f.read()
            md5 = hash_bytes(buf)
            self.client.upload_fileobj(BytesIO(buf), bucket, md5)
        return self.gen_file_url(bucket, md5)
