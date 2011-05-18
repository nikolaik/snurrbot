import sys
from twisted.words.protocols import irc
from twisted.internet import protocol, reactor


class SnurrBot(irc.IRCClient):
    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    def signedOn(self):
        self.join(self.factory.channel)
        print "Signed on as %s." % (self.nickname,)

    def joined(self, channel):
        print "Joined %s." % (channel,)

    def privmsg(self, user, channel, msg):
        print msg

class SnurrBotFactory(protocol.ClientFactory):
    protocol = SnurrBot

    def __init__(self, channel, nickname='snurr'):
        self.channel = channel
        self.nickname = nickname

    def clientConnectionLost(self, connector, reason):
        print "Lost connection (%s), reconnecting." % (reason,)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Could not connect: %s" % (reason,)

class MediaWikiProtocol(protocol.DatagramProtocol):
    def startProtocol(self):
        print "Listening for wikiChanges"
        reactor.connectTCP('irc.ifi.uio.no', 6667, SnurrBotFactory('#' + chan))

    def stopProtocol(self):
        print "MediWiki listener stopped"

    def datagramRecieved(self, data, (host, port)):
        print "received %r from %s:%d" % (data, host, port)
        self.transport.write(data, (host, port))
        print self,data,host,port

if __name__ == "__main__":
    if len(sys.argv) == 1:
        chan = sys.argv[1]
        reactor.listenUDP(4321, MediaWikiProtocol())
        reactor.run()
    else:
        print "Usage: %s IRC_CHANNEL" % (sys.argv[0],)
