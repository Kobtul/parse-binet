import json
# from json import dumps, loads, JSONEncoder, JSONDecoder
import signal
# import pandas
# import ipwhois
import sys
from fileToAnalyze import BINETFLOW, COMPUTERSTOANALYZER
from WhoisCache import RadpCache

#from aenum import Enum

# import pickle
# import jsonpickle

import copy


SAVECACHE = True
USEWHOISDATA = True

timeIDSInCapture = []
result = {}
temp = {}
whoiscache = RadpCache ()
connectionCache = {}


def load_computers_to_analyze_from_file():
    ips = set()
    file = open (COMPUTERSTOANALYZER, 'r')
    for line in file:
        ip = line.split (':')[0]
        ips.add(ip)
    return ips

def intializeComputersToAnalyze(ips):
    for ip in ips:
        result[ip] = {}
        result[ip]['time'] = {}
        result[ip]['perflow'] = {}
        result[ip]['perflow']['consumerproducerratio'] = set()
        temp[ip] = {}
    for ip in temp:
        initializeTempHourDict (temp[ip])

def fillFeaturesClassFromTempClass(time):
    if not time:
        return
    dataDateID = time.split (' ')[0]
    dataHourID = time.split (' ')[1]
    # for ip in result:
    #     dictHourFeatures = result[ip]
    #     dictHourFeatures['time'][dataDateID][dataHourID] = {}

    for ip in result:

        ipfeaturesTimeDict = temp[ip]
        temp[ip] = {}

        #ipfeaturesTimeDict['hoursummary']['numberOfIPSContactedAsClient'] = len (ipfeaturesTimeDict['clientDictIPSContacted'])
        #ipfeaturesTimeDict['hoursummary']['numberOfIPSContactedAsServer'] = len (ipfeaturesTimeDict['setOfIPSContactedAsServer'])
        ipfeaturesTimeDict['hoursummary']['clientNumberOfNonAnsweredConnections'] = len (ipfeaturesTimeDict['clientDictOfNonAnsweredConnections'])
        ipfeaturesTimeDict['hoursummary']['serverNumberOfNonAnsweredConnections'] = len (ipfeaturesTimeDict['serverDictOfNonAnsweredConnections'])

        ipfeaturesTimeDict['hoursummary']['clientNummberOfDistinctCountries'] = len (ipfeaturesTimeDict['clientDictNumberOfDistinctCountries'])
        ipfeaturesTimeDict['hoursummary']['clientNummberOfDistinctOrganizations'] = len (ipfeaturesTimeDict['clientDictNumberOfDistinctOrganizations'])

        if dataDateID in result[ip]['time']:
            result[ip]['time'][dataDateID][dataHourID] = ipfeaturesTimeDict
        else:
            result[ip]['time'][dataDateID] = {}
            result[ip]['time'][dataDateID][dataHourID] = ipfeaturesTimeDict

def initializeTempHourDict(tempDict):
    tempDict['hoursummary'] = {}
    tempDict['hoursummary']['numberOfIPFlows'] = 0

    initializeNumberFeatureAsServerAsClient(tempDict['hoursummary'],'NumberOfIPFlows')
    initializeNumberFeatureAsServerAsClient(tempDict['hoursummary'],'TotalNumberOfTransferedData')

    #tempDict['clientDictIPSContacted'] = {}
    initializeDictFeatureAsServerAsClient (tempDict, 'DictOfNonAnsweredConnections')
    initializeDictFeatureAsServerAsClient (tempDict, 'DictNumberOfDistinctCountries')
    initializeDictFeatureAsServerAsClient (tempDict, 'DictNumberOfDistinctOrganizations')
    initializeDictFeatureAsServerAsClient (tempDict, 'DictClassBnetworks')

    initializePortFeatures(tempDict)

    tempDict['serverSourcePortDictIPsTCP'] = {}
    tempDict['serverSourcePortDictIPsUDP'] = {}

    tempDict['clientDestinationPortDictIPsTCP'] = {}
    tempDict['clientDestinationPortDictIPsUDP'] = {}

def initializeDictFeatureAsServerAsClient(dict,name):
    dict['client' + name] = {}
    dict['server' + name] = {}

def initializeNumberFeatureAsServerAsClient(dict,name):
    dict['client' + name] = 0
    dict['server' + name] = 0

def getCountryFromWhoisCache(ip):
    data = whoiscache.get_country_for_ip (ip)
    return data

