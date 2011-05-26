import sys
from twisted.words.protocols import irc
from twisted.internet import protocol, reactor


class SnurrBot(irc.IRCClient):

    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    def __unicode__(self):
        return "SnurrBot:%s" % (nickname,)

    def signedOn(self):
        self.join(self.factory.channel)
        print "Signed on as %s." % (self.nickname,)
        self.factory.bot = self

    def joined(self, channel):
        print "Joined %s." % (channel,)

    def privmsg(self, user, channel, msg):
        print "PRIVMSG: %s" % (msg,)
    
    def msgToChannel(self, msg):
        print "PRIVMSG %s: '%s'" % (self.factory.channel, msg,)
        self.say(self.factory.channel, msg, length=512)


class SnurrBotFactory(protocol.ClientFactory):
    protocol = SnurrBot

    def __init__(self, channel, nickname='snurr'):
        self.channel = channel
        self.nickname = nickname

    def __unicode__(self):
        return "SnurrBotFactory"

    def clientConnectionLost(self, connector, reason):
        print "Lost connection (%s), reconnecting." % (reason,)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Could not connect: %s" % (reason,)

class MediaWikiProtocol(protocol.DatagramProtocol):

    def __init__(self, botfactory):
        self.botfactory = botfactory

    def startProtocol(self):
        print "Listening for Recent Changes from MediaWiki"

    def stopProtocol(self):
        print "MediWiki listener stopped"

    def datagramReceived(self, data, (host, port)):
        print "received %r from %s:%d" % (data, host, port)
        print "Relaying msg IRCClient in %s" % (self.botfactory,)
        if self.botfactory.bot:
            self.botfactory.bot.msgToChannel("EDBWiki: " + data)

if __name__ == "__main__":
    if len(sys.argv) == 3:
        chan = sys.argv[1]
        wiki_port = int(sys.argv[2])

        snurr = SnurrBotFactory('#' + chan)
        wiki = MediaWikiProtocol(snurr)

		# Start the MediaWiki listener.
        reactor.listenUDP(wiki_port, wiki)

		# Start IRC-bot.
        reactor.connectTCP('irc.ifi.uio.no', 6667, snurr)

        reactor.run()
    else:
        print "Usage: %s [IRC_CHANNEL] [MEDIAWIKI_PORT]" % (sys.argv[0],)
