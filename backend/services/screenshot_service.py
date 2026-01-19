import os
import uuid
import time
from typing import Optional
from pathlib import Path

# Try to import boto3, but handle if it's not installed (though we installed it)
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

# Try to import playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)

class ScreenshotService:
    """
    Service to capture screenshots using Playwright and upload to S3.
    """

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
        """
        Takes a screenshot of the given URL and uploads it to S3.
        Returns the S3 URL (presigned or public).
        """
        if not self.is_available():
            logger.error("screenshot_service_not_available")
            return None

        try:
            # Generate unique filename
            filename = f"screenshots/{uuid.uuid4()}.png"
            local_path = f"/tmp/{filename.split('/')[-1]}"

            logger.info("taking_screenshot", url=url)

            # Capture screenshot
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                # Set viewport size for better screenshots
                context = browser.new_context(viewport={'width': 1280, 'height': 720})
                page = context.new_page()

                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                except Exception as e:
                    logger.warning("page_load_timeout_or_error", error=str(e))
                    # Continue anyway, might have partial load

                page.screenshot(path=local_path)
                browser.close()

            # Upload to S3
            if os.path.exists(local_path):
                logger.info("uploading_screenshot", filename=filename)

                with open(local_path, "rb") as f:
                    self.s3_client.upload_fileobj(
                        f,
                        self.bucket_name,
                        filename,
                        ExtraArgs={'ContentType': 'image/png'}
                    )

                # Cleanup local file
                os.remove(local_path)

                # Generate URL
                # If bucket is private, generate presigned URL (valid for 1 hour)
                # If public, we can construct the URL.
                # Assuming private for safety, generating presigned URL.
                try:
                    url = self.s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': self.bucket_name, 'Key': filename},
                        ExpiresIn=3600 * 24 * 7  # 1 week expiration
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
