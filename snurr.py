import optparse
from datetime import datetime
from twisted.words.protocols import irc
from twisted.internet import protocol, reactor, ssl

class SnurrBot(irc.IRCClient):

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
        # Do nothing with PRIVMSG's
        log("PRIVMSG: %s" % (msg,))
    
    def msgToChannel(self, msg):
        # Sends a message to the predefined channel
        log("Message sent to %s" % (self.factory.channel,))
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

def log(message):
    now = datetime.now().strftime("%b %d %H:%M:%S")
    print "{0} {1}".format(now, message)


if __name__ == "__main__":
    usage = 'Usage: python snurr.py [options] CHANNEL'
    parser = optparse.OptionParser(description='Pipes UDP-messages to an IRC-channel.',
                                   usage=usage)
    parser.add_option('-c', '--connect', metavar='SERVER',
                      help='IRC server (default: irc.ifi.uio.no)', default='irc.ifi.uio.no')
    parser.add_option('-p', '--port', metavar='PORT', type=int,
                      help='IRC server port (default: 6667)', default=6667)
    parser.add_option('-s','--ssl', action='store_true',
                      help='connect with SSL (default: False)', default=False)
    parser.add_option('-l', '--listen_port', metavar='LISTEN_PORT', type=int,
                      help='UDP listen port (default: 55666)', default=55666)
    options, args = parser.parse_args()

    if len(args) != 1:
        print usage
        exit()
    snurr = SnurrBotFactory('#' + args[0])
    listener = UDPListener(snurr)

    # Start the listener.
    reactor.listenUDP(options.listen_port, listener)

    # Start IRC-bot on specified server and port.
    if options.ssl:
        reactor.connectSSL(options.connect, options.port, snurr, ssl.ClientContextFactory())
    else:
        reactor.connectTCP(otions.connect, options.port, snurr)
    reactor.run()
