from twisted.python import log
from twisted.python.log import logging
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor

from vumi.service import Worker, Consumer, Publisher
from vumi.workers.smpp.client import EsmeTransceiverFactory, EsmeTransceiver

import json


class SmppConsumer(Consumer):
    """
    This consumer creates the generic outbound SMPP transport.
    Anything published to the `vumi.smpp` exchange with
    routing key smpp.* (* == single word match, # == zero or more words)
    """
    exchange_name = "vumi.smpp"
    exchange_type = "topic"
    durable = False
    queue_name = "smpp"
    routing_key = "smpp.*"

    def __init__(self, send_callback):
        self.send = send_callback

    def consume_json(self, dictionary):
        log.msg("Consumed JSON %s" % dictionary)
        return self.send(**dictionary)

    def consume(self, message):
        if self.consume_json(json.loads(message.content.body)):
            self.ack(message)


class SmppPublisher(Publisher):
    """
    This publisher publishes all incoming SMPP messages to the
    `vumi.smpp` exchange, its default routing key is `smpp.fallback`
    """
    exchange_name = "vumi.smpp"
    exchange_type = "topic"             # -> route based on pattern matching
    routing_key = 'smpp.fallback'       # -> overriden in publish method
    durable = False                     # -> not created at boot
    auto_delete = False                 # -> auto delete if no consumers bound
    delivery_mode = 2                   # -> do not save to disk

    def publish_json(self, dictionary, **kwargs):
        log.msg("Publishing JSON %s with extra args: %s" % (dictionary, kwargs))
        super(SmppPublisher, self).publish_json(dictionary, **kwargs)


class SmppTransport(Worker):
    """
    The SmppTransport
    """

    def startWorker(self):
        log.msg("Starting the SmppTransport")

        # start the Smpp transport
        factory = EsmeTransceiverFactory()
        factory.loadDefaults(self.config)
        factory.setConnectCallback(self.esme_connected)
        factory.setDisconnectCallback(self.esme_disconnected)
        reactor.connectTCP(
                factory.defaults['host'],
                factory.defaults['port'],
                factory)

    @inlineCallbacks
    def esme_connected(self, client):
        log.msg("ESME Connected, adding handlers")
        self.esme_client = client
        self.esme_client.set_handler(self)

        # Start the publisher
        self.publisher = yield self.start_publisher(SmppPublisher)
        # Start the consumer, pass along the send_smpp callback for sending
        # back consumed AMQP messages over SMPP.
        self.consumer = yield self.start_consumer(SmppConsumer, self.send_smpp)


    @inlineCallbacks
    def esme_disconnected(self):
        log.msg("ESME Disconnected, stopping consumer")
        stop = yield self.consumer.stop()


    def send_smpp(self, msisdn, message, *args, **kwargs):
        print "Sending SMPP, to: %s, message: %s" % (msisdn, message)
        return self.esme_client.submit_sm(
                short_message = str(message),
                destination_addr = str(msisdn),
                )

    def sms_callback(self, *args, **kwargs):
        print "Got SMS:", args, kwargs

    def errback(self, *args, **kwargs):
        print "Got Error: ", args, kwargs

    def stopWorker(self):
        log.msg("Stopping the SMPPTransport")
