#!/usr/bin/env python
# encoding: utf-8
import optparse
import subprocess 
import time
from datetime import datetime

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor, ssl
from twisted.enterprise import adbapi

class SnurrBot(irc.IRCClient):
    def __init__(self):
        self.actions = IRCActions(self)

    def _get_nickname(self):
        return self.factory.nickname

    nickname = property(_get_nickname)

    def __unicode__(self):
        return "SnurrBot:%s" % (nickname,)

    def signedOn(self):
        self.join(self.factory.channel)
        log("Signed on as %s." % (self.nickname,))
        # make the client instance known to the factory
        self.factory.bot = self

    def joined(self, channel):
        log("Joined %s." % (channel,))

    def privmsg(self, user, channel, msg):
        # Handle command strings.
        if msg.startswith("!"):
            self.actions.new(msg[1:], user, channel)
        log("PRIVMSG: %s: %s" % (user,msg,))
    
    def msgToChannel(self, msg):
        # Sends a message to the predefined channel
        log("Message sent to %s" % (self.factory.channel,))
        if len(msg) > 0:
            self.say(self.factory.channel, msg, length=512)


class SnurrBotFactory(protocol.ClientFactory):
    protocol = SnurrBot

    def __init__(self, channel, nickname='snurr'):
        self.channel = channel
        self.nickname = nickname

    def __unicode__(self):
        return "SnurrBotFactory"

    def clientConnectionLost(self, connector, reason):
        log("Lost connection (%s), reconnecting." % (reason,))
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        log("Could not connect: (%s), retrying." % (reason,))

class UDPListener(protocol.DatagramProtocol):

    def __init__(self, botfactory):
        self.botfactory = botfactory

    def startProtocol(self):
        log("Listening for messages.")

    def stopProtocol(self):
        log("Listener stopped")

    def datagramReceived(self, data, (host, port)):
        # UDP messages (from MediaWiki f.ex) arrive here and are relayed
        # to the ircbot created by the bot factory.
        log("Received %r from %s:%d" % (data, host, port))
        log("Relaying msg to IRCClient in %s" % (self.botfactory,))
        if self.botfactory.bot:
            self.botfactory.bot.msgToChannel(data)

class IRCActions():
    def __init__(self, bot):
        self.bot = bot
        self.dbpool = self._get_dbpool()

    def _get_dbpool(self):
        # Setup an async db connection
        # CONFIG:
        return adbapi.ConnectionPool("MySQLdb",
            host="snes.neuf.no", user="driftlogg",
            passwd="", db="driftlogg")

    def ping(self, host):
        # TODO rewrite async
        try:
            command = "ping -W 1 -c 1 " + host
            retcode = subprocess.call(command.split(),stdout=subprocess.PIPE)
            if retcode == 0:
                return host + " pinger fint den :P"
            elif retcode == 2:
                return host + " pinger ikke :("
            else:
               print retcode
               return "ping returned: " + str(retcode)
        except OSError, e:
            log("Execution failed:" + str(e))
            return "feil med ping:" + str(e)

    def help(self):
        text = ""
        text += "Command: !help\n"
        text += "   This help message\n"
        text += "Command: !log DESCRIPTION\n"
        text += "   Add new entry in log\n"
        text += "Command: !lastlog\n"
        text += "   Last log entry\n"
        text += "Command: !ping HOST\n"
        text += "   Ping target host"
        return text

    def new(self, msg, user, channel):
        nick = user.split('!', 1)[0] # Strip out hostmask

        # Process the commands
        parts = msg.split()
        if parts[0] == "ping" and len(parts) == 2:
            self.bot.msgToChannel(self.ping(parts[1]))
        elif parts[0] == "help" and len(parts) == 1:
            self.bot.msgToChannel(self.help())
        elif parts[0] == "log" and len(parts) == 2:
            # set_log_entry should create a deferred and
            # the callback should fire when the db returns.
            self.set_log_entry(nick, msg).addCallback(self.msg_log_entry)
        elif parts[0] == "lastlog" and len(parts) == 1:
            # ...same as above
            self.get_lastlog().addCallback(self.msg_lastlog)
        else:
            self.bot.msgToChannel("Need !help " + nick + "?")

    def set_log_entry(self, nick, entry):
        sql = """INSERT INTO driftslogg (time, user, log) 
                 VALUES(NOW(), %s, %s)""", (nick, entry)
        return self.dbpool.runQuery(sql)

    def msg_log_entry(self, result):
        if not result:
            return "Kunne ikke oppdatere driftslogg, er db oppe?"
        else:
            return "Yes sir! Driftslogg oppdatert."

    def get_lastlog(self):
        sql = "SELECT * FROM driftslogg ORDER BY time DESC LIMIT 3"
        return self.dbpool.runQuery(sql)

    def msg_lastlog(self, log_entries):
        for i,entry in enumerate(log_entries, start=1):
            self.bot.msgToChannel(str(i) +
                                  ":" + entry[2] +
                                  " (" + entry[1] + ", " +
                                  str(time.ctime(entry[0])) + ")")


def log(message):
    now = datetime.now().strftime("%b %d %H:%M:%S")
    print "{0} {1}".format(now, message)

def setup_and_parse_options():
    parser = optparse.OptionParser(description='Pipes UDP-messages to an IRC-channel.',
                                   usage=usage())
    parser.add_option('-c', '--connect', metavar='SERVER',
                      help='IRC server (default: irc.ifi.uio.no)', default='irc.ifi.uio.no')
    parser.add_option('-p', '--port', metavar='PORT', type=int,
                      help='IRC server port (default: 6667)', default=6667)
    parser.add_option('-s','--ssl', action='store_true',
                      help='connect with SSL (default: False)', default=False)
    parser.add_option('-l', '--listen_port', metavar='LISTEN_PORT', type=int,
                      help='UDP listen port (default: 55666)', default=55666)
    return parser.parse_args()

def usage():
    return 'Usage: python snurr.py [-h] [options] CHANNEL'

if __name__ == "__main__":
    options, args = setup_and_parse_options()

    if len(args) != 1:
        print usage()
        exit()
    snurr = SnurrBotFactory('#' + args[0])
    listener = UDPListener(snurr)

    # Start the listener.
    reactor.listenUDP(options.listen_port, listener)

    # Start IRC-bot on specified server and port.
    if options.ssl:
        reactor.connectSSL(options.connect, options.port, snurr, ssl.ClientContextFactory())
    else:
        reactor.connectTCP(options.connect, options.port, snurr)
    reactor.run()
