"""Upload command for xtctool CLI."""

import click
import sys
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


@click.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--host', '-h', help='Device IP address', required=True)
@click.option('--port', '-p', type=int, default=80, help='Device port')
@click.option('--remote-path', '-r', default=None, help='Remote file path (default: same as local filename)')
def upload(
    file_path: str,
    host: str,
    port: int,
    remote_path: str
):
    """Upload file to ESP32 device.

    Example:
        xtctool upload output.xtc --host 192.168.1.2
        xtctool upload output.xth --host 192.168.1.2 --remote-path /comics/page1.xth
    """
    try:
        # Determine remote path
        if remote_path is None:
            remote_path = f"/{Path(file_path).name}"

        # Ensure remote path starts with /
        if not remote_path.startswith('/'):
            remote_path = f"/{remote_path}"

        url = f"http://{host}:{port}/edit"

        logger.info(f"Uploading {file_path} to {host}:{port}{remote_path}...")

        # Read file
        with open(file_path, 'rb') as f:
            file_data = f.read()

        # Prepare multipart form data
        # The form field name is "data" and filename is the remote path
        files = {
            'data': (remote_path, file_data, 'application/octet-stream')
        }

        # Send request
        response = requests.post(
            url,
            files=files,
            headers={
                'Accept': '*/*',
                'User-Agent': 'xtctool/0.1.0',
            },
            timeout=30
        )

        # Check response
        if response.status_code == 200:
            logger.info(f"Successfully uploaded to {host}{remote_path}")
        else:
            logger.error(
                f"Upload failed with status {response.status_code}: {response.text}"
            )
            sys.exit(1)

    except requests.exceptions.ConnectionError:
        logger.error(f"Could not connect to {host}:{port}")
        logger.error("Make sure the device is powered on and connected to the network.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
