# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.


import httplib
import datetime
import re
import urlparse

import sickbeard

from base64 import standard_b64encode
import xmlrpclib

from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex
from sickbeard.providers.generic import GenericProvider
from sickbeard import config
from sickbeard import logger


def sendNZB(nzb):

    addToTop = False
    nzbgetprio = 0

    if sickbeard.NZBGET_HOST == None:
        logger.log(u"No NZBGet host found in configuration. Please configure it.", logger.ERROR)
        return False

    try:
        url = config.clean_url(sickbeard.NZBGET_HOST)

        if sickbeard.NZBGET_USERNAME or sickbeard.NZBGET_PASSWORD:
            scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
            netloc = sickbeard.NZBGET_USERNAME + ":" + sickbeard.NZBGET_PASSWORD + "@" + netloc
            url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))

        url = urlparse.urljoin(url, u"/xmlrpc")
        url = url.encode('utf-8', 'ignore')

        logger.log(u"Connecting to NZBGet: " + url, logger.DEBUG)

        nzbGetRPC = xmlrpclib.ServerProxy(url)

        if nzbGetRPC.writelog("INFO", "SickBeard connected to drop off " + nzb.name + ".nzb" + " any moment now."):
            logger.log(u"Successful connected to NZBGet", logger.DEBUG)

        else:
            logger.log(u"Successful connected to NZBGet, but unable to send a message", logger.ERROR)

    except httplib.socket.error:
        logger.log(u"Please check if NZBGet is running. NZBGet is not responding.", logger.ERROR)
        return False

    except xmlrpclib.ProtocolError, e:
        if (e.errmsg == "Unauthorized"):
            logger.log(u"NZBGet username or password is incorrect.", logger.ERROR)

        else:
            logger.log(u"NZBGet protocol error: " + e.errmsg, logger.ERROR)

        return False

    except Exception, e:
        logger.log(u"NZBGet sendNZB failed. Error: " + ex(e), logger.ERROR)
        return False

    # if it aired recently make it high priority
    for curEp in nzb.episodes:
        if datetime.date.today() - curEp.airdate <= datetime.timedelta(days=7):
            addToTop = True
            nzbgetprio = 100

    # if it's a normal result need to download the NZB content
    if nzb.resultType == "nzb":
        genProvider = GenericProvider("")
        data = genProvider.getURL(nzb.url)
        if (data == None):
            return False

    # if we get a raw data result thats even better
    elif nzb.resultType == "nzbdata":
        data = nzb.extraInfo[0]

    nzbcontent64 = standard_b64encode(data)

    logger.log(u"Sending NZB to NZBGet")
    logger.log(u"URL: " + url, logger.DEBUG)

    try:
        # Find out if nzbget supports priority (Version 9.0+), old versions beginning with a 0.x will use the old command
        if re.search(r"^0", nzbGetRPC.version()):
            nzbget_result = nzbGetRPC.append(nzb.name + ".nzb", sickbeard.NZBGET_CATEGORY, addToTop, nzbcontent64)
        else:
            nzbget_result = nzbGetRPC.append(nzb.name + ".nzb", sickbeard.NZBGET_CATEGORY, nzbgetprio, False, nzbcontent64)

        if nzbget_result:
            logger.log(u"NZB sent to NZBGet successfully", logger.DEBUG)
            return True

        else:
            logger.log(u"NZBGet could not add %s to the queue" % (nzb.name + ".nzb"), logger.ERROR)
            return False

    except:
        logger.log(u"Connect Error to NZBGet: could not add %s to the queue" % (nzb.name + ".nzb"), logger.ERROR)
