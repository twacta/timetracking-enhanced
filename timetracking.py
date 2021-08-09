#! /usr/bin/python3
import requests
from requests.auth import HTTPBasicAuth
import json
import datetime

# tasks details: https://onedior.atlassian.net/browse/ONE-6650
with open("config.json") as config_file:
    config = json.load(config_file)

jiraUserName = config["JIRA_USERNAME"]
jiraApiToken = config["JIRA_API_TOKEN"]
jiraApiHost = "https://onedior.atlassian.net/rest/api/3/"
timePerIssue = config["timePerDay"]
useMonth = config["useMonth"]


def yes_or_no(question):
    reply = str(input(question + " (y/n): ")).lower().strip()
    if reply[0] == "y":
        return True
    if reply[0] == "n":
        return False
    else:
        return yes_or_no("Uhhhh... please enter ")


def getDays():
    return getDaysOfThisMonth() if useMonth else getDaysOfThisWeek()


def getDaysOfThisWeek():
    theday = datetime.date.today()
    weekday = theday.isoweekday()
    start = theday - datetime.timedelta(days=weekday - 1)
    dates = [start + datetime.timedelta(days=d) for d in range(5)]
    dates = [str(d) for d in dates]
    return dates


def getDaysOfThisMonth():
    theday = datetime.date.today()
    start = datetime.date(theday.year, theday.month, 1)
    end = datetime.date(
        theday.year if theday.month < 12 else theday.year + 1,
        theday.month + 1 if theday.month < 12 else 1,
        1,
    )
    nbOfDay = (end - start).days
    dates = [start + datetime.timedelta(days=d) for d in range(nbOfDay)]
    dates = [str(d) for d in filter(lambda x: x.isoweekday() < 6, dates)]
    return dates


def addWorklogForOneIssueOneDay(issueNumber, startDate, timeSpent):
    auth = HTTPBasicAuth(jiraUserName, jiraApiToken)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = json.dumps(
        {
            "timeSpentSeconds": timeSpent * 3600,
            "started": startDate + "T09:30:00.000+0000",
        }
    )
    response = requests.request(
        "POST",
        jiraApiHost + "issue/" + issueNumber + "/worklog",
        data=payload,
        headers=headers,
        auth=auth,
    )

    return response.status_code


def addWorkloadForAllDays():
    for day in getDays():
        for issue in timePerIssue:
            if timePerIssue[issue] != 0:
                print(
                    "Day "
                    + day
                    + ": "
                    + "Adding "
                    + str(timePerIssue[issue])
                    + " hours to issue "
                    + issue
                )
                status = addWorklogForOneIssueOneDay(issue, day, timePerIssue[issue])
                if status == 201:
                    print("Success ✅")
                else:
                    print("Something went wrong, you have to check on Jira... ❌")


print("💡 This will add predefined worklog on the following days")
print(" ".join(map(str, getDays())))
if yes_or_no("Do you confirm ?"):
    addWorkloadForAllDays()
else:
    print("Ok aborting 😈")