def processLine(lineDict, lastTimeID):
    time = lineDict['StartTime']
    dataDateID = time.split ()[0]
    dataHourID = time.split ()[1].split (':')[0]
    actualDataId = dataDateID + " " + dataHourID
    if (actualDataId != lastTimeID):
        print(dataHourID)
        timeIDSInCapture.append (dataHourID)
        fillFeaturesClassFromTempClass (lastTimeID)
        for ip in temp:
            initializeTempHourDict (temp[ip])

    dur = lineDict['Dur']
    protocol = lineDict['Proto']
    ipFrom = lineDict['SrcAddr']
    sourcePort = lineDict['Sport']
    arrow = stripSpacesFromConnection (lineDict['Dir'])
    ipTo =  lineDict['DstAddr']
    dstPort = lineDict['Dport']
    connectionInformationState = lineDict['State']
    sTos = lineDict['sTos']
    dTos = lineDict['dTos']
    totalPakets = float(lineDict['TotPkts'])
    totBytes = float (lineDict['TotBytes'])
    srcBytes = float (lineDict['SrcBytes'])
    label = lineDict['Label']

    if (ipFrom in result):
        addFeaturesForIP('client',ipFrom,ipTo,lineDict,dur,protocol,sourcePort,dstPort,connectionInformationState,totalPakets,totBytes,srcBytes)
    elif (ipTo in result):
        addFeaturesForIP('server',ipTo,ipFrom,lineDict,dur,protocol,sourcePort,dstPort,connectionInformationState,totalPakets,totBytes,srcBytes)


    # TODO deal with _RA
    # print (line)
    return actualDataId

#ipDict is ip where the features are added
def addFeaturesForIP(clientorserver,ipDict,ipTarget,lineDict,dur,protocol,sourcePort,dstPort,connectionInformationState,totalPakets,totBytes,srcBytes):
    ipFeaturesTemp = temp[ipDict]
    ipFeaturesTemp['hoursummary'][clientorserver +'NumberOfIPFlows'] = ipFeaturesTemp['hoursummary'][clientorserver +'NumberOfIPFlows'] + 1
    # ipFeaturesTemp['hoursummary']['numberOfIPFlows'] = ipFeaturesTemp['hoursummary']['numberOfIPFlows'] + 1
    # per flow consumer/producer ratio
    result[ipDict]['perflow']['consumerproducerratio'].add (srcBytes / totBytes)
    if (detectConnection (connectionInformationState)):
        # ipFeaturesTemp['clientDictIPSContacted'].add (ipTo)
        #addFeaturesToDict (ipFeaturesTemp, 'clientDictIPSContacted', ipTarget, 1)
        if USEWHOISDATA:
            country = getCountryFromWhoisCache (ipTarget)
            addFeaturesToDict (ipFeaturesTemp, clientorserver +'DictNumberOfDistinctCountries', country, 1)
            addFeaturesToDict (ipFeaturesTemp, clientorserver +'DictNumberOfDistinctOrganizations',
                               whoiscache.get_organization_of_ip (ipTarget), 1)

            # ipFeaturesTemp['clientDictNumberOfDistinctOrganizations'].add (whoiscache.get_organization_of_ip (ipTo))
        classB = ipTarget.split ('.')[0] + '.' + ipTarget.split ('.')[1]

        # ipFeaturesTemp['clientDictClassBnetworks'].add (classB)
        addFeaturesToDict(ipFeaturesTemp, clientorserver +'DictClassBnetworks', classB, 1)

        ipFeaturesTemp['hoursummary'][clientorserver +'TotalNumberOfTransferedData'] = ipFeaturesTemp['hoursummary'][
                                                                        clientorserver +'TotalNumberOfTransferedData'] + totBytes
        fillDataToPortFeatures(clientorserver,protocol,ipFeaturesTemp,dstPort,ipTarget,sourcePort,totBytes,totalPakets,lineDict)
    elif (detectConnectionAttemptWithNoAnswer (connectionInformationState)):
        addFeaturesToDict (ipFeaturesTemp, clientorserver + 'DictOfNonAnsweredConnections', ipTarget, 1)
        #TODO Ask sebas if not answered connections should be in the histograms
        fillDataToPortFeatures(clientorserver,protocol,ipFeaturesTemp,dstPort,ipTarget,sourcePort,totBytes,totalPakets,lineDict)
        #TODO Check log of not used lines that should be catched by this


        # ipFeaturesTemp['clientDictOfNonAnsweredConnections'].add (ipTo)
    elif (detectPAPAsituation (connectionInformationState)):
        # print(line)
        # TODO fix this
        # try:
        #     conto = connectionCache[ipFrom]
        #     #if (conto != ipTo):
        #     if(not (ipTo in conto)):
        #         connectionCache[ipFrom].add (ipTo)
        #         ipFeaturesTemp['clientDictIPSContacted'].add (ipTo)
        #         ipFeaturesTemp['setClientNummberOfDistinctCountries'].add (getCountryFromWhoisCache (ipTo))
        #     else:
        #         pass
        # except KeyError:
        #     connectionCache[ipFrom] = set()
        #     connectionCache[ipFrom].add(ipTo)
        #     ipFeaturesTemp['clientDictIPSContacted'].add (ipTo)
        #     ipFeaturesTemp['setClientNummberOfDistinctCountries'].add (getCountryFromWhoisCache (ipTo))
        pass
    else:
        pass
        print (lineDict)

    ipFeaturesTemp['hoursummary']['numberOfIPFlows'] = ipFeaturesTemp['hoursummary']['numberOfIPFlows'] + 1
