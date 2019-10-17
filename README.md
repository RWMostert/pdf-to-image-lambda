# PDF-to-Image
Convert a PDF document in a source S3 bucket to a image, saving the image to a destination S3 bucket.

Thanks to Lambda's concurrency, this approach is well-suited to variable bulk/batch higher-volume conversion workloads.

Please double check you are in the AWS region you intend; this needs to be the **same region** as the bucket which will contain the PDF documents you wish to convert.

## Getting Started
- Clone this repository.
- In `.chalice/config/json` set the following environment variables:

> **ORIGIN_BUCKET**: the _name_ of the S3 bucket in which the original PDF documents are stored.  Any new uploads to this bucket will trigger the function to run.

> **DESTINATION_BUCKET**: the _name_ of the S3 bucket to which the converted image will be saved.

> **DPI** (optional): Dots per inch, can be seen as the relative resolution of the output image, higher is better but anything above 300 is usually not discernable to the naked eye. Keep in mind that this is directly related to the ouput images size when using file formats without compression (like PPM).

> **FORMAT** (optional): File format of the output images.  Supported values are "ppm", "jpeg", "png" and "tiff".

- Next create a Python virtual environment: `virtualenv env -p python3`.
- Activate the virtual environment: `source env/bin/activate`
- Install the requirements: `pip3 install -r requirements.txt`
- And deploy: `chalice deploy`

This should deploy a Lambda function which triggers on any upload to your `ORIGIN_BUCKET`. 

## Execution Role

Ensure that your execution role has both "s3:GetObject" and "s3:PutObject" permissions on both the source and destination buckets.

The easiest is to open the Lambda Function settings, scroll down to the **Execution Role** section, and click "View the
 pdf2image-dev role" on the IAM console.  Confirm that the role's policies includes S3 permissions, e.g.:

 ```
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::*"
        }
```

Without GetObject permission on the triggering bucket and PutObject permission on the output bucket, you'll get Access Denied errors.

## S3 Trigger
This function can respond to S3 ObjectCreated events. 

To configure the trigger, on the Lambda function, in "Designer > Add triggers", click "S3". The "Configure triggers" dialog appears.
Select a bucket (any time a pdf is added to this bucket, the function will run).

Verify that "all object create events" is selected (or choose PUT POST or COPY).

Click "Add" (bottom right), then "Save" (top right).

## Environment Variables

On the same screen in the Lambda Management Console for this function, scroll down to "Environment Variables":

You will need to set the output S3 Bucket for this function.  Optionally, you could also set the **format** and the **dpi** for the output image.


## Confirm successful installation
### S3 Trigger
If you configured the S3 trigger, you can try it, by copying a PDF document into the S3 bucket you have set the trigger on.

To verify it works, look for a PDF in your output bucket, or check the logs in cloudwatch

### Sizing Notes
If you observe "Process exited before completing request" errors, it might point to your lambda function not having sufficient access to sufficient resources, or having insufficient time-out period.
##### Memory
Experience suggests assigning *2048MB*.  
This can be set under the "Memory (MB)" header in the "Basic settings" section of the Lambda function configuration tab.

##### Timeout
The time taken for the Lambda to run, will depend on the size of the PDF document being processed.  For maximum flexibility, allow a 15 minute timeout, although experience suggests that the function should hardly ever take longer than a few seconds to run. 

This can be set under the "Timeout" header in the "Basic settings" section of the Lambda function configuration tab.
