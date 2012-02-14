from datetime import datetime

from twisted.trial.unittest import TestCase
from twisted.internet.defer import inlineCallbacks, returnValue

from vumi.message import TransportUserMessage, TransportEvent
from vumi.dispatchers.base import BaseDispatchWorker, ToAddrRouter
from vumi.tests.utils import get_stubbed_worker, FakeRedis
from vumi.tests.fake_amqp import FakeAMQPBroker


class DispatcherTestCase(TestCase):

    """
    This is a base class for testing dispatcher workers.

    """

    # base timeout of 5s for all dispatcher tests
    timeout = 5

    dispatcher_name = "sphex_dispatcher"
    dispatcher_class = None

    def setUp(self):
        self._workers = []
        self._amqp = FakeAMQPBroker()

    def tearDown(self):
        for worker in self._workers:
            worker.stopWorker()

    @inlineCallbacks
    def get_dispatcher(self, config, cls=None, start=True):
        """
        Get an instance of a dispatcher class.

        :param config: Config dict.
        :param cls: The Dispatcher class to instantiate.
                    Defaults to :attr:`dispatcher_class`
        :param start: True to start the displatcher (default), False otherwise.

        Some default config values are helpfully provided in the
        interests of reducing boilerplate:

        * ``dispatcher_name`` defaults to :attr:`self.dispatcher_name`
        """

        if cls is None:
            cls = self.dispatcher_class
        config.setdefault('dispatcher_name', self.dispatcher_name)
        worker = get_stubbed_worker(cls, config, self._amqp)
        self._workers.append(worker)
        if start:
            yield worker.startWorker()
        returnValue(worker)

    def mkmsg_in(self, content='hello world', message_id='abc',
                 to_addr='9292', from_addr='+41791234567',
                 session_event=None, transport_type=None,
                 helper_metadata=None, transport_metadata=None,
                 transport_name=None):
        if helper_metadata is None:
            helper_metadata = {}
        if transport_metadata is None:
            transport_metadata = {}
        return TransportUserMessage(
            from_addr=from_addr,
            to_addr=to_addr,
            message_id=message_id,
            transport_name=transport_name,
            transport_type=transport_type,
            transport_metadata=transport_metadata,
            helper_metadata=helper_metadata,
            content=content,
            session_event=session_event,
            timestamp=datetime.now(),
            )

    def mkmsg_out(self, content='hello world', message_id='1',
                  to_addr='+41791234567', from_addr='9292',
                  session_event=None, in_reply_to=None,
                  transport_type=None, transport_metadata=None,
                  transport_name=None):
        if transport_metadata is None:
            transport_metadata = {}
        params = dict(
            to_addr=to_addr,
            from_addr=from_addr,
            message_id=message_id,
            transport_name=transport_name,
            transport_type=transport_type,
            transport_metadata=transport_metadata,
            content=content,
            session_event=session_event,
            in_reply_to=in_reply_to,
            )
        return TransportUserMessage(**params)

    def get_dispatched_messages(self, transport_name, direction='outbound'):
        return self._amqp.get_messages('vumi', '%s.%s' % (
            transport_name, direction))

    def wait_for_dispatched_messages(self, transport_name, amount,
                                        direction='outbound'):
        return self._amqp.wait_messages('vumi', '%s.%s' % (
            transport_name, direction), amount)

    def dispatch(self, message, transport_name, direction='inbound',
                    exchange='vumi'):
        rkey = '%s.%s' % (transport_name, direction)
        self._amqp.publish_message(exchange, rkey, message)
        return self._amqp.kick_delivery()


class MessageMakerMixIn(object):
    """TestCase mixin for creating transport messages."""

    def mkmsg_ack(self, transport_name, **kw):
        event_kw = dict(
            event_type='ack',
            user_message_id='1',
            sent_message_id='abc',
            transport_name=transport_name,
            transport_metadata={},
            )
        event_kw.update(kw)
        return TransportEvent(**event_kw)

    def mkmsg_in(self, transport_name, content='foo', **kw):
        msg_kw = dict(
            from_addr='+41791234567',
            to_addr='9292',
            transport_name=transport_name,
            transport_type='sms',
            transport_metadata={},
            content=content,
            )
        msg_kw.update(kw)
        return TransportUserMessage(**msg_kw)

    def mkmsg_out(self, transport_name, content='hello world', **kw):
        msg_kw = dict(
            to_addr='+41791234567',
            from_addr='9292',
            transport_name=transport_name,
            transport_type='sms',
            transport_metadata={},
            content=content,
            )
        msg_kw.update(kw)
        return TransportUserMessage(**msg_kw)


