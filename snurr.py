import sys
from twisted.words.protocols import irc
from twisted.internet import protocol, reactor
from datetime import datetime

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
        log("Could not connect: %s" % (reason,))

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
    if len(sys.argv) == 4:
        chan = sys.argv[2]
        listen_port = int(sys.argv[3])

        snurr = SnurrBotFactory('#' + chan)
        listener = UDPListener(snurr)

        # Start the listener.
        reactor.listenUDP(listen_port, listener)

        # Start IRC-bot on IRCNet.
        reactor.connectTCP(sys.argv[1], 6667, snurr)

        reactor.run()
    else:
        print "Usage: python %s <IRC_SERVER> <IRC_CHANNEL> <UDP_PORT>" % (sys.argv[0],)
