Class overview
==============

This is a broad overview of Vumi's classes, and their relationships with one
another.

Vumi
----

.. inheritance-diagram::
   vumi.application.base
   vumi.application.http_relay
   vumi.application.session
   vumi.dispatchers.base
   vumi.dispatchers.simple.dispatcher
   vumi.service
   vumi.session
   vumi.workers.session.worker

:mod:`vumi.transports`
~~~~~~~~~~~~~~~~~~~~~~

.. inheritance-diagram::
   vumi.transports.api.api
   vumi.transports.api.oldapi
   vumi.transports.base
   vumi.transports.cellulant.cellulant
   vumi.transports.failures
   vumi.transports.httprpc.httprpc
   vumi.transports.infobip.infobip
   vumi.transports.integrat.integrat
   vumi.transports.integrat.utils
   vumi.transports.irc.irc
   vumi.transports.opera.opera
   vumi.transports.opera.utils
   vumi.transports.scheduler
   vumi.transports.smpp.client
   vumi.transports.smpp.server
   vumi.transports.smpp.service
   vumi.transports.smpp.transport
   vumi.transports.telnet.telnet
   vumi.transports.truteq.truteq
   vumi.transports.twitter.twitter
   vumi.transports.vas2nets.transport_stubs
   vumi.transports.vas2nets.vas2nets
   vumi.transports.vodacom_messaging.vodacom_messaging
   vumi.transports.xmpp.xmpp

:mod:`vumi.blinkenlights`
~~~~~~~~~~~~~~~~~~~~~~~~~

.. inheritance-diagram::
   vumi.blinkenlights.message20110707
   vumi.blinkenlights.message20110818
   vumi.blinkenlights.metrics
   vumi.blinkenlights.metrics_workers

Support
~~~~~~~

.. inheritance-diagram::
   vumi.database.base
   vumi.errors
   vumi.log
   vumi.message
   vumi.options
   vumi.scripts.inject_messages
   vumi.scripts.parse_smpp_log_messages
   vumi.status
   vumi.utils

Demos
-----

.. inheritance-diagram::
   vumi.demos.hangman
   vumi.demos.ircbot
   vumi.demos.rps
   vumi.demos.tictactoe
   vumi.demos.wikipedia
   vumi.demos.words

Deprecated
----------

:mod:`vumi.webapp`
~~~~~~~~~~~~~~~~~~

.. deprecated:: 0.3.0

.. inheritance-diagram::
   vumi.webapp.api.base.handlers
   vumi.webapp.api.base.urls
   vumi.webapp.api.client
   vumi.webapp.api.fields
   vumi.webapp.api.forms
   vumi.webapp.api.gateways.clickatell.handlers
   vumi.webapp.api.gateways.clickatell.urls
   vumi.webapp.api.gateways.opera.backend
   vumi.webapp.api.gateways.opera.handlers
   vumi.webapp.api.gateways.opera.urls
   vumi.webapp.api.gateways.smpp.handlers
   vumi.webapp.api.gateways.smpp.urls
   vumi.webapp.api.handlers
   vumi.webapp.api.models
   vumi.webapp.api.signals
   vumi.webapp.api.tasks
   vumi.webapp.api.urls
   vumi.webapp.api.utils
   vumi.webapp.api.views
   vumi.webapp.application
   vumi.webapp.prelaunch.models
   vumi.webapp.prelaunch.views
