#! /usr/bin/python3
import requests
from requests.auth import HTTPBasicAuth
import json
import datetime
import argparse

# tasks details: https://onedior.atlassian.net/browse/ONE-6650
with open("config.json") as config_file:
    config = json.load(config_file)

jiraUserName = config["JIRA_USERNAME"]
jiraApiToken = config["JIRA_API_TOKEN"]
jiraApiHost = "https://onedior.atlassian.net/rest/api/3/"
timePerIssue = config["timePerDay"]


def get_cli_args():
    parser = argparse.ArgumentParser(description="fill in the CRA for the current week")
    parser.add_argument(
        "--force", help="ignore already contributed day check", action="store_true"
    )
    parser.add_argument(
        "--setup",
        help="paste the script required for crontab setup",
        action="store_true",
    )
    parser.add_argument(
        "--month",
        help="fill in a month instead of just the current week",
        action="store_true",
    )
    parser.add_argument(
        "--yes",
        help="no user input required (assume yes)",
        action="store_true",
    )
    return parser.parse_args()


def yes_or_no(question):
    reply = str(input(f"{question} (y/n): ")).lower().strip()
    if reply[0] == "y":
        return True
    if reply[0] == "n":
        return False
    else:
        return yes_or_no("Uhhhh... please enter ")


def get_store_days_contributed():
    days_contributed = []
    try:
        with open("store.json", "r") as store_file:
            days_contributed = json.load(store_file)
    except:
        pass
    return days_contributed


def remove_duplicates(list_of_values):
    return list(dict.fromkeys(list_of_values))


def set_store_days_contributed(new_days):
    days_contributed = get_store_days_contributed()
    with open("store.json", "w") as store_file:
        days_contributed.extend(new_days)
        json.dump(remove_duplicates(days_contributed), store_file)


def day_with_week(day, days_contributed):
    return (day, day, day in days_contributed)


def getDays(useMonth=False):
    days_contributed = get_store_days_contributed()
    days = getDaysOfThisMonth() if useMonth else getDaysOfThisWeek()
    return map(lambda day: day_with_week(day, days_contributed), days)


def getDaysOfThisWeek():
    theday = datetime.date.today()
    weekday = theday.isoweekday()
    start = theday - datetime.timedelta(days=weekday - 1)
    dates = [start + datetime.timedelta(days=d) for d in range(5)]
    return map(str, dates)


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
    return map(str, filter(lambda x: x.isoweekday() < 6, dates))


def addWorklogForOneIssueOneDay(issueNumber, startDate: datetime, timeSpent):
    auth = HTTPBasicAuth(jiraUserName, jiraApiToken)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = json.dumps(
        {
            "timeSpentSeconds": timeSpent * 3600,
            "started": f"{startDate}T09:30:00.000+0000",
        }
    )
    # doc: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-worklogs/
    response = requests.request(
        "POST",
        f"{jiraApiHost}issue/{issueNumber}/worklog",
        data=payload,
        headers=headers,
        auth=auth,
    )

    return response.status_code


def day_in_contributed_(days_contributed, week_of_day):
    return week_of_day in days_contributed


def addWorkloadForAllDays(days_to_contribute):
    for x in days_to_contribute:
        day = x[0]
        for issue in timePerIssue:
            if timePerIssue[issue] != 0:
                print(f"Day {day}: Adding {timePerIssue[issue]} hours to issue {issue}")
                status = addWorklogForOneIssueOneDay(issue, day, timePerIssue[issue])
                if status == 201:
                    print("Success ✅")
                else:
                    print("Something went wrong, you have to check on Jira... ❌")
    set_store_days_contributed(
        map(
            lambda x: x[0],
            days_to_contribute,
        )
    )


def print_cron_tab_setup():
    print(
        f"To setup this script as a cron, setup your config.json with the common workload, then open your crontab (run 'crontab -e') and paste the following, updating the absolute path to this folder:"
        + "\n\n0 10 * * 1-5 cd /path/to/timetracking-enhanced/folder;./timetracking.py --yes"
    )


def main():
    args = get_cli_args()
    if args.setup:
        print_cron_tab_setup()
        exit(0)
    days_to_contribute = list(getDays(args.month))
    days_ignoring_contributed = (
        days_to_contribute
        if args.force
        else list(filter(lambda x: x[2] == False, days_to_contribute))
    )
    if len(days_ignoring_contributed) == 0:
        print(
            "all days have already been contributed, launch with '--force' to ignore the check"
        )
        exit(0)
    print("💡 This will add predefined worklog on the following days:")
    print(" ".join(map(lambda x: x[0], days_ignoring_contributed)))

    if not args.yes and not yes_or_no("Do you confirm ?"):
        print("Ok aborting 😈")
        exit(0)

    addWorkloadForAllDays(days_ignoring_contributed)


if __name__ == "__main__":
    main()
