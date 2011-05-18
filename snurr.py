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
        print "PRIVMSG: %s" (msg,)
    
    def msgToChannel(self, msg):
        self.msg(self.factory.channel, msg)

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

    def __init__(self, ircbot):
        self.ircbot = ircbot

    def startProtocol(self):
        print "Listening for Recent Changes from MediaWiki"

    def stopProtocol(self):
        print "MediWiki listener stopped"

    def datagramRecieved(self, data, (host, port)):
        print "received %r from %s:%d" % (data, host, port)
        print "relaying to ircbot %s" % (self.ircbot,)
        self.ircbot.msgToChannel(data)
        print self,data,host,port

if __name__ == "__main__":
    if len(sys.argv) == 2:
        chan = sys.argv[1]
        snurr = SnurrBotFactory('#' + chan)
        wiki = MediaWikiProtocol(snurr)

		# Start the MediaWiki listener.
        reactor.listenUDP(41894, wiki)

		# Start IRC-bot.
        reactor.connectTCP('irc.ifi.uio.no', 6667, snurr)

        reactor.run()
    else:
        print "Usage: %s IRC_CHANNEL" % (sys.argv[0],)