def unusedSnippedsOfCode():
    # value = ipFeaturesTemp['clientDestinationPortNumberOfFlowsTCP'].get (sourcePort, None)
    # if value is not None:
    #     ipFeaturesTemp["clientDestinationPortNumberOfFlowsTCP"][sourcePort] += 1
    # else:
    #     ipFeaturesTemp["clientDestinationPortNumberOfFlowsTCP"][sourcePort] = 1
    print('not used anymore')
def initializePortFeatures(tempDict):
    s = ['client','server']
    d = ['SourcePort', 'DestinationPort']
    f = ['TotalBytes', 'TotalPackets', 'NumberOfFlows']
    p = ['TCP','UDP']
    for source in s:
        for port in d:
            for feature in f:
                for protocol in p:
                    tempDict[source+port+feature+protocol] = {}
def fillDataToPortFeatures(clientorserver,protocol,ipFeaturesTemp,dstPort,ipTarget,sourcePort,totBytes,totalPakets,lineDict):
    if clientorserver == 'client':
        portDictIPS = 'clientDestinationPortDictIPs'
    else:
        portDictIPS = 'serverSourcePortDictIPs'

    if protocol == 'tcp':
        addPortDictIPSToDict (ipFeaturesTemp, portDictIPS + 'TCP', dstPort, ipTarget)
        addAllPortFeaturesToDict (ipFeaturesTemp, clientorserver, protocol, sourcePort, dstPort, totBytes, totalPakets)
    elif protocol == 'udp':  # udp protocol
        addPortDictIPSToDict (ipFeaturesTemp, portDictIPS + 'UDP', dstPort, ipTarget)
        addAllPortFeaturesToDict (ipFeaturesTemp, clientorserver, protocol, sourcePort, dstPort, totBytes, totalPakets)
    else:
        print(lineDict)

def addAllPortFeaturesToDict(ipFeaturesTemp,source,protocol,sourcePort,destinationPort,totalBytes,totalPackets):
    d = {'SourcePort':sourcePort , 'DestinationPort':destinationPort}
    f = {'TotalBytes' : totalBytes, 'TotalPackets' : totalPackets, 'NumberOfFlows':1}
    for port in d:
        for feature in f:
            nameOfTheFeauture = source+port+feature+protocol.upper()
            addFeaturesToDict(ipFeaturesTemp, nameOfTheFeauture, d[port], f[feature])

def addFeaturesToDict(ipFeaturesTemp, dictname, data, howmuchadd):
    if data in ipFeaturesTemp[dictname]:
        ipFeaturesTemp[dictname][data] += howmuchadd
    else:
        ipFeaturesTemp[dictname][data] = howmuchadd
def addPortDictIPSToDict(ipFeaturesTemp, dictname, port, ip):
    if port in ipFeaturesTemp[dictname]:
        if ip in ipFeaturesTemp[dictname][port]:
            ipFeaturesTemp[dictname][port][ip] += 1
        else:
            ipFeaturesTemp[dictname][port][ip] = 1
    else:
        ipFeaturesTemp[dictname][port] = {ip: 1}

