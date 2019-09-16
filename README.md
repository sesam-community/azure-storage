[![Build Status](https://travis-ci.org/sesam-community/azure-storage.svg?branch=master)](https://travis-ci.org/sesam-community/azure-storage)


# azure-storage
Can be used to
 * reads files from Azure Storage(Blob/Files)
 * upload files to Azure Storage(Blob/Files)

 ### Environment Parameters

 | CONFIG_NAME        | DESCRIPTION           | IS_REQUIRED  |DEFAULT_VALUE|
 | -------------------|---------------------|:------------:|:-----------:|
 | ACCOUNT_NAME | Azure Storage account name. | no, basic auth alternatively | n/a |
 | ACCOUNT_KEY |  Azure Storage account key. | no, basic auth alternatively | n/a |
 | SAS_PARAMS | dict for the sas_token generation parameters | no | check the code |


 ### Query Parameters

 ##### POST REQUEST:

 | CONFIG_NAME        | DESCRIPTION           | IS_REQUIRED  |DEFAULT_VALUE|
 | -------------------|---------------------|:------------:|:-----------:|
 | start_timedelta | time offset for the start of sas_token validity. <numeric_value> followed by M, H and D for minutes, hours and days, respectively. | no | 0M (immediate start) |
 | expiry_timedelta | time offset for the expiry of sas_token validity. <numeric_value> followed by M, H and D for minutes, hours and days, respectively.  | no | 12H |



 ### An example of system config:

 ```json
 {
   "_id": "my_azure_storage",
   "type": "system:microservice",
   "connect_timeout": 60,
   "docker": {
     "environment": {
       "ACCOUNT_NAME":"myaccount",
       "ACCOUNT_KEY":"myaccount-key"
     },
     "image": "sesamcommunity/azure-storage:latest",
     "port": 5000
   },
   "read_timeout": 7200,
 }
 ```

### An example of input-pipe config:
```json
  {
    "_id": "mydataset-from-azure-storage-file",
    "type": "pipe",
    "source": {     
        "type": "json",
        "system": "my_azure_storage",
        "url": "/file/myshare/mydir/mydataset.json"
    },
    "transform": {
      "type": "dtl",
      "rules": {
        "default": [
          ["copy", "*"]
        ]
      }
    }
  }

  ```

### An example of output-pipe config:
Note that to uploading could be tricky due to batchsize etc. You might utilize another microservice between sesam and azure-storage for tailor-made solutions.
 ```json
 {
   "_id": "mydataset-ftp-endpoint",
   "type": "pipe",
   "source": {
     "type": "dataset",
     "dataset": "mydataset-ftp"
   },
   "sink": {
     "type": "json",
     "system": "my_azure_storage",
     "batch_size": 1000000,
     "url": "/file/myshare/mydir/mydataset.json"
   },
   "transform": {
     "type": "dtl",
     "rules": {
       "default": [
         ["copy", "*"]
       ]
     }
   }
 }

 ```
