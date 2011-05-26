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
        # make the client instance known to the factory
        self.factory.bot = self

    def joined(self, channel):
        print "Joined %s." % (channel,)

    def privmsg(self, user, channel, msg):
        # Do nothing with PRIVMSG's
        print "PRIVMSG: %s" % (msg,)
    
    def msgToChannel(self, msg):
        # Sends a message to the predefined channel
        print "Message sent to %s" % (self.factory.channel,)
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
        # UDP messages from MediaWiki arrive here and are relayed
        # to the ircbot created by the bot factory.
        print "Received %r from %s:%d" % (data, host, port)
        print "Relaying msg to IRCClient in %s" % (self.botfactory,)
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

        # Start IRC-bot on IRCNet.
        reactor.connectTCP('irc.ifi.uio.no', 6667, snurr)

        reactor.run()
    else:
        print "Usage: python %s <IRC_CHANNEL> <MEDIAWIKI_PORT>" % (sys.argv[0],)