def detectConnection(connectionInformation):
    # TODO : For the UDP
    if (connectionInformation == 'CON'):
        return True
    # if (connectionInformation == 'URP'):    #ASK SEBAS FOR THIS, this is icmp protocol
    #    return True
    if (len (connectionInformation.split ('_')) != 2):
        return False
    connectionInformationFrom = connectionInformation.split ('_')[0]
    connectionInformationTo = connectionInformation.split ('_')[1]
    if ('S' in connectionInformationFrom and 'S' in connectionInformationTo and 'A' in connectionInformationTo):  # maybe add to the dict of opened connection if there is no fin
        return True
    return False


def detectConnectionAttemptWithNoAnswer(connectionInformation):
    if (len (connectionInformation.split ('_')) != 2):
        return False
    connectionInformationFrom = connectionInformation.split ('_')[0]
    connectionInformationTo = connectionInformation.split ('_')[1]
    if (connectionInformationFrom == 'S' and connectionInformationTo == ''):  # Absolutely no answer
        return True
    if ('S' in connectionInformationFrom and 'R' in connectionInformationTo and 'A' in connectionInformationTo):  # Reset Acknowledged
        return True
    return False


def detectPAPAsituation(connectionInformation):
    if (len (connectionInformation.split ('_')) != 2):
        return False
    connectionInformationFrom = connectionInformation.split ('_')[0]
    connectionInformationTo = connectionInformation.split ('_')[1]
    if ('A' in connectionInformationFrom and 'A' in connectionInformationTo):
        return True
    return False
    # if (ipFrom in result or EXAMINEALLCOMPUTERS):
    #     ipFeaturesTemp = temp[ipFrom]
    #     ipFeaturesTemp['clientNumberOfIPFlows'] = ipFeaturesTemp['clientNumberOfIPFlows'] + 1
    #     if (connectionDirection == '<->' or connectionDirection == '<?>'):
    #         ipFeaturesTemp['clientDictIPSContacted'].add(ipTo)
    #         ipFeaturesTemp['setClientNummberOfDistinctCountries'].add(getCountryFromWhoisCache(ipTo))
    # if (ipTo in result or EXAMINEALLCOMPUTERS):
    #     ipFeaturesTemp = temp[ipTo]
    #     ipFeaturesTemp['clientNumberOfIPFlows'] = ipFeaturesTemp['clientNumberOfIPFlows'] + 1
    #     if (connectionDirection == '<->' or connectionDirection == '<?>'):
    #         ipFeaturesTemp['clientDictIPSContacted'].add(ipFrom)
    # if (connectionDirection != '<->'):
    #    print(line)



def stripSpacesFromConnection(string):
    string.lstrip (' ')
    string = string[2:]
    whitelist = set ('<->')
    ''.join (filter (whitelist.__contains__, string))
    whitelist = set ('->')
    ''.join (filter (whitelist.__contains__, string))
    return string


def convertLineToDict(line):
    #StartTime, Dur, Proto, SrcAddr, Sport, Dir, DstAddr, Dport, State, sTos, dTos, TotPkts, TotBytes, SrcBytes, Label
    lineDict = {}
    lineDict['StartTime'] = line.split (',')[0]
    lineDict['Dur'] = line.split (',')[1]
    lineDict['Proto'] = line.split (',')[2]
    lineDict['SrcAddr'] = line.split (',')[3]
    lineDict['Sport'] = line.split (',')[4]
    lineDict['Dir'] = line.split (',')[5]
    lineDict['DstAddr'] = line.split (',')[6]
    lineDict['Dport'] = line.split (',')[7]
    lineDict['State'] = line.split (',')[8]
    lineDict['sTos']= line.split (',')[9]
    lineDict['dTos'] = line.split (',')[10]
    lineDict['TotPkts'] = line.split (',')[11]
    lineDict['TotBytes'] = line.split (',')[12]
    lineDict['SrcBytes'] = line.split (',')[13]
    lineDict['Label'] = line.split (',')[14]
    return lineDict

def convertDictToLine(lineDict):
    return lineDict['StartTime'] + ',' + lineDict['Dur'] + ',' + lineDict['Proto'] + ',' + lineDict['SrcAddr'] + ',' + lineDict['Sport'] + ',' + lineDict['Dir'] + ',' +lineDict['DstAddr'] + ',' + lineDict['Dport'] + ',' + lineDict['State'] + ',' +lineDict['sTos'] + ',' + lineDict['dTos'] + ',' + lineDict['TotPkts'] + ',' +lineDict['TotBytes'] + ',' + lineDict['SrcBytes'] + ',' + lineDict['Label']