class TestBaseDispatchWorker(TestCase, MessageMakerMixIn):

    @inlineCallbacks
    def setUp(self):
        config = {
            "transport_names": [
                "transport1",
                "transport2",
                "transport3",
                ],
            "exposed_names": [
                "app1",
                "app2",
                "app3",
                ],
            "router_class": "vumi.dispatchers.base.SimpleDispatchRouter",
            "route_mappings": {
                "transport1": ["app1"],
                "transport2": ["app2"],
                "transport3": ["app1", "app3"]
                },
            }
        self.worker = get_stubbed_worker(BaseDispatchWorker, config)
        self._amqp = self.worker._amqp_client.broker
        yield self.worker.startWorker()

    @inlineCallbacks
    def tearDown(self):
        yield self.worker.stopWorker()

    def dispatch(self, message, rkey=None, exchange='vumi'):
        if rkey is None:
            rkey = self.rkey('outbound')
        self._amqp.publish_message(exchange, rkey, message)
        return self._amqp.kick_delivery()

    def assert_messages(self, rkey, msgs):
        self.assertEqual(msgs, self._amqp.get_messages('vumi', rkey))

    def assert_no_messages(self, *rkeys):
        for rkey in rkeys:
            self.assertEqual([], self._amqp.get_messages('vumi', rkey))

    def clear_dispatched(self):
        self._amqp.dispatched.clear()

    @inlineCallbacks
    def test_inbound_message_routing(self):
        msg = self.mkmsg_in('transport1')
        yield self.dispatch(msg, 'transport1.inbound')
        self.assert_messages('app1.inbound', [msg])
        self.assert_no_messages('app1.event', 'app2.inbound', 'app2.event',
                                'app3.inbound', 'app3.event')

        self.clear_dispatched()
        msg = self.mkmsg_in('transport2')
        yield self.dispatch(msg, 'transport2.inbound')
        self.assert_messages('app2.inbound', [msg])
        self.assert_no_messages('app1.inbound', 'app1.event', 'app2.event',
                                'app3.inbound', 'app3.event')

        self.clear_dispatched()
        msg = self.mkmsg_in('transport3')
        yield self.dispatch(msg, 'transport3.inbound')
        self.assert_messages('app1.inbound', [msg])
        self.assert_messages('app3.inbound', [msg])
        self.assert_no_messages('app1.event', 'app2.inbound', 'app2.event',
                                'app3.event')

    @inlineCallbacks
    def test_inbound_event_routing(self):
        msg = self.mkmsg_ack('transport1')
        yield self.dispatch(msg, 'transport1.event')
        self.assert_messages('app1.event', [msg])
        self.assert_no_messages('app1.inbound', 'app2.event', 'app2.inbound',
                                'app3.event', 'app3.inbound')

        self.clear_dispatched()
        msg = self.mkmsg_ack('transport2')
        yield self.dispatch(msg, 'transport2.event')
        self.assert_messages('app2.event', [msg])
        self.assert_no_messages('app1.event', 'app1.inbound', 'app2.inbound',
                                'app3.event', 'app3.inbound')

        self.clear_dispatched()
        msg = self.mkmsg_ack('transport3')
        yield self.dispatch(msg, 'transport3.event')
        self.assert_messages('app1.event', [msg])
        self.assert_messages('app3.event', [msg])
        self.assert_no_messages('app1.inbound', 'app2.event', 'app2.inbound',
                                'app3.inbound')

    @inlineCallbacks
    def test_outbound_message_routing(self):
        msgs = [self.mkmsg_out('transport1') for _ in range(3)]
        yield self.dispatch(msgs[0], 'app1.outbound')
        yield self.dispatch(msgs[1], 'app2.outbound')
        yield self.dispatch(msgs[2], 'app3.outbound')
        self.assert_messages('transport1.outbound', msgs)
        self.assert_no_messages('transport2.outbound', 'transport3.outbound')

        self.clear_dispatched()
        msgs = [self.mkmsg_out('transport2') for _ in range(3)]
        yield self.dispatch(msgs[0], 'app1.outbound')
        yield self.dispatch(msgs[1], 'app2.outbound')
        yield self.dispatch(msgs[2], 'app3.outbound')
        self.assert_messages('transport2.outbound', msgs)
        self.assert_no_messages('transport1.outbound', 'transport3.outbound')

        self.clear_dispatched()
        msgs = [self.mkmsg_out('transport3') for _ in range(3)]
        yield self.dispatch(msgs[0], 'app1.outbound')
        yield self.dispatch(msgs[1], 'app2.outbound')
        yield self.dispatch(msgs[2], 'app3.outbound')
        self.assert_messages('transport3.outbound', msgs)
        self.assert_no_messages('transport1.outbound', 'transport2.outbound')


class DummyDispatcher(object):

    class DummyPublisher(object):
        def __init__(self):
            self.msgs = []

        def publish_message(self, msg):
            self.msgs.append(msg)

    def __init__(self, config):
        self.transport_publisher = {}
        for transport in config['transport_names']:
            self.transport_publisher[transport] = self.DummyPublisher()
        self.exposed_publisher = {}
        for exposed in config['exposed_names']:
            self.exposed_publisher[exposed] = self.DummyPublisher()


