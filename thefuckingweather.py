# Python module for thefuckingweather.com, version 2.0
# Copyright (C) 2013  Red Hat, Inc., and others.
# https://github.com/ianweller/python-thefuckingweather
#
# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://sam.zoy.org/wtfpl/COPYING for more details.
#
# Credits:
# - Colin Rice for fixing the (no-longer used) regexps to allow for
#   negative temperatures

"""Scrapes data from www.thefuckingweather.com for a given location."""

from bs4 import BeautifulSoup
from optparse import OptionParser
import urllib
import urllib2

DEGREE_SYMBOL = u"\xb0"


class LocationError(StandardError):
    """
    The website reported a "I CAN'T FIND THAT SHIT" error, which could mean
    either the server has no clue what to do with your location or that it
    messed up.
    """

    def __init__(self):
        StandardError.__init__(self, ("I CAN'T FIND THAT SHIT returned "
                                      "from website"))


class ParseError(StandardError):
    """
    Something is wrong with the code or the site owner updated his template.
    """

    def __init__(self, lookup):
        StandardError.__init__(
            self, """Couldn't parse the website: lookup {0} failed

Please report what you did to get this error and this full Python traceback
to ian@ianweller.org. Thanks!""".format(lookup))


def get_weather(location=False, celsius=False):
    """
    Retrieves weather and forecast data for a given location.

    Data is presented in a dict with three main elements: "location" (the
    location presented by TFW), "current" (current weather data) and "forecast"
    (a forecast of the next two days, with highs, lows, and what the weather
    will be like).

    "current" is a dictionary with three elements: "temperature" (an integer),
    "weather" (a list of descriptive elements about the weather, e.g., "ITS
    FUCKING HOT", which may be coupled with something such as "AND THUNDERING")
    and "remark" (a string printed by the server which is meant to be witty but
    is sometimes not. each to their own, I guess).

    "forecast" is a list of dictionaries, which each contain the keys "day" (a
    three-letter string consisting of the day of week), "high" and "low"
    (integers representing the relative extreme temperature of the day), and
    "weather" (a basic description of the weather, such as "Scattered
    Thunderstorms").

    The default is for temperatures to be in Fahrenheit. If you're so inclined,
    you can pass True as a second variable and get temperatures in Celsius.

    If you need a degree symbol, you can use thefuckingweather.DEGREE_SYMBOL.
    """
    # Generate query string
    if location == False:
        query = {"random": "True"}
    else:
        query = {"where": location}
    if celsius:
        query["unit"] = "c"
    query_string = urllib.urlencode(query)

    # Fetch HTML
    url = "http://www.thefuckingweather.com/?" + query_string
    data = urllib2.urlopen(url).read()
    soup = BeautifulSoup(data)

    # Check for an error report
    large = soup.find("p", {"class": "large"})
    if not large:
        raise ParseError("p.large")
    if large.text == "I CAN'T FIND THAT SHIT":
        raise LocationError()

    # No error, so parse current weather data
    return_val = {"current": {}, "forecast": []}

    location_span = soup.find(id="locationDisplaySpan")
    if not location_span:
        raise ParseError("#locationDisplaySpan")
    return_val["location"] = location_span.text

    temp = soup.find("span", {"class": "temperature"})
    if not temp:
        raise ParseError("span.temperature")
    try:
        return_val["current"]["temperature"] = int(temp.text)
    except ValueError:
        raise ParseError("span.temperature is not an int")

    # we called the "flavor" the remark before the website updated so now this
    # is just plain confusing
    remark = soup.find("p", {"class": "remark"})
    if not remark:
        raise ParseError("p.remark")
    special_cond = soup.find("p", {"class": "specialCondition"})
    if special_cond:
        return_val["current"]["weather"] = (remark.text, special_cond.text)
    else:
        return_val["current"]["weather"] = (remark.text,)

    flavor = soup.find("p", {"class": "flavor"})
    if not flavor:
        raise ParseError("p.flavor")
    return_val["current"]["remark"] = flavor.text

    # the fucking forecast
    return_val["forecast"] = list()
    forecast = soup.find("div", {"class": "forecastBody"})
    if not forecast:
        raise ParseError("div.forecastBody")
    try:
        day_row, high_row, low_row, forecast_row = forecast.findAll("tr")
    except ValueError:
        raise ParseError("div.forecastBody tr count is not 4")

    days = [x.text for x in day_row.findAll("th")[1:]]
    highs = [int(x.text) for x in high_row.findAll("td")]
    lows = [int(x.text) for x in low_row.findAll("td")]
    forecasts = [x.text for x in forecast_row.findAll("td")]

    if not (len(days) == len(highs) == len(lows) == len(forecasts)):
        raise ParseError("forecast counts don't match up")

    for i in range(len(days)):
        return_val["forecast"].append({"day": days[i],
                                       "high": highs[i],
                                       "low": lows[i],
                                       "weather": forecasts[i]})

    return return_val


def main():
    """
    This function is run when the python file is run from the command line. It
    prints content formatted somewhat like www.thefuckingweather.com. You can
    use the -c (--celsius) switch to return temperatures in Celsius.
    """
    usage = "usage: %prog [-c] location"
    parser = OptionParser(usage=usage)
    parser.add_option("-c", "--celsius", dest="celsius", action="store_true",
                      help=("return temperatures in Celsius (Fahrenheit "
                            "without this switch)"), default=False)
    (options, args) = parser.parse_args()
    if len(args) == 1:
        weather = get_weather(args[0], options.celsius)

        # Location
        print "({0})".format(weather["location"])

        # Current conditions
        print "{0}{1}?! {2}".format(weather["current"]["temperature"],
                                    DEGREE_SYMBOL.encode("utf-8"),
                                    weather["current"]["weather"][0])
        if len(weather) > 1:
            print weather["current"]["weather"][1]
        print weather["current"]["remark"]
        print

        # Daily forecast
        print "Forecast:"
        for daily in weather["forecast"]:
            print "  {0}:".format(daily["day"])
            print "    High: {0}".format(daily["high"])
            print "    Low: {0}".format(daily["low"])
            print "    Weather: {0}".format(daily["weather"])
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
