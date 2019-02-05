# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import random
import time
import sys
import iothub_client
import json
import can
import threading
from time import sleep

# pylint: disable=E0611
from iothub_client import IoTHubModuleClient, IoTHubClientError, IoTHubTransportProvider
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError

# messageTimeout - the maximum time in milliseconds until a message times out.
# The timeout period starts at IoTHubModuleClient.send_event_async.
# By default, messages do not expire.
MESSAGE_TIMEOUT = 10000

# Global hub_manager instance
hub_manager = None

# global counters
RECEIVE_CALLBACKS = 0
SEND_CALLBACKS = 0

#TEMPERATURE_THRESHOLD = 25
TWIN_CALLBACKS = 0

#CAN Bus Variables
can_interface = "can0"
can_bus = None
can_bus_type = "socketcan"
obdii_query_interval = 5.0

#obdii_sensor_values
coolant_temp = 0.0
rpms = 0.0
maf = 0.0

# Choose HTTP, AMQP or MQTT as transport protocol.  Currently only MQTT is supported.
PROTOCOL = IoTHubTransportProvider.MQTT

# Callback received when the message that we're forwarding is processed.
def send_confirmation_callback(message, result, user_context):
    global SEND_CALLBACKS
    print ( "Confirmation[%d] received for message with result = %s" % (user_context, result) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    SEND_CALLBACKS += 1
    print ( "    Total calls confirmed: %d" % SEND_CALLBACKS )


# module_twin_callback is invoked when the module twin's desired properties are updated.
def module_twin_callback(update_state, payload, user_context):
    global TWIN_CALLBACKS
    global obdii_query_interval
    print ( "\nTwin callback called with:\nupdateStatus = %s\npayload = %s\ncontext = %s" % (update_state, payload, user_context) )
    data = json.loads(payload)
    if "desired" in data and "obdii_query_interval" in data["desired"]:
        obdii_query_interval = data["desired"]["obdii_query_interval"]
    if "obdii_query_interval" in data:
        obdii_query_interval = data["obdii_query_interval"]
    TWIN_CALLBACKS += 1
    print ( "Total calls confirmed: %d\n" % TWIN_CALLBACKS )


def send_can_message(msg):
  global can_bus
  if can_bus != None:
    try:
      can_bus.send(msg)
      print("Message sent on {}".format(can_bus.channel_info))
    except can.CanError as can_error:
      print("Message not sent: " + str(can_error))


def send_obdii_queries():
  global can_interface
  global can_bus

  threading.Timer(obdii_query_interval, send_obdii_queries).start()

  # Request the Engine Coolant Temperature (PID 0x5)
  msg = can.Message(arbitration_id=0x7DF,data=[2,1,0x5,0,0,0,0,0],extended_id=False)
  send_can_message(msg)
  sleep(0.02)

  # Request the Engine RPM (PID 0xC)
  msg = can.Message(arbitration_id=0x7DF,data=[2,1,0xC,0,0,0,0,0],extended_id=False)
  send_can_message(msg)
  sleep(0.02)

  # Request the MAF Air Flow Rate (PID 0x10)
  msg = can.Message(arbitration_id=0x7DF,data=[2,1,0x10,0,0,0,0,0],extended_id=False)
  send_can_message(msg)
  sleep(0.02)

def handle_can_message(message):
  global coolant_temp
  global rpms
  global maf

  # print ("CAN Message Received: " + str(message))
  
  # See the following to parse OBD-II responses:
  # https://en.wikipedia.org/wiki/OBD-II_PIDs#Service_01_PID_00

  id = message.arbitration_id
  addlbytes = message.data[0]
  service = message.data[1]
  pid = message.data[2]

  if addlbytes == 0x10:
    print("This message is the first message in a multi-message response.  Aborting further processing of the message.")
    return

  if id == 0x7E8 and service == 0x41: # 41 is an OBD-II response to a service 01 request
    if pid == 0x5:
      valuea = message.data[3]
      coolant_temp = valuea-40
      print("ECM Engine Coolant Temp: {}".format(coolant_temp))
    if pid == 0xC:
      valuea = message.data[3]
      valueb = message.data[4]
      rpms =  ((256*valuea)+valueb)/4.0
      print("ECM RPMs                : {}".format(rpms))
    if pid == 0x10:
      valuea = message.data[3]
      valueb = message.data[4]
      maf =  ((256*valuea)+valueb)/4.0
      print ("MAF Air Flow Rate      : {}".format(maf))

def send_iothub_message():
  global coolant_temp
  global rpms
  global maf
  global hub_manager

  threading.Timer(obdii_query_interval, send_iothub_message).start()

  msg_text = "{\"coolant_temp\": %.2f,\"rpms\": %s,\"maf\": %s}"
  msg_text_formatted = msg_text % (coolant_temp,rpms,maf)
  print(" Sending: {}".format(msg_text_formatted))
  msg = IoTHubMessage(msg_text_formatted)
  hub_manager.forward_event_to_output("output1",msg,0)

class HubManager(object):

    def __init__(
            self,
            protocol=IoTHubTransportProvider.MQTT):
        self.client_protocol = protocol
        self.client = IoTHubModuleClient()
        self.client.create_from_environment(protocol)

        # set the time until a message times out
        self.client.set_option("messageTimeout", MESSAGE_TIMEOUT)
        
        # Sets the callback when a module twin's desired properties are updated.
        self.client.set_module_twin_callback(module_twin_callback, self)
 
    # Forwards the message received onto the next stage in the process.
    def forward_event_to_output(self, outputQueueName, event, send_context):
        self.client.send_event_async(
            outputQueueName, event, send_confirmation_callback, send_context)

class CustomListener(can.Listener):

  message_received_callback = None

  def on_message_received(self,msg):
    #print("CUSTOM LISTENER RECEIVED A MESSAGE:")
    self.message_received_callback(msg)

def main(protocol):
    global hub_manager
    global can_interface
    global can_bus
    global can_bus_type
    try:
        print ( "\nPython %s\n" % sys.version )
        print ( "IoT Hub Client for Python" )

        hub_manager = HubManager(protocol)

        print ( "Starting the IoT Hub Python sample using protocol %s..." % hub_manager.client_protocol )
        print ( "The sample is now waiting for messages and will indefinitely.  Press Ctrl-C to exit. ")

        print ( "Initializing CAN Bus" )
        try:
          can_filters = []
          can_filters.append({"can_id": 0x7DF, "can_mask": 0x7FF})
          can_filters.append({"can_id": 0x7E0, "can_mask": 0x7E0})
          can_bus = can.interface.Bus(can_interface, bustype=can_bus_type,can_filters=can_filters)
          
          # Setup automatic printing of heard messages
          customListener = CustomListener()
          customListener.message_received_callback = handle_can_message
          can.Notifier(can_bus, [customListener])

          print ( "Starting thread to send obdii queries")
          send_obdii_queries()
          # Wait a short while before we start sending iot hub messages 
          # to give the module time to collect meaningful data from the can bus
          sleep(0.5)
          
          print ("Starting thread to send iothub messages")
          send_iothub_message()


        except Exception as e:
          print ("Error initializing CAN Bus: " + str(e) )

        while True:
            time.sleep(1)

    except IoTHubError as iothub_error:
        print ( "Unexpected error %s from IoTHub" % iothub_error )
        return
    except KeyboardInterrupt:
        print ( "IoTHubModuleClient sample stopped" )

if __name__ == '__main__':
    main(PROTOCOL)