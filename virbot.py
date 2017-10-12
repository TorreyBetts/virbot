import commands
import numerics
import re
import socket
import sys
import json
import hues

def getRequester(usesPrefix, text):
    searchPattern = "(?<=:).+(?=!)" if usesPrefix else ".+(?=!)"
    requestMatches = re.search(searchPattern, text, re.I)
    if requestMatches:
        return str(requestMatches.group())
    return ""

def processSentMessage(message):
    hues.log(hues.huestr("[SENT] " + message).magenta.bold.colorized)

def processServerMessage(irc, host, numeric, user, message):
    if config["numerics"].get(numeric, None) != None:
        commandMethod = getattr(numerics, config["numerics"][numeric])
        commandMethod(irc, config, host, user, message)
    elif numeric == "NOTICE":
        hues.log(hues.huestr("[NOTICE] " + message).blue.bold.colorized)
    else:
        hues.log(hues.huestr("[SERVER] " + message).cyan.bold.colorized)

def processChatMessage(irc, sender, command, receiver, message):
    message = message[1:] if message.startswith(":") else message
    requester = getRequester(False, sender) if receiver == nick else receiver
    commandLookup = message.split()[0]

    if config["botcommands"].get(commandLookup, None) != None:
        hues.log(hues.huestr("[RECEIVED] " + commandLookup + " command FROM " + requester + " (" + sender + ")").green.colorized)
        commandMethod = getattr(commands, config["botcommands"][commandLookup])
        if (len(message.split()) == 1):
            commandMethod(irc, config, requester, None)
        else:
            commandMethod(irc, config, requester, message.replace(commandLookup, ""))

def main(argv):
    sentUser = False
    sentNick = False

    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    irc.connect((config["server"]["name"], config["server"]["port"]))
    try:
        while True:
            data = irc.recv(2048)
            if len(data) <= 0:
                continue

            if config["debugmode"]:
                print data

            if data.startswith('ERROR') == True:
                #TODO: Add proper error output and reconnection if configured
                hues.log(hues.huestr(data).magenta.bold.colorized)
                sys.exit()

            if data.find('PING') != -1 and data.find(u"\u0001PING") == -1:
                irc.send(config["irccommands"]["pong"].format(data.split()[1]))
                processSentMessage("PONG to SERVER" + " (" + data.split()[1][1:] + ")")
                continue

            if data.find(u"\u0001PING") != -1:
                requester = getRequester(True, data)
                if requester != None:
                    pingindex = data.index(u"\u0001PING")
                    pingreply = data[pingindex:]
                    pingreply = pingreply.replace("\r\n", "")
                    irc.send(u"NOTICE " + requester + u" :" + pingreply + u"\u0001\n")
                    processSentMessage("PONG to " + requester + " (" + pingreply[6:] + ")")
                    continue

            if sentUser == False:
                irc.send(config["irccommands"]["user"].format(nick, nick, nick, realname))
                sentUser = True
                processSentMessage("USER")
                continue

            if sentUser and sentNick == False:
                irc.send(config["irccommands"]["nick"].format(nick))
                sentNick = True
                processSentMessage("NICK" + " (" + nick + ")")
                continue

            for lineText in data.split("\r\n"):
                messageMatches = re.search("(:[\\w\\.]+\\s)(\\d{3}\\s|[A-Z]+\\s)([\\w]+\\s)(.+)", lineText)
                if messageMatches:
                    processServerMessage(irc, messageMatches.group(1)[1:-1], messageMatches.group(2)[:-1],
                                         messageMatches.group(3)[:-1], messageMatches.group(4)[1:])

                messageMatches = re.search("(:.+@.+\\s)([A-Z]+\\s)([\\w#]+\\s)(:?.+)", lineText)
                if messageMatches:
                    processChatMessage(irc, messageMatches.group(1)[1:-1], messageMatches.group(2)[:-1],
                                       messageMatches.group(3)[:-1], messageMatches.group(4))

    except KeyboardInterrupt:
        commands.kill_command(irc, config, None, None)

if __name__ == "__main__":
    reload(sys)
    sys.setdefaultencoding('utf8')

    with open('config.json', 'r') as configFile:
        config = json.load(configFile)

    nick = config["nickname"]
    realname = config["realname"]

    main(sys.argv[1:])
