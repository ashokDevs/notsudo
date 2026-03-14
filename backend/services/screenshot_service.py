import os
import uuid
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)

SCREENSHOT_PRESIGN_EXPIRY = 3_600 * 24 * 7
SCREENSHOT_TIMEOUT_MS = 30_000
VIEWPORT_WIDTH = 1_280
VIEWPORT_HEIGHT = 720


class ScreenshotService:
    def __init__(self):
        self.bucket_name = os.environ.get('AWS_S3_BUCKET', 'notsudo-sandbox-code')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')

        if BOTO3_AVAILABLE:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                region_name=self.region
            )
        else:
            self.s3_client = None
            logger.warning("boto3_not_available")

    def is_available(self) -> bool:
        return BOTO3_AVAILABLE and PLAYWRIGHT_AVAILABLE and bool(self.s3_client)

    def take_screenshot(self, url: str) -> Optional[str]:
        if not self.is_available():
            logger.error("screenshot_service_not_available")
            return None

        try:
            filename = f"screenshots/{uuid.uuid4()}.png"
            local_path = f"/tmp/{filename.split('/')[-1]}"

            logger.info("taking_screenshot", url=url)

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(viewport={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT})
                page = context.new_page()

                try:
                    page.goto(url, wait_until="networkidle", timeout=SCREENSHOT_TIMEOUT_MS)
                except Exception as e:
                    logger.warning("page_load_timeout_or_error", error=str(e))

                page.screenshot(path=local_path)
                browser.close()

            if os.path.exists(local_path):
                logger.info("uploading_screenshot", filename=filename)

                with open(local_path, "rb") as f:
                    self.s3_client.upload_fileobj(
                        f,
                        self.bucket_name,
                        filename,
                        ExtraArgs={'ContentType': 'image/png'}
                    )

                os.remove(local_path)

                try:
                    url = self.s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': self.bucket_name, 'Key': filename},
                        ExpiresIn=SCREENSHOT_PRESIGN_EXPIRY
                    )
                    return url
                except Exception as e:
                    logger.error("presigned_url_generation_failed", error=str(e))
                    return None
            else:
                logger.error("screenshot_file_not_found", path=local_path)
                return None

        except Exception as e:
            logger.error("take_screenshot_failed", error=str(e))
            return None
