import logging
import re
import subprocess
from datetime import datetime
from time import sleep

import paho.mqtt.client as MQTTClient
import requests
from pydantic import BaseSettings
from rich.logging import RichHandler


class Settings(BaseSettings):
    """ Model for the app configuartion """

    # Logging settings
    logging_level: int = logging.INFO

    # Commands for the temps
    cpu_temp_file: str = '/sys/class/thermal/thermal_zone0/temp'
    gpu_temp_command: str = '/usr/bin/vcgencmd measure_temp'

    # MQTT settings
    mqtt_broker_port: int = 1883
    mqtt_broker: str
    mqtt_client_id: str
    mqtt_username: str
    mqtt_password: str
    mqtt_topic_cpu: str
    mqtt_topic_gpu: str

    class Config:
        env_prefix = 'rpi_temp_'


def worker() -> None:
    """ The worker function """

    # Get the configuration
    settings = Settings()

    logger = logging.getLogger('Worker')
    cpu_temp: float | None = None
    gpu_temp: float | None = None

    # Get the CPU temperature
    logger.info('Reading CPU temperature from file')
    with open(settings.cpu_temp_file, 'r', encoding='utf-8') as temp_file:
        temp = temp_file.read()
        cpu_temp = float(temp) / 1000
        logger.info('Temperature for the CPU: %s', cpu_temp)

    # Get the GPU temperature
    logger.info('Reading CPU temperature from file')
    output = subprocess.check_output(
        settings.gpu_temp_command.split()).decode('utf-8')
    # Get the temperature
    gpu_temp = float(re.findall(r'temp\=([0-9]+\.[0-9])', output)[0])
    logger.info('Temperature for the GPU: %s', gpu_temp)

    # Update MQTT
    mqtt = MQTTClient.Client(client_id=settings.mqtt_client_id)
    mqtt.username_pw_set(username=settings.mqtt_username,
                         password=settings.mqtt_password)
    mqtt.connect(host=settings.mqtt_broker,
                 port=settings.mqtt_broker_port)
    mqtt.publish(topic=settings.mqtt_topic_cpu, payload=cpu_temp)
    mqtt.publish(topic=settings.mqtt_topic_gpu, payload=gpu_temp)
    mqtt.disconnect()


def rpi_temp() -> None:
    """ Main method for the script """
    # Get the configuration
    settings = Settings()

    # Configure logging
    logging.basicConfig(
        level=settings.logging_level,
        format='%(name)s: %(message)s',
        datefmt="[%X]",
        handlers=[RichHandler()]
    )

    last_minute = 0

    while True:
        current_time = datetime.now()
        if current_time.minute != last_minute:
            last_minute = current_time.minute
            worker()
        sleep(5)


if __name__ == '__main__':
    # Run the main function
    rpi_temp()
