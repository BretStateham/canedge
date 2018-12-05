# canedge
Azure IoT Edge sample CAN Bus (really specfically OBD-II on CAN Bus) module

## Overview

- Sends periodic requests on the CAN Bus for PIDs
  - 0x05 – Engine Coolant Temperature
  - 0x0C – Engine RPM
  - 0x10 – MAF Air Flow Rate

- Listens for 0x7E8 messages for those PIDS and stores the values
- Sends periodic messages to Azure IoT Hub with latest values
- Frequency control by the obdii_query_interval twin property

## Change Image Tag

You will need to modify the `modules/canmodule/module.json` file to set the `repository` to an appropriate one for you (`localhost`, `your docker hub username`, `your acr fqdn`, etc)

For example, if you wanted to push your image to docker hub, and your docker hub username was `awesomedev` you would change:

`canacr.azurecr.io/canmodule`

to 

`awesomedev/canmodule`

```json
{
    "$schema-version": "0.0.1",
    "description": "",
    "image": {
        "repository": "canacr.azurecr.io/canmodule",
        "tag": {
            "version": "0.0.27",
            "platforms": {
                "amd64": "./Dockerfile.amd64",
                "amd64.debug": "./Dockerfile.amd64.debug",
                "arm32v7": "./Dockerfile.arm32v7"
            }
        },
        "buildOptions": []
    },
    "language": "python"
}
```

## ACR Credentials

You will need to choose where you want to push your container to

I used an Azure Container Registry named `canacr`.  

To use ACR, you will need to:

1. Create your own Azure Container Registry with "Admin Enabled"
1. Get the login credentials for your ACR
1. Create a file name ".env" in the root of the project folder
1. Modify the .env file to use your ACR credentials:

  ```text
  CONTAINER_REGISTRY_USERNAME_canacr=<your_acr_name>
  CONTAINER_REGISTRY_PASSWORD_canacr=<your_acr_password>
  ```

  For example:

  ```text
  CONTAINER_REGISTRY_USERNAME_canacr=canacr
  CONTAINER_REGISTRY_PASSWORD_canacr=QR1BF+9cdfDoPbBEER/1+U19GOoDugwl
  ```
