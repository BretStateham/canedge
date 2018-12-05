# canedge
Azure IoT Edge sample CAN Bus (really specfically OBD-II on CAN Bus) module

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