def gatherData():
    with open (BINETFLOW, 'r') as f:
        next (f)
        lastHourID = ""
        for line in f:
            lineDict = convertLineToDict(line)
            lastHourID = processLine (lineDict, lastHourID)
        fillFeaturesClassFromTempClass (lastHourID)


def getTimeIDSInCapture():
    return timeIDSInCapture


def getResult():
    return result


def dumper(obj):
    if isinstance (obj, set):
        return list (obj)
    return obj.__dict__


def humanreadabledump(obj):
    if isinstance (obj, set):
        return str (list (obj))
        # return ','.join(filter(None, list (obj)))
    return obj.__dict__


def signal_handler(signal, frame):
    if SAVECACHE:
        print ('You pressed Ctrl+C! Wait till caches are saved to the disc please, program will exit afterwards')
        with open ('whoiscahce.json', 'w') as fp:
            json.dump (whoiscache.get_whois_cache (), fp, default=dumper, indent=2)
        with open ('country_cache.json', 'w') as fp:
            json.dump (whoiscache.get_country_cache (), fp, default=dumper, indent=2)
        print('Exiting now!')
    sys.exit(0)

def generate_profile_from_weblogs(weblogs,ips):
    load_whois_cache_from_file()
    intializeComputersToAnalyze(ips)
    lastHourID = ""
    for weblog in weblogs:
        lineDict = weblog.attributes
        lastHourID = processLine(lineDict, lastHourID)
    fillFeaturesClassFromTempClass(lastHourID)
    if SAVECACHE:
        save_whois_cache_to_file()
    return result

def save_whois_cache_to_file():
    with open('whoiscahce.json', 'w') as fp:
        json.dump(whoiscache.get_whois_cache(), fp, default=dumper, indent=2)

def load_whois_cache_from_file():
    try:
        with open('whoiscahce.json') as data_file:
            whoiscache.whois_cache = json.load(data_file)
    except IOError:
        print('whoiscahce not found')
if __name__ == "__main__":
    #TODO Add option to load whois data on the background to speed the creation of the profile
    #TODO Add branch for devel
    signal.signal (signal.SIGINT, signal_handler)
    try:
        with open ('country_cache.json') as data_file:
            whoiscache.whois_country_cache = json.load (data_file)
    except IOError:
        print('country cache not found')
    ips = load_computers_to_analyze_from_file()
    intializeComputersToAnalyze(ips)
    gatherData ()

    # Using Data frame for generating json is no longer needed

    # dataFrame = pandas.DataFrame.from_dict(result)
    # resjson = dataFrame.to_json(orient='records', lines=True)
    # dataFramedict = dataFrame.to_dict(orient='records')
    # with open('test.json','w') as fp:
    #     fp.write(resjson)
    print('printed lines are not taken in account for profile, my TODO is to include them all')
    print('saving results')
    with open ('result.json', 'w') as fp:
        json.dump (result, fp, default=dumper)
    if SAVECACHE:
        save_whois_cache_to_file()
        with open ('country_cache.json', 'w') as fp:
            json.dump (whoiscache.get_country_cache (), fp, default=dumper, indent=2)
    print('done')
    # naplot = result['147.32.80.9']['hours']['date:2016/10/05 hour:00']['clientSourcePortNumberOfFlowsUDP']
    # x = []
    # y = []
    # for key in naplot:
    #     x.append(key)
    #     y.append(naplot[key])
    # import numpy as np
    # import matplotlib.mlab as mlab
    # import matplotlib.pyplot as plt
    #
    # mu, sigma = 100, 15
    # #x = mu + sigma * np.random.randn (10000)
    #
    # # the histogram of the data
    # n, bins, patches = plt.hist (x, 50, normed=1, facecolor='green', alpha=0.75)
    #
    # # add a 'best fit' line
    # #y = mlab.normpdf (bins, mu, sigma)
    # y = np.random.randn (len(x))
    # l = plt.plot (bins, y, 'r--', linewidth=1)
    #
    # plt.xlabel ('Smarts')
    # plt.ylabel ('Probability')
    # plt.title (r'$\mathrm{Histogram\ of\ IQ:}\ \mu=100,\ \sigma=15$')
    # plt.axis ([0, 65536, 0, 0.03])
    # plt.grid (True)
    #
    # plt.show ()