class TestToAddrRouter(TestCase, MessageMakerMixIn):
    def setUp(self):
        self.config = {
            'transport_names': ['transport1'],
            'exposed_names': ['app1', 'app2'],
            'toaddr_mappings': {
                'app1': 'to:.*:1',
                'app2': 'to:app2',
                },
            }
        self.dispatcher = DummyDispatcher(self.config)
        self.router = ToAddrRouter(self.dispatcher, self.config)

    def test_dispatch_inbound_message(self):
        msg = self.mkmsg_in(to_addr='to:foo:1', transport_name='transport1')
        self.router.dispatch_inbound_message(msg)
        publishers = self.dispatcher.exposed_publisher
        self.assertEqual(publishers['app1'].msgs, [msg])
        self.assertEqual(publishers['app2'].msgs, [])

    def test_dispatch_outbound_message(self):
        msg = self.mkmsg_out(transport_name='transport1')
        self.router.dispatch_outbound_message(msg)
        publishers = self.dispatcher.transport_publisher
        self.assertEqual(publishers['transport1'].msgs, [msg])


class TestTransportToTransportRouter(TestCase, MessageMakerMixIn):

    @inlineCallbacks
    def setUp(self):
        config = {
            "transport_names": [
                "transport1",
                "transport2",
                ],
            "exposed_names": [],
            "router_class": "vumi.dispatchers.base.TransportToTransportRouter",
            "route_mappings": {
                "transport1": ["transport2"],
                },
            }
        self.worker = get_stubbed_worker(BaseDispatchWorker, config)
        self._amqp = self.worker._amqp_client.broker
        yield self.worker.startWorker()

    @inlineCallbacks
    def tearDown(self):
        yield self.worker.stopWorker()

    def dispatch(self, message, rkey=None, exchange='vumi'):
        if rkey is None:
            rkey = self.rkey('outbound')
        self._amqp.publish_message(exchange, rkey, message)
        return self._amqp.kick_delivery()

    def assert_messages(self, rkey, msgs):
        self.assertEqual(msgs, self._amqp.get_messages('vumi', rkey))

    def assert_no_messages(self, *rkeys):
        for rkey in rkeys:
            self.assertEqual([], self._amqp.get_messages('vumi', rkey))

    def clear_dispatched(self):
        self._amqp.dispatched.clear()

    @inlineCallbacks
    def test_inbound_message_routing(self):
        msg = self.mkmsg_in('transport1')
        yield self.dispatch(msg, 'transport1.inbound')
        self.assert_messages('transport2.outbound', [msg])
        self.assert_no_messages('transport2.inbound', 'transport1.outbound')


class UserGroupingRouterTestCase(DispatcherTestCase):

    dispatcher_class = BaseDispatchWorker
    transport_name = 'test_transport'

    @inlineCallbacks
    def setUp(self):
        yield super(UserGroupingRouterTestCase, self).setUp()
        self.config = {
            'dispatcher_name': 'user_group_dispatcher',
            'router_class': 'vumi.dispatchers.base.UserGroupingRouter',
            'transport_names': [
                self.transport_name,
            ],
            'exposed_names': [
                'app1',
                'app2',
            ],
            'group_mappings': {
                'group1': 'app1',
                'group2': 'app2',
                },
            }

        self.fake_redis = FakeRedis()
        self.dispatcher = yield self.get_dispatcher(self.config)
        self.router = self.dispatcher._router
        self.router.r_server = self.fake_redis
        self.router.setup_routing()

    def test_group_assignment(self):
        msg = self.mkmsg_in(transport_name=self.transport_name)
        selected_group = self.router.get_group_for_user(msg.user())
        self.assertTrue(selected_group)
        for i in range(0, 10):
            group = self.router.get_group_for_user(msg.user())
            self.assertEqual(group, selected_group)

    def test_round_robin_group_assignment(self):
        messages = [self.mkmsg_in(transport_name=self.transport_name,
                        from_addr='from_%s' % (i,)) for i in range(0, 4)]
        groups = [self.router.get_group_for_user(message.user())
                    for message in messages]
        self.assertEqual(groups, [
            'group1',
            'group2',
            'group1',
            'group2',
        ])

    @inlineCallbacks
    def test_routing_to_application(self):
        # generate 4 messages, 2 from each user
        msg1 = self.mkmsg_in(transport_name=self.transport_name,
                                from_addr='from_1')
        msg2 = self.mkmsg_in(transport_name=self.transport_name,
                                from_addr='from_2')
        msg3 = self.mkmsg_in(transport_name=self.transport_name,
                                from_addr='from_1')
        msg4 = self.mkmsg_in(transport_name=self.transport_name,
                                from_addr='from_2')
        # send them through to the dispatcher
        messages = [msg1, msg2, msg3, msg4]
        for message in messages:
            yield self.dispatch(message, transport_name=self.transport_name)

        app1_messages = self.get_dispatched_messages('app1',
                                                        direction='inbound')
        app2_messages = self.get_dispatched_messages('app2',
                                                        direction='inbound')
        self.assertEqual(app1_messages, [msg1, msg3])
        self.assertEqual(app2_messages, [msg2, msg4])

    @inlineCallbacks
    def test_routing_to_transport(self):
        app_msg = self.mkmsg_in(transport_name=self.transport_name,
                                from_addr='from_1')
        yield self.dispatch(app_msg, transport_name='app1',
                                direction='outbound')
        [transport_msg] = self.get_dispatched_messages(self.transport_name,
                                                direction='outbound')
        self.assertEqual(app_msg, transport_msg)
