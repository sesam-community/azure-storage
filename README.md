# sesam-datasource-ftp
sesam Http->Ftp microservice

An example of system config: 

```json
{
  "_id": "sesam-datasource-ftp",
  "type": "system:microservice",
  "connect_timeout": 60,
  "docker": {
    "environment": {
      "sys_id": "ftp://ftp_server_url"
    },
    "image": "sesam/sesam-datasource-ftp:latest",
    "memory": 64,
    "port": 5000
  },
  "read_timeout": 7200,
  "verify_ssl": false
}
```

This microservice should receive some http request,
such as "http://sesam-datasource-ftp:5000/{sys_id}/file?fpath={fpath}".

{sys_id} should be an environment variable that contains the ftp server url. 
If you dont want to define {sys_id} in the environment variables. 
You also can use this url pattern "http://sesam-datasource-ftp:5000/{sys_id}/file?fpath={fpath}&sys_id=ftp://ftp_server_url".

