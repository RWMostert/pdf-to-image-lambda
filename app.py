import boto3
import logging
import os

from chalice import Chalice, Response
from io import BytesIO
from pdf2image import convert_from_bytes

app = Chalice(app_name='pdf2image')


DPI = 300
if 'DPI' in os.environ:
    try:
        DPI = int(os.environ['DPI'])
    except Exception as e:
        logging.debug(f"Couldn't process DPI environment variable: {str(e)}.  Using the default: DPI=300")
else:
    logging.info(f"No DPI environment variable set.  Using the default: DPI=300")

_SUPPORTED_IMAGE_EXTENSIONS = ["ppm", "jpeg", "png", "tiff"]
FMT = "png"
if 'FMT' in os.environ:
    environ_fmt = str(os.environ['FMT'])
    if environ_fmt in _SUPPORTED_IMAGE_EXTENSIONS:
        FMT = environ_fmt
    else:
        logging.debug(f"Couldn't process FMT variable.  "
                      f"Only the following formats are supported: {','.join(_SUPPORTED_IMAGE_EXTENSIONS)}.  "
                      f"Using the default: FMI='png'")
else:
    logging.info(f"No FMT environment variable set.  Using the default: FMT='png'")

DESTINATION_BUCKET = None
if 'DESTINATION_BUCKET' in os.environ:
    DESTINATION_BUCKET = str(os.environ['DESTINATION_BUCKET'])
    logging.info(f"Setting the destination bucket: {DESTINATION_BUCKET}. "
                 f"Be sure to set the S3 bucket trigger on the Lambda's configuration")
else:
    raise Exception(f"Couldn't process the DESTINATION_BUCKET environment variable. "
                    f"The DESTINATION_BUCKET needs to be set to a valid S3 bucket to which the user has full access.")

ORIGIN_BUCKET = ''
if 'ORIGIN_BUCKET' in os.environ:
    ORIGIN_BUCKET = str(os.environ['ORIGIN_BUCKET'])
    logging.info(f"Setting the origin bucket: {ORIGIN_BUCKET}. "
                 f"Be sure to set the S3 bucket trigger on the Lambda's configuration")
else:
    logging.info(f"Couldn't process the ORIGIN_BUCKET environment variable. "
                 f"Be sure to set the S3 bucket trigger on the Lambda's configuration.")

_SUPPORTED_FILE_EXTENSION = '.pdf'


@app.on_s3_event(bucket=ORIGIN_BUCKET,
                 events=['s3:ObjectCreated:*'])
def pdf_to_image(event):
    """Take a pdf fom an S3 bucket and convert it to a list of pillow images (one for each page of the pdf).
    :param event: A Lambda event (referring to an S3 event object created event).
    :return:
    """
    if not event.key.endswith(_SUPPORTED_FILE_EXTENSION):
        raise Exception(f"Only .pdf files are supported by this module.")

    logging.info(f"Fetching item (bucket: '{event.bucket}', key: '{event.key}') from S3.")

    # Fetch the image bytes
    s3 = boto3.resource('s3')
    obj = s3.Object(event.bucket, event.key)
    infile = obj.get()['Body'].read()
    logging.info("Successfully retrieved S3 object.")

    # Set poppler path
    poppler_path = "/var/task/lib/poppler-utils-0.26/usr/bin"
    images = convert_from_bytes(infile,
                                dpi=DPI,
                                fmt=FMT,
                                poppler_path=poppler_path)
    logging.info("Successfully converted pdf to image.")

    for page_num, image in enumerate(images):

        # The directory is: <name of the pdf>-num_pages-<number of pages in the pdf>
        directory = event.key.split('.')[0] + "-num_pages-" + str(len(images))

        # Then save the image and name it: <name of the pdf>-page<page number>.FMT
        location = directory + "/" + event.key.split('.')[0] + "-page" + str(page_num) + '.' + FMT

        logging.info(f"Saving page number {str(page_num)} to S3 at location: {DESTINATION_BUCKET}, {location}.")

        # Load it into the buffer and save the boytjie to S3
        buffer = BytesIO()
        image.save(buffer, FMT.upper())
        buffer.seek(0)
        s3.Object(
            DESTINATION_BUCKET,
            location
        ).put(
            Body=buffer,
            Metadata={
                'ORIGINAL_DOCUMENT_BUCKET': event.bucket,
                'ORIGINAL_DOCUMENT_KEY': event.key,
                'PAGE_NUMBER': str(page_num),
                'PAGE_COUNT': str(len(images))
            }
        )

    return Response(f"PDF document ({event.key}) successfully converted to a series of images.")
